"""Agent loop of the AI assistant, without Qt.

For a task of several dependent steps (a recipe of CrysPy such as the
step-by-step refinement) the model works one action at a time: it writes
a short thought and one action in JSON, the program runs the action and
gives the result back (the observation: text, chi_sq/n and R_F2 before and
after, warnings, errors), and the model decides the next action, until it gives
the final answer or the limits are reached.

The algorithms (recipes), the numbers and the checks of the results are
in CrysPy (tools list_recipes, get_recipe, refine, undo_refinement); this
module only runs the loop. The same module is planned for PyColl5: keep
it free of CrysPy Editor specifics (the tools come through run_tool).
"""
import json
from typing import Callable, List, Optional

MAX_AGENT_STEPS = 12  # actions for one request by default (setting "max_steps")
MAX_SAME_CALLS = 2  # the same action with the same arguments
MAX_ERRORS_IN_ROW = 3  # failed actions one after another
N_MAX_OBSERVATION = 1500  # characters of the result of the last actions
N_MAX_OLD_OBSERVATION = 300  # characters of the results of older actions
N_RECENT_OBSERVATIONS = 2  # the last observations given in full
N_MAX_STEP_RESULT = 6  # lines of the result of an action shown to the user
FINAL = "final"

AGENT_RULES = """Work step by step: respond with ONE JSON object for ONE action:
{"thought": "<one short sentence: what the last result shows and why this action>",
 "action": "<name of the action>", "arguments": {...}}
When the task is done, or cannot be done, respond:
{"thought": "...", "action": "final", "answer": "<answer for the user>"}
After each action you get its result. Read it before the next action: when it
is an Error, correct the arguments or choose another way; never repeat a failed
call unchanged. When a recipe applies, take its steps with get_recipe first and
follow them; judge each step by the change of chi_sq/n (R_F2 for single
crystals) and the warnings in the results, as the recipe says. Report only what the results show, with numbers;
never claim a step that was not done."""


def form_step_schema(l_action: List[str]) -> dict:
    """JSON schema of a reply of the model (grammar of llama.cpp): the
    action is one of the known names, so no other can be written."""
    return {
        "type": "object",
        "properties": {
            "thought": {"type": "string"},
            "action": {"type": "string", "enum": list(l_action) + [FINAL]},
            "arguments": {"type": "object"},
            "answer": {"type": "string"},
        },
        "required": ["thought", "action"],
    }


def take_step_reply(raw: str, take_json_object: Callable) -> dict:
    """{"thought", "action", "arguments", "answer"} of a reply of the model;
    a reply without an action is the final answer."""
    reply = take_json_object(raw)
    if reply is None:
        return {"thought": "", "action": FINAL, "arguments": {}, "answer": raw.strip()}
    action = str(reply.get("action") or FINAL).strip()
    arguments = reply.get("arguments", {})
    answer = reply.get("answer", reply.get("final", ""))
    return {"thought": str(reply.get("thought", "") or ""),
            "action": FINAL if action.lower() in ("", "none", FINAL) else action,
            "arguments": arguments if isinstance(arguments, dict) else {},
            "answer": "" if answer is None else str(answer)}


def cut_text(text: str, n_max: int) -> str:
    return text if len(text) <= n_max else text[:n_max] + "\n[...cut...]"


def shorten_old_observations(messages: list, n_prefix: int):
    """Keep the last observations in full and the start of older ones:
    the context of a small model is short."""
    l_index = [ind for ind in range(n_prefix, len(messages))
               if messages[ind]["role"] == "user"]
    for ind in l_index[:-N_RECENT_OBSERVATIONS]:
        messages[ind] = dict(messages[ind], content=cut_text(messages[ind]["content"], N_MAX_OLD_OBSERVATION))


class Agent:
    """The loop plan -> action -> observation -> decision.

    model: an object with chat(messages, flag_json, schema) -> str;
    run_tool(name, obj, arguments) -> (result, flag_object_changed): the
    result is text (an error starts with "Error") or a Dialog (questions to
    the user: the loop stops and the assistant asks them);
    l_action: names of the actions the model may call;
    take_json_object(text) -> dict or None;
    max_steps: the most actions for one request."""

    def __init__(self, model, run_tool: Callable, l_action: List[str], take_json_object: Callable,
                 max_steps: int = MAX_AGENT_STEPS):
        self.model = model
        self.max_steps = max(1, int(max_steps))
        self.run_tool = run_tool
        self.l_action = list(l_action)
        self.take_json_object = take_json_object

    def run(self, system_prompt: str, history: list, question: str, cryspy_object=None,
            on_action: Optional[Callable] = None, should_stop: Optional[Callable] = None,
            l_first: Optional[list] = None, on_step: Optional[Callable] = None) -> dict:
        """Run the loop for the request.

        l_first: actions [(name, arguments)] already chosen by the model
        (e.g. get_recipe), done before the first call of the loop.
        on_step(text): called with the text of each step for the user when
        the step starts (its number, thought and action) and when its result
        comes, so that the user sees the course of the work and can stop it.

        Returns {"steps": [(thought, action, arguments, result)], "answer",
        "flag_object_changed", "dialog": a Dialog when an action asks the
        user, "stopped": the reason the loop ended without an answer}."""
        messages = [{"role": "system", "content": f"{system_prompt}\n\n{AGENT_RULES}"}]
        messages.extend(history)
        messages.append({"role": "user", "content": question})
        n_prefix = len(messages)
        schema = form_step_schema(self.l_action)
        l_step, l_call = [], []
        flag_object_changed, n_error, answer, stopped, dialog = False, 0, "", "", None
        l_todo = [{"thought": "", "action": name, "arguments": arguments, "answer": ""}
                  for name, arguments in (l_first or [])]
        while True:
            if should_stop is not None and should_stop():
                stopped = f"Stopped by the user after {len(l_step)} actions."
                break
            if l_todo:
                step = l_todo.pop(0)
                messages.append({"role": "assistant", "content": json.dumps(
                    {"thought": step["thought"], "action": step["action"], "arguments": step["arguments"]})})
            else:
                if len(l_step) >= self.max_steps:
                    stopped = (f"The limit of {self.max_steps} actions is reached (Maximal number of "
                               "steps of the agent in the model settings).")
                    break
                shorten_old_observations(messages, n_prefix)
                raw = self.model.chat(messages, flag_json=True, schema=schema)
                messages.append({"role": "assistant", "content": raw})
                step = take_step_reply(raw, self.take_json_object)
            if step["action"] == FINAL:
                answer = step["answer"]
                break
            action, arguments = step["action"], step["arguments"]
            if on_step is not None:
                on_step(form_step_start_text(len(l_step) + 1, step["thought"], action))
            key = (action, json.dumps(arguments, sort_keys=True, default=str))
            if l_call.count(key) >= MAX_SAME_CALLS:
                result = ("Error: this action with these arguments was already done "
                          f"{MAX_SAME_CALLS} times; choose another action or give the final answer.")
            else:
                l_call.append(key)
                if on_action is not None:
                    on_action(action)
                result, flag_changed = self.run_tool(action, cryspy_object, arguments)
                if not isinstance(result, str):  # a Dialog: the user answers its questions
                    dialog = result
                    l_step.append((step["thought"], action, arguments, result.start()))
                    if on_step is not None:
                        on_step(form_step_result_text(action, result.start()))
                    break
                flag_object_changed = flag_object_changed or (flag_changed and not result.startswith("Error"))
            if on_step is not None:
                on_step(form_step_result_text(action, result))
            l_step.append((step["thought"], action, arguments, result))
            n_error = n_error + 1 if result.startswith("Error") else 0
            if n_error >= MAX_ERRORS_IN_ROW:
                stopped = f"{MAX_ERRORS_IN_ROW} actions failed one after another."
                break
            messages.append({"role": "user", "content": (
                f"Result of {action}:\n{cut_text(result, N_MAX_OBSERVATION)}\n\n"
                "Next action, or the final answer (JSON).")})
        return {"steps": l_step, "answer": answer, "flag_object_changed": flag_object_changed,
                "dialog": dialog, "stopped": stopped}


def form_step_start_text(number: int, thought: str, action: str) -> str:
    s_thought = f" {thought}" if thought else ""
    return f"Step {number}:{s_thought}\n[{action}] ..."


def form_step_result_text(action: str, result) -> str:
    """The start of the result of an action for the user."""
    l_line = str(result).split("\n")
    s_result = "\n".join(l_line[:N_MAX_STEP_RESULT])
    if len(l_line) > N_MAX_STEP_RESULT:
        s_result += "\n..."
    return f"[{action}] {s_result}"


def form_steps_text(l_step: list) -> str:
    """The course of the work for the user: the thought and the start of
    the result of each action."""
    ls_out = []
    for number, (thought, action, _, result) in enumerate(l_step, start=1):
        s_thought = f" {thought}" if thought else ""
        ls_out.append(f"Step {number}:{s_thought}\n{form_step_result_text(action, result)}")
    return "\n\n".join(ls_out)

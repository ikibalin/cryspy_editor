"""Local LLM assistant for CrysPy Editor, without Qt.

The model is any chat model in GGUF format loaded by llama-cpp-python
(optional dependency: pip install cryspy_editor[ai]). Nothing is sent
to the internet: the model file is chosen by the user and runs locally.

The structure is the one of the assistant of PyColl5 (assistant.py,
assistant_tools.py, ui_assistant.py): LocalModel talks to the model,
Assistant asks it for actions in JSON and runs them; only the tools differ
(here the tools of CrysPy).
"""
import json
import os
import re
from typing import Callable, Dict, List, Optional

from cryspy_editor.widgets.assistant_agent import Agent, form_steps_text
from cryspy_editor.widgets.assistant_dialog import ALL_INFORMATION, Dialog, is_cancel
from cryspy_editor.widgets.assistant_tools import (
    D_TOOLS,
    form_recipes_text,
    form_tools_text,
    is_answer_tool,
    is_request_tool,
    run_tool,
)

try:
    from llama_cpp import Llama
    flag_llama_cpp = True
except ImportError:
    Llama = None
    flag_llama_cpp = False


INSTALL_HINT = (
    "The AI assistant needs the optional package llama-cpp-python.\n"
    "Install it with:\n    pip install llama-cpp-python\n"
    "or\n    pip install cryspy_editor[ai]"
)

MAX_HISTORY_MESSAGES = 10
TOKENS_PER_MESSAGE = 8
MAX_STEPS = 6  # actions for one request
MAX_RETRIES = 2  # the model corrects the actions with an error in their arguments
N_MAX_RESULT = 3000  # characters of a result of a tool given to the model
N_MAX_HISTORY = 2000  # characters of a reply kept in the chat history
ANSWER_KEYS = ("answer", "message", "reply", "text")  # the answer in the reply of the model
# actions that start the agent loop (assistant_agent.py): a recipe of CrysPy,
# or a task whose next steps depend on the results
STEP_BY_STEP = "work_step_by_step"
AGENT_ACTIONS = ("get_recipe", STEP_BY_STEP)
NOTHING_DONE = ("Nothing is done: no action of the assistant was run for this request. Ask in other words, "
                "or do it in the window of CrysPy Editor.")
# an answer that reports a change (English, Russian, French, German): without
# an action that made it, it is not shown (claims_done)
RE_DONE = re.compile(
    r"\b(is|are|was|were|has been|have been|has|have|I've|I have|we have)\s+(now\s+|been\s+|successfully\s+)*"
    r"(applied|set|changed|updated|done|refined|reduced|saved|exported|coloured|colored|tagged|selected|"
    r"removed|created|made|corrected|replaced|integrated|opened|started|finished|completed)\b"
    r"|\b(applied|updated|refined|completed|done)\s+(to|for|in|on)\s+(all|the|\d)"
    r"|^\s*(done|applied|completed)\b"
    r"|применен|применён|установлен|изменен|изменён|сделан|выполнен|уточнен|уточнён|сохранен|сохранён"
    r"|выделен|окрашен|удален|удалён|обновлен|обновлён|заменен|заменён|готово"
    r"|\b(appliqu|modifi|effectu|termin|enregistr)é|\b(angewendet|gesetzt|geändert|erledigt)\b",
    re.IGNORECASE)

# n_threads = 0 means all cores but one; n_gpu_layers = -1 means all layers
# on GPU (Metal on Apple Silicon, CUDA if llama-cpp-python is built with it)
DEFAULT_SETTINGS = {
    "n_ctx": 4096,
    "n_threads": 0,
    "n_gpu_layers": -1,
    "max_tokens": 512,
    "temperature": 0.2,
}

# (minimal RAM in GB, models, approximate size of the Q4_K_M file); the
# step-by-step work by recipes needs a general instruct model of 7B or more
L_RECOMMENDED_MODELS = (
    (0, "Qwen2.5-3B-Instruct (single requests only: too weak for recipes)", "2 GB"),
    (8, "Qwen2.5-7B-Instruct", "4.7 GB"),
    (16, "Qwen2.5-14B-Instruct", "9 GB"),
)


def take_settings(settings: Optional[dict] = None) -> dict:
    """Default settings updated by known keys of the given ones."""
    d_out = dict(DEFAULT_SETTINGS)
    if isinstance(settings, dict):
        for key in DEFAULT_SETTINGS:
            if key in settings:
                d_out[key] = type(DEFAULT_SETTINGS[key])(settings[key])
    return d_out


def get_total_memory_gb() -> Optional[float]:
    """Physical memory of the computer in GB, None if unknown."""
    try:
        if os.name == "nt":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return status.ullTotalPhys / 1024**3
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3
    except (AttributeError, ValueError, OSError):
        return None


def take_recommended_index(memory_gb: Optional[float]) -> Optional[int]:
    """Index in L_RECOMMENDED_MODELS for the given memory."""
    if memory_gb is None:
        return None
    index = 0
    for ind, (min_memory, _, _) in enumerate(L_RECOMMENDED_MODELS):
        # 8 GB machines report a bit less than 8
        if memory_gb >= 0.9 * min_memory:
            index = ind
    return index


def take_json_object(text: str) -> Optional[dict]:
    """Return the first JSON object found in the text, or None."""
    decoder = json.JSONDecoder()
    idx = text.find("{")
    while idx != -1:
        try:
            obj, _ = decoder.raw_decode(text[idx:])
            if isinstance(obj, dict):
                return obj
        except ValueError:
            pass
        idx = text.find("{", idx + 1)
    return None


def form_system_prompt(cryspy_object=None) -> str:
    """Instructions for the model: the program, the actions with their
    arguments, the loaded object and the answer format."""
    s_recipe = ""
    if "get_recipe" in D_TOOLS:
        s_recipe = f"""

A task of several steps where the next step depends on the results (e.g. a
step-by-step refinement) is done by a recipe of CrysPy: give the single action
"get_recipe" with the name of the recipe; you will then work one action at a
time. Recipes:
{form_recipes_text()}
When no recipe fits such a task, give the single action "{STEP_BY_STEP}" {{}}."""
    s_state = "\nNo file is opened now."
    if cryspy_object is not None:
        l_name = [str(getattr(item, "data_name", type(item).__name__))
                  for item in getattr(cryspy_object, "items", [])]
        s_state = (f"\nThe opened file has {len(l_name)} data blocks: "
                   f"{', '.join(l_name)}." if l_name else "\nThe opened file is empty.")
    return f"""You are the assistant of CrysPy Editor, a program for crystallographic
analysis of neutron and X-ray diffraction data with the CrysPy library
(crystal structures, magnetic structures, single crystal, powder and TOF
experiments, refinement RhoChi, MEM). The user works with an rcif file.{s_state}

To do what the user asks, choose the actions of CrysPy, done in their order:
{form_tools_text()}

A request of several parts (e.g. refine the cell and then refine) has one
action for each part. A greeting or a question about scientific things needs
no action. When the user asks how to describe something in rcif or what a
category means (thermal vibrations, multipoles, extinction, twins, ...), use
the action "get_help" and answer from its text only. A question about the
opened file (parameters, cell, chi-square, structure) is answered by an
action, never from the chat: the values in the chat may be old or wrong. In
the answers name the menus and windows of CrysPy Editor, never the actions.
Answer in the language of the user. Never invent results: use the actions.
Nothing is changed without an action: when no action does what the user
asks, give no action and say that you cannot do it (and where in CrysPy
Editor it is done); never write that something is done, applied or set.{s_recipe}

Respond ONLY with a JSON object:
{{"actions": [{{"action": "<one of: {', '.join(take_action_names())}>", "arguments": {{...}}}}, ...], "answer": "<short text for the user>"}}

Examples (request: actions):
- how to describe thermal vibrations?:
  [{{"action": "get_help", "arguments": {{"query": "thermal vibrations"}}}}]
- which parameters are refined?:
  [{{"action": "list_parameters", "arguments": {{"refined_only": true}}}}]
- refine the cell parameters and run the refinement:
  [{{"action": "refine_parameters", "arguments": {{"pattern": "cell.length"}}}},
  {{"action": "refine", "arguments": {{}}}}]
- set a of crystal_pbso4 to 8.48:
  [{{"action": "set_parameter", "arguments": {{"path": "crystal_pbso4.cell.length_a", "value": 8.48}}}}]
- fix all parameters and refine only atomic positions:
  [{{"action": "fix_parameters", "arguments": {{}}}},
  {{"action": "refine_parameters", "arguments": {{"pattern": "atomic positions"}}}}]
- refine the scale factor:
  [{{"action": "refine_parameters", "arguments": {{"pattern": "scale"}}}}]
- calculate the nuclear structure factor of (5 0 3):
  [{{"action": "calculate_structure_factor", "arguments": {{"hkl": "5 0 3"}}}}]
- download Al from COD and add it:
  [{{"action": "add_crystal_from_cod", "arguments": {{"formula": "Al"}}}}]{form_agent_examples()}"""


def take_action_names() -> list:
    """Names of the actions of the first reply of the model."""
    l_name = list(D_TOOLS)
    if "get_recipe" in D_TOOLS:
        l_name.append(STEP_BY_STEP)
    return l_name


def form_agent_examples() -> str:
    if "get_recipe" not in D_TOOLS:
        return ""
    return """
- refine the structure step by step:
  [{"action": "get_recipe", "arguments": {"name": "refine_structure"}}]"""


def fit_messages(messages: list, max_tokens: int, n_ctx: int, count_tokens: Callable) -> list:
    """Shorten the messages so that the prompt and the answer fit the
    context of n_ctx tokens: first the oldest history is dropped (the
    system message and the last message stay), then the longest message is
    cut from its end."""
    budget = n_ctx - max_tokens - TOKENS_PER_MESSAGE * len(messages) - 16  # the chat template adds a few
    if budget <= 0:
        raise ValueError(
            f"The maximal answer length ({max_tokens} tokens) leaves no room for the question in the context "
            f"of {n_ctx} tokens. Increase the context or decrease the answer length in "
            "AI assistant -> Load local model.")
    messages = [dict(message) for message in messages]
    l_tokens = [count_tokens(message["content"]) for message in messages]
    while sum(l_tokens) > budget and len(messages) > 2:
        del messages[1], l_tokens[1]
    while sum(l_tokens) > budget:
        ind = max(range(len(messages)), key=lambda i: l_tokens[i])
        excess = sum(l_tokens) - budget
        content = messages[ind]["content"]
        n_keep = max(0, int(len(content) * (1 - (excess + 8) / l_tokens[ind])) - 1)
        if n_keep == 0 or n_keep >= len(content):
            n_keep = len(content) // 2
        messages[ind]["content"] = content[:n_keep] + "\n[...cut...]"
        l_tokens[ind] = count_tokens(messages[ind]["content"])
        if len(content) < 16:
            break
    return messages


def take_step(step: dict) -> Optional[tuple]:
    """(action, arguments) of a step of the reply of the model; None for no
    action. Without "arguments", the other keys of the step are the
    arguments (models write {"action": "set_parameter", "path": ...}).
    "tool" is the key of the first version of the prompt. An unknown action
    is kept: CrysPy answers it with the list of known tools."""
    action = str(step.get("action", step.get("tool", "none")) or "none").strip()
    if action.lower() in ("none", ""):
        return None
    if "arguments" in step:
        arguments = step["arguments"]
    else:
        arguments = {key: value for key, value in step.items()
                     if key not in ("action", "tool") + ANSWER_KEYS}
    return action, arguments if isinstance(arguments, dict) else {}


def take_decision(raw: str) -> dict:
    """{"actions": [(action, arguments), ...], "answer"} of the reply of the
    model: {"actions": [{"action", "arguments"}, ...], "answer"} or a single
    {"action", "arguments", "answer"}; a reply that is not JSON is the
    answer."""
    decision = take_json_object(raw)
    if decision is None:
        return {"actions": [], "answer": raw.strip()}
    l_step = decision.get("actions")
    if not isinstance(l_step, list):
        l_step = [decision]
    l_action = [step for step in (take_step(step) for step in l_step if isinstance(step, dict)) if step]
    answer = next((decision[key] for key in ANSWER_KEYS if key in decision), "")
    return {"actions": l_action, "answer": "" if answer is None else str(answer)}


def claims_done(answer: str) -> bool:
    """The answer reports a change (applied, set, done...): shown only when
    an action made it (small models write "parameters refined" with no
    action)."""
    return bool(RE_DONE.search(answer or ""))


class LocalModel:
    """A local GGUF chat model loaded by llama-cpp-python."""

    def __init__(self, model_path: str, settings: Optional[dict] = None):
        if not flag_llama_cpp:
            raise ImportError(INSTALL_HINT)
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"Model file '{model_path}' is not found.")
        self.settings = take_settings(settings)
        n_threads = self.settings["n_threads"]
        if n_threads <= 0:
            n_threads = max(1, (os.cpu_count() or 2) - 1)
        self.model_path = model_path
        self.llm = Llama(
            model_path=model_path, n_ctx=self.settings["n_ctx"],
            n_threads=n_threads, n_gpu_layers=self.settings["n_gpu_layers"],
            verbose=False)

    @property
    def model_name(self) -> str:
        return os.path.basename(self.model_path)

    def close(self):
        """Free the model and its context now. Called before the program
        exits: a model left to the interpreter shutdown makes the Metal
        backend of llama.cpp abort (GGML_ASSERT in ggml_metal_device_free)."""
        llm = getattr(self, "llm", None)
        self.llm = None
        if llm is not None and hasattr(llm, "close"):
            llm.close()

    def count_tokens(self, text: str) -> int:
        return len(self.llm.tokenize(text.encode("utf-8"), add_bos=False))

    def chat(self, messages: List[Dict[str, str]], flag_json: bool = False,
             schema: Optional[dict] = None) -> str:
        """Reply of the model; with flag_json it is a JSON object, with
        schema it follows the JSON schema (grammar of llama.cpp)."""
        kwargs = {}
        if flag_json:
            kwargs["response_format"] = {"type": "json_object"}
            if schema is not None:
                kwargs["response_format"]["schema"] = schema
        max_tokens = self.settings["max_tokens"]
        messages = fit_messages(messages, max_tokens, self.llm.n_ctx(), self.count_tokens)
        result = self.llm.create_chat_completion(
            messages=messages, max_tokens=max_tokens,
            temperature=self.settings["temperature"], **kwargs)
        return result["choices"][0]["message"]["content"].strip()


class Assistant:
    """Chat with a model (an object with chat(messages, flag_json) -> str,
    such as LocalModel) that chooses the actions of CrysPy."""

    def __init__(self, model):
        self.model = model
        self.history: List[Dict[str, str]] = []
        self.dialog: Optional[Dialog] = None  # questions of an action to the user
        self.flag_dialog_changed = False  # the action of the dialog changes the CrysPy object
        self.flag_stop = False  # set from the window (request_stop): the agent loop stops

    @property
    def model_name(self) -> str:
        return getattr(self.model, "model_name", "model")

    @property
    def model_path(self) -> str:
        return getattr(self.model, "model_path", "")

    def clear_history(self):
        self.history = []
        self.dialog = None

    def request_stop(self):
        """Stop the step-by-step work after the running action (called
        from another thread)."""
        self.flag_stop = True

    def is_asking(self) -> bool:
        """True while the assistant waits for the answer to its question."""
        return self.dialog is not None

    def _remember(self, question: str, text: str):
        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": text[:N_MAX_HISTORY]})

    def _finish_dialog(self, on_action: Optional[Callable] = None):
        """Result of the action of the dialog with all its values: text, or
        the next Dialog when the action needs more values."""
        dialog, self.dialog = self.dialog, None
        if on_action is not None:
            on_action(dialog.name)
        try:
            result = dialog.finish()
        except (ValueError, TypeError, KeyError) as e:
            return f"Error: {e}"
        return result if isinstance(result, Dialog) else str(result)

    def answer_dialog(self, answer: str, on_action: Optional[Callable] = None) -> dict:
        """The answer of the user to the question of the dialog: read without
        the model; the action is done when all values are known."""
        dialog = self.dialog
        name, l_action = dialog.name, []
        if is_cancel(answer):
            self.dialog = None
            text = f"Stopped: {name} is not done."
        else:
            flag_taken, message = self.dialog.answer(answer)
            if not flag_taken:
                text = f"{message}\n{self.dialog.prompt()}"
            elif self.dialog.is_done():
                result = self._finish_dialog(on_action)
                if isinstance(result, Dialog):  # the action asks more: the numbers of questions go on
                    self.dialog, result.n_asked = result, dialog.n_asked
                    message = message.replace(f"\n{ALL_INFORMATION}", "")
                    s_intro = f"{result.intro}\n" if result.intro else ""
                    text = f"{message}\n{s_intro}{result.prompt()}"
                else:
                    l_action.append((name, dict(dialog.values), result))
                    text = f"{message}\n\n[{name}] {result}"
            else:
                text = f"{message}\n{self.dialog.prompt()}"
        self._remember(answer, text)
        flag_object_changed = bool(l_action) and self.flag_dialog_changed and not l_action[0][2].startswith("Error")
        return {"text": text, "actions": l_action, "flag_object_changed": flag_object_changed,
                "question": self.is_asking()}

    def close(self):
        """Free the model (see LocalModel.close)."""
        if hasattr(self.model, "close"):
            self.model.close()

    def ask(self, question: str, cryspy_object=None, on_action: Optional[Callable] = None) -> dict:
        """Process a request: the model chooses the actions (at most
        MAX_STEPS) and the answer at once; after the actions of a question
        (assistant_tools.is_answer_tool) it answers from their results.
        on_action(name): called before each action.

        Returns {"text": reply for the user, "actions": [(name, arguments,
        result), ...], "flag_object_changed": the CrysPy object was
        modified, "question": the assistant asks a question (a tool returned
        an assistant_dialog.Dialog); the next request is its answer}."""
        if self.dialog is not None:
            return self.answer_dialog(question, on_action)
        messages = [{"role": "system", "content": form_system_prompt(cryspy_object)}]
        messages.extend(self.history[-MAX_HISTORY_MESSAGES:])
        messages.append({"role": "user", "content": question})
        raw = self.model.chat(messages, flag_json=True)
        decision = take_decision(raw)
        if any(action in AGENT_ACTIONS for action, _ in decision["actions"]) and "get_recipe" in D_TOOLS:
            return self.ask_step_by_step(question, cryspy_object, decision["actions"], on_action)
        answer = decision["answer"]
        l_action, l_done = [], []
        flag_object_changed = False
        l_todo = decision["actions"]
        for i_retry in range(MAX_RETRIES + 1):
            l_error = []
            for action, arguments in l_todo:
                key = (action, json.dumps(arguments, sort_keys=True, default=str))
                if key in l_done or len(l_done) >= MAX_STEPS:
                    continue
                l_done.append(key)
                if action == "get_help" and not arguments.get("query"):
                    arguments = dict(arguments, query=question)
                if is_request_tool(action):
                    arguments = dict(arguments, request=question)
                if on_action is not None:
                    on_action(action)
                result, flag_changed = run_tool(action, cryspy_object, arguments)
                if isinstance(result, Dialog):  # the next requests are the answers to its questions
                    tool = D_TOOLS.get(action)
                    self.dialog = result
                    self.flag_dialog_changed = bool(getattr(tool, "flag_object_changed", flag_changed))
                    l_action.append((action, arguments, result.start()))
                    break
                flag_object_changed = flag_object_changed or flag_changed
                if result.startswith("Error") and i_retry < MAX_RETRIES:  # corrected below
                    # the model may send the same call again: it is tried again
                    l_done.remove(key)
                    l_error.append((action, arguments, result))
                else:
                    l_action.append((action, arguments, result))
            if not l_error or self.dialog is not None:
                break
            s_error = "\n".join(f"{action} {json.dumps(arguments, default=str)}: {result}"
                                for action, arguments, result in l_error)
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": (
                f"These actions were not done:\n{s_error}\nThe other actions are done. Respond with the corrected "
                'actions only: {"actions": [...]}.')})
            raw = self.model.chat(messages, flag_json=True)
            l_todo = take_decision(raw)["actions"]
        # the answer was written before the results: not when an action failed
        flag_failed = any(result.startswith("Error") for _, _, result in l_action)
        if flag_failed or self.dialog is not None:  # the questions are the answer
            answer = ""
        # a change is never reported without an action that made it
        if not l_action and claims_done(answer):
            answer = NOTHING_DONE
        # the answer to a question is made from the results (no more actions)
        if self.dialog is None and any(is_answer_tool(action) for action, _, _ in l_action):
            s_result = "\n\n".join(f"Result of {action}:\n{result[:N_MAX_RESULT]}" for action, _, result in l_action)
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": (
                f"{s_result}\n\nThe actions are done. Answer the request \"{question}\" only from these results, "
                "not from the chat (its values may be old); when the results do not answer it, say so. "
                'Respond with {"answer": "<short text for the user>"}.')})
            reply = take_decision(self.model.chat(messages, flag_json=True))["answer"]
            if flag_failed and claims_done(reply):  # "set and refined" after an error: the results say it
                reply = ""
            answer = reply or ("" if claims_done(answer) else answer)
        text = "\n\n".join(f"[{action}] {result}" for action, _, result in l_action)
        if answer:
            text = answer if text == "" else f"{text}\n\n{answer}"
        if text == "":
            text = "No answer: try to ask in other words."
        self._remember(question, text)
        return {"text": text, "actions": l_action, "flag_object_changed": flag_object_changed,
                "question": self.is_asking()}

    def ask_step_by_step(self, question: str, cryspy_object, l_first: list,
                         on_action: Optional[Callable] = None) -> dict:
        """The request is done by the agent loop (assistant_agent.Agent):
        one action at a time, each chosen after the result of the previous
        one. l_first: the actions chosen already (get_recipe)."""
        self.flag_stop = False
        l_first = [(action, arguments) for action, arguments in l_first
                   if action in AGENT_ACTIONS and action != STEP_BY_STEP][:1]
        agent = Agent(self.model, run_tool, list(D_TOOLS), take_json_object)
        out = agent.run(form_system_prompt(cryspy_object), self.history[-MAX_HISTORY_MESSAGES:], question,
                        cryspy_object, on_action=on_action, should_stop=lambda: self.flag_stop,
                        l_first=l_first)
        l_action = [(action, arguments, result) for _, action, arguments, result in out["steps"]]
        answer = out["answer"]
        if out["dialog"] is not None:
            self.dialog = out["dialog"]
            self.flag_dialog_changed = bool(getattr(D_TOOLS.get(self.dialog.name), "flag_object_changed", True))
            answer = ""
        elif not any(not str(result).startswith("Error") for _, _, result in l_action) and claims_done(answer):
            answer = NOTHING_DONE
        ls_out = [form_steps_text(out["steps"])] if out["steps"] else []
        if out["stopped"]:
            ls_out.append(f"{out['stopped']} The results above are those of the actions done.")
        if answer:
            ls_out.append(answer)
        text = "\n\n".join(ls_out) or "No answer: try to ask in other words."
        self._remember(question, text)
        return {"text": text, "actions": l_action, "flag_object_changed": out["flag_object_changed"],
                "question": self.is_asking()}

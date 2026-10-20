"""Local LLM assistant for CrysPy Editor.

The model is any chat model in GGUF format loaded by llama-cpp-python
(optional dependency: pip install cryspy_editor[ai]). Nothing is sent
to the internet: the model file is chosen by the user and runs locally.
"""
import json
import os
from typing import Callable, Dict, List, Optional

import cryspy

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


def action_refine(cryspy_object: cryspy.GlobalN) -> str:
    if len(cryspy_object.get_variable_names()) == 0:
        return "No parameters are marked for refinement."
    result = cryspy.rhochi_rietveld_refinement(cryspy_object)
    return f"Refinement finished.\n{result}"


def action_calculate(cryspy_object: cryspy.GlobalN) -> str:
    result = cryspy.rhochi_no_refinement(cryspy_object)
    return f"Calculation finished.\n{result}"


def action_fix_all_parameters(cryspy_object: cryspy.GlobalN) -> str:
    cryspy_object.fix_variables()
    return "All parameters are fixed."


def action_show_refined_parameters(cryspy_object: cryspy.GlobalN) -> str:
    names = cryspy_object.get_variable_names()
    if len(names) == 0:
        return "No parameters are marked for refinement."
    ls_out = ["| Parameter | Index | Value |", "| --- | --- | --- |"]
    for name in names:
        value = cryspy_object.get_variable_by_name(name)
        param, index = name[-1][0], name[-1][1]
        ls_out.append(f"| {param} | {index} | {value:.5f} |")
    return "\n".join(ls_out)


def action_show_model(cryspy_object: cryspy.GlobalN) -> str:
    return cryspy_object.to_cif()


# name -> (description for the model, function, flag_object_changed)
D_ACTIONS: Dict[str, tuple] = {
    "refine": (
        "run the refinement of the parameters marked for refinement",
        action_refine, True),
    "calculate": (
        "calculate the model without refinement (chi-square, calculated data)",
        action_calculate, True),
    "fix_all_parameters": (
        "fix all parameters (switch off their refinement)",
        action_fix_all_parameters, True),
    "show_refined_parameters": (
        "list the parameters marked for refinement with their values",
        action_show_refined_parameters, False),
    "show_model": (
        "show the whole current model and data as text",
        action_show_model, False),
}


def form_system_prompt() -> str:
    ls_action = [f"- {name}: {desc}" for name, (desc, _, _) in D_ACTIONS.items()]
    s_actions = "\n".join(ls_action)
    return f"""You are the assistant of CrysPy Editor, a program for crystallographic
analysis of neutron and X-ray diffraction data with the CrysPy library.
The user has a CrysPy object loaded (crystal structures, experiments, data).

If the user asks to do something with the object, choose one action:
{s_actions}
Otherwise use the action "none" and answer the question in "answer".

Respond ONLY with a JSON object:
{{"action": "<one of: {', '.join(D_ACTIONS)}, none>", "answer": "<short text for the user>"}}"""


class LLMLocal:
    """Chat with a local GGUF model and run CrysPy actions it chooses."""

    def __init__(self, model_path: str, n_ctx: int = 4096,
                 n_threads: Optional[int] = None):
        if not flag_llama_cpp:
            raise ImportError(INSTALL_HINT)
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"Model file '{model_path}' is not found.")
        if n_threads is None:
            n_threads = max(1, (os.cpu_count() or 2) - 1)
        self.model_path = model_path
        self.llm = Llama(
            model_path=model_path, n_ctx=n_ctx, n_threads=n_threads,
            verbose=False)
        self.history: List[Dict[str, str]] = []

    @property
    def model_name(self) -> str:
        return os.path.basename(self.model_path)

    def clear_history(self):
        self.history = []

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 512,
             flag_json: bool = False) -> str:
        kwargs = {}
        if flag_json:
            kwargs["response_format"] = {"type": "json_object"}
        result = self.llm.create_chat_completion(
            messages=messages, max_tokens=max_tokens, temperature=0.2,
            **kwargs)
        return result["choices"][0]["message"]["content"].strip()

    def decide(self, question: str) -> dict:
        """Ask the model which action to take; return {'action', 'answer'}."""
        messages = [{"role": "system", "content": form_system_prompt()}]
        messages.extend(self.history[-MAX_HISTORY_MESSAGES:])
        messages.append({"role": "user", "content": question})
        raw = self.chat(messages, flag_json=True)
        decision = take_json_object(raw)
        if decision is None:
            decision = {"action": "none", "answer": raw}
        action = str(decision.get("action", "none")).strip()
        if action not in D_ACTIONS:
            action = "none"
        return {"action": action, "answer": str(decision.get("answer", ""))}

    def comment_result(self, question: str, action: str, result: str) -> str:
        """Ask the model to comment the result of an executed action."""
        messages = [
            {"role": "system", "content":
                "You are a crystallography assistant. Comment briefly the "
                "result for the user: quality of the fit (chi-square), "
                "suspicious or correlated parameters, what to try next."},
            {"role": "user", "content":
                f"Request: {question}\nAction: {action}\nResult:\n{result[:6000]}"},
        ]
        return self.chat(messages)

    def answer(self, question: str, cryspy_object=None,
               callback_action: Optional[Callable[[str], None]] = None) -> dict:
        """Process the user question.

        Returns dict with keys 'text' (reply for the user) and
        'flag_object_changed' (the CrysPy object was modified).
        """
        decision = self.decide(question)
        action, text = decision["action"], decision["answer"]
        flag_object_changed = False
        if action != "none" and cryspy_object is not None:
            description, function, flag_object_changed = D_ACTIONS[action]
            if callback_action is not None:
                callback_action(action)
            result = function(cryspy_object)
            if action in ("refine", "calculate"):
                comment = self.comment_result(question, action, result)
                text = f"{result}\n\n{comment}"
            else:
                text = result if text == "" else f"{text}\n\n{result}"
        elif action != "none":
            text = "Open a file first: there is no CrysPy object to work with."
        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": text[:2000]})
        return {"text": text, "flag_object_changed": flag_object_changed,
                "action": action}

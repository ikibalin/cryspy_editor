"""Local LLM assistant for CrysPy Editor.

The model is any chat model in GGUF format loaded by llama-cpp-python
(optional dependency: pip install cryspy_editor[ai]). Nothing is sent
to the internet: the model file is chosen by the user and runs locally.
"""
import json
import os
from typing import Callable, Dict, List, Optional

import numpy

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
TOKENS_PER_MESSAGE = 8

# n_threads = 0 means all cores but one; n_gpu_layers = -1 means all layers
# on GPU (Metal on Apple Silicon, CUDA if llama-cpp-python is built with it)
DEFAULT_SETTINGS = {
    "n_ctx": 4096,
    "n_threads": 0,
    "n_gpu_layers": -1,
    "max_tokens": 512,
    "temperature": 0.2,
}

# (minimal RAM in GB, models, approximate size of the Q4_K_M file)
L_RECOMMENDED_MODELS = (
    (0, "Qwen2.5-1.5B-Instruct", "1 GB"),
    (8, "Qwen2.5-3B-Instruct, Llama-3.2-3B-Instruct", "2 GB"),
    (16, "Llama-3.1-8B-Instruct, Qwen2.5-7B-Instruct", "5 GB"),
    (32, "Qwen2.5-14B-Instruct", "9 GB"),
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


def format_parameter_name(name: tuple) -> str:
    """CrysPy variable name as text.

    (('global', ''), ('crystal', 'ho2ti2o7'), ('atom_site_susceptibility', ''),
    ('chi_11', 0)) -> 'crystal_ho2ti2o7.atom_site_susceptibility.chi_11[0]'
    """
    if len(name) == 3 and isinstance(name[0], str):
        # name from the dictionary pipeline (RhoChi result):
        # ('diffrn_x', 'extinction_radius', (0,)) -> 'diffrn_x.extinction_radius[0]'
        index = ", ".join(str(int(i)) for i in numpy.atleast_1d(name[2]))
        return f"{name[0]}.{name[1]}[{index}]"
    ls_part = []
    for part_name, part_label in name[:-1]:
        if part_name == "global":
            continue
        if part_label in (None, "", ()):
            ls_part.append(str(part_name))
        else:
            ls_part.append(f"{part_name}_{part_label}")
    param, index = name[-1][0], name[-1][1]
    if index in (None, "", ()):
        ls_part.append(str(param))
    elif isinstance(index, tuple):
        ls_part.append(f"{param}[{', '.join(str(i) for i in index)}]")
    else:
        ls_part.append(f"{param}[{index}]")
    return ".".join(ls_part)


def form_parameter_table(cryspy_object: cryspy.GlobalN) -> str:
    """Refined parameters with values and errors as a short text table."""
    ls_out = []
    for name in cryspy_object.get_variable_names():
        value = cryspy_object.get_variable_by_name(name)
        name_sigma = name[:-1] + ((name[-1][0] + "_sigma", name[-1][1]),)
        try:
            sigma = cryspy_object.get_variable_by_name(name_sigma)
            ls_out.append(f"{format_parameter_name(name)} = {value:.5f} +- {sigma:.5f}")
        except Exception:
            ls_out.append(f"{format_parameter_name(name)} = {value:.5f}")
    return "\n".join(ls_out)


def format_refinement_result(result: dict, cryspy_object: cryspy.GlobalN,
                             correlation_limit: float = 0.7) -> str:
    """Short text of a RhoChi result: chi-square, parameters, correlations.

    The full result holds the whole correlation matrix and long parameter
    names, which do not fit into the context of a small local model.
    """
    ls_out = []
    if "chi_sq" in result:
        ls_out.append(f"chi_sq = {float(result['chi_sq']):.5g}")
    table = form_parameter_table(cryspy_object)
    if table != "":
        ls_out.append("Refined parameters:\n" + table)
    names = result.get("parameter_name", [])
    matrix = result.get("correlation_matrix", None)
    if matrix is not None and len(names) == len(matrix):
        l_pair = []
        for ind_1 in range(len(names)):
            for ind_2 in range(ind_1 + 1, len(names)):
                value = float(matrix[ind_1][ind_2])
                if abs(value) >= correlation_limit:
                    l_pair.append((abs(value), value, ind_1, ind_2))
        l_pair.sort(reverse=True)
        if len(l_pair) > 0:
            ls_out.append(f"Correlations |r| >= {correlation_limit}:")
            for _, value, ind_1, ind_2 in l_pair[:20]:
                ls_out.append(
                    f"{format_parameter_name(names[ind_1])} - "
                    f"{format_parameter_name(names[ind_2])}: {value:.2f}")
        else:
            ls_out.append(f"No correlations with |r| >= {correlation_limit}.")
    return "\n".join(ls_out)


def action_refine(cryspy_object: cryspy.GlobalN) -> str:
    if len(cryspy_object.get_variable_names()) == 0:
        return "No parameters are marked for refinement."
    result = cryspy.rhochi_rietveld_refinement(cryspy_object)
    return "Refinement finished.\n" + format_refinement_result(result, cryspy_object)


def action_calculate(cryspy_object: cryspy.GlobalN) -> str:
    result = cryspy.rhochi_no_refinement(cryspy_object)
    return "Calculation finished.\n" + format_refinement_result(result, cryspy_object)


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
        self.history: List[Dict[str, str]] = []

    @property
    def model_name(self) -> str:
        return os.path.basename(self.model_path)

    def clear_history(self):
        self.history = []

    def chat(self, messages: List[Dict[str, str]],
             flag_json: bool = False) -> str:
        kwargs = {}
        if flag_json:
            kwargs["response_format"] = {"type": "json_object"}
        settings = getattr(self, "settings", DEFAULT_SETTINGS)
        messages = self.fit_messages(messages, settings["max_tokens"])
        result = self.llm.create_chat_completion(
            messages=messages, max_tokens=settings["max_tokens"],
            temperature=settings["temperature"], **kwargs)
        return result["choices"][0]["message"]["content"].strip()

    def count_tokens(self, text: str) -> int:
        return len(self.llm.tokenize(text.encode("utf-8"), add_bos=False))

    def fit_messages(self, messages: List[Dict[str, str]],
                     max_tokens: int) -> List[Dict[str, str]]:
        """Shorten messages so that the prompt and the answer fit the context.

        First the oldest history is dropped (the system message and the last
        message stay), then the longest message is cut from its end.
        """
        n_ctx = self.llm.n_ctx()
        # chat template adds a few tokens per message
        budget = n_ctx - max_tokens - TOKENS_PER_MESSAGE * len(messages) - 16
        if budget <= 0:
            raise ValueError(
                f"Maximal answer length ({max_tokens} tokens) does not leave "
                f"room for the question in the context of {n_ctx} tokens. "
                "Increase the context or decrease the answer length in "
                "AI assistant -> Load local model.")
        messages = [dict(message) for message in messages]
        l_tokens = [self.count_tokens(m["content"]) for m in messages]
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
            l_tokens[ind] = self.count_tokens(messages[ind]["content"])
            if len(content) < 16:
                break
        return messages

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
                f"Request: {question}\nAction: {action}\nResult:\n{result}"},
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

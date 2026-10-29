"""Local LLM assistant for CrysPy Editor, without Qt.

The model is any chat model in GGUF format loaded by llama-cpp-python
(optional dependency: pip install cryspy_editor[ai]), or a model of Ollama
or of another server (assistant_models.ServerModel). Nothing is sent to
the internet: the model file is chosen by the user and runs locally.

The structure is the one of the assistant of PyColl5 (assistant.py,
assistant_tools.py, ui_assistant.py): LocalModel talks to the model,
Assistant asks it for actions in JSON and runs them; only the tools differ
(here the tools of CrysPy).
"""
import json
import os
import re
from typing import Callable, Dict, List, Optional

from cryspy_editor.widgets.assistant_agent import (
    ASK_ACTION,
    MAX_AGENT_STEPS,
    Agent,
    form_step_result_text,
    form_steps_text,
)
from cryspy_editor.widgets.assistant_commands import (
    form_capabilities_text,
    is_capability_question,
    parse_command,
    parse_command_arguments,
    take_recipe_names,
)
from cryspy_editor.widgets.assistant_dialog import ALL_INFORMATION, Dialog, is_cancel
from cryspy_editor.widgets.assistant_tools import (
    D_TOOLS,
    form_object_recipes_text,
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
    "A GGUF model file needs the optional package llama-cpp-python.\n"
    "Install it with:\n    pip install cryspy_editor[ai]\n"
    "or\n    pip install llama-cpp-python\n"
    "pip compiles it, so install a C/C++ compiler first:\n"
    "  Windows: Build Tools for Visual Studio, 'Desktop development with C++'\n"
    "  macOS: xcode-select --install\n"
    "  Linux: gcc, g++ and make (e.g. build-essential)\n"
    "Without a compiler use Ollama (https://ollama.com) instead: choose\n"
    "Ollama in Source of the model settings; llama-cpp-python is not needed."
)

MAX_HISTORY_MESSAGES = 10
TOKENS_PER_MESSAGE = 8
MAX_STEPS = 6  # actions for one request
MAX_RETRIES = 2  # the model corrects the actions with an error in their arguments
N_MAX_RESULT = 3000  # characters of a result of a tool given to the model
N_MAX_HISTORY = 2000  # characters of a reply kept in the chat history
N_MIN_CUT_TOKENS = 64  # messages longer than this are cut before the system message
ANSWER_KEYS = ("answer", "message", "reply", "text")  # the answer in the reply of the model
# actions that start the agent loop (assistant_agent.py): a recipe of CrysPy,
# or a task whose next steps depend on the results
STEP_BY_STEP = "work_step_by_step"
WRITE_RECIPE = "get_recipe_guide"  # a recipe for the CookBook written from the words of the user
AGENT_ACTIONS = ("get_recipe", "use_recipe", STEP_BY_STEP, WRITE_RECIPE, ASK_ACTION)
NO_MODEL = ("No model is loaded (AI assistant -> Load model). Without it type @name to run a recipe "
            "or an action of CrysPy, or ask 'what can you do?'.")
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

# an answer that announces the next step of the work ("I will check the
# attributes..."): the request is not finished, the agent loop goes on
RE_MORE = re.compile(
    r"\b(I will|I'll|I am going to|I'm going to|let me|next,? I|now I|I need to|I have to)\s+(?!not\b)\w"
    r"|^\s*(я\s+)?(проверю|посмотрю|добавлю|сделаю|найду|узнаю|определю)\b"
    r"|\bсейчас\s+(я\s+)?(проверю|посмотрю|добавлю|сделаю|найду|узнаю|определю)\b"
    r"|\b(je vais|ich werde)\b",
    re.IGNORECASE)

# n_threads = 0 means all cores but one; n_gpu_layers = -1 means all layers
# on GPU (Metal on Apple Silicon, CUDA if llama-cpp-python is built with it)
DEFAULT_SETTINGS = {
    "n_ctx": 4096,
    "n_threads": 0,
    "n_gpu_layers": -1,
    "max_tokens": 512,
    "temperature": 0.2,
    "max_steps": MAX_AGENT_STEPS,
    "thinking": False,  # a thinking model (qwen3, deepseek-r1) thinks before each answer
    "max_thinking_tokens": 2048,  # then the thinking is stopped and the model decides
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
step-by-step refinement) is done one action at a time. When the user describes
the steps or the rule of decisions himself (e.g. "refine each parameter in turn
and keep it if chi_sq gets better"), give the single action "{STEP_BY_STEP}" {{}}:
the steps of the user are followed, never a recipe instead of them. When the
user only names the task (e.g. "refine the structure step by step"), give the
single action "get_recipe" with the name of the recipe that fits. Recipes:
{form_recipes_text()}
When no recipe fits such a task, give the single action "{STEP_BY_STEP}" {{}}.{form_write_recipe_rule()}"""
    s_state = "\nNo file is opened now."
    if cryspy_object is not None:
        l_name = [str(getattr(item, "data_name", type(item).__name__))
                  for item in getattr(cryspy_object, "items", [])]
        s_state = (f"\nThe opened file has {len(l_name)} data blocks: "
                   f"{', '.join(l_name)}." if l_name else "\nThe opened file is empty.")
        s_object_recipe = form_object_recipes_text(cryspy_object) if s_recipe else ""
        if s_object_recipe:
            s_recipe += f"\nThe experiments of the opened file and their recipes:\n{s_object_recipe}"
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
Editor it is done); never write that something is done, applied or set.{form_methods_rule()}{s_recipe}

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


def form_methods_rule() -> str:
    """The rule for the methods of the objects (CrysPy tools list_methods,
    call_method): an operation the user names that is not an action."""
    if "call_method" not in D_TOOLS:
        return ""
    return """
The data blocks, loops and items of the file have methods (e.g.
define_background_points of a powder experiment): an operation the user names
that is not an action is looked up with "list_methods" {"pattern": "<a word of
it>"} and done with "call_method" {"method": "<name>", <its arguments>}."""


def form_write_recipe_rule() -> str:
    """The rule of the first reply for a request to write a recipe."""
    if WRITE_RECIPE not in D_TOOLS:
        return ""
    return f"""
When the user asks to write (compose, make) a recipe for the CookBook from an
algorithm described in words, give the single action "{WRITE_RECIPE}" {{}}: the
recipe is written step by step, with questions to the user when needed."""


def take_action_names() -> list:
    """Names of the actions of the first reply of the model."""
    l_name = list(D_TOOLS)
    if "get_recipe" in D_TOOLS:
        l_name.append(STEP_BY_STEP)
    return l_name


def form_agent_examples() -> str:
    if "get_recipe" not in D_TOOLS:
        return ""
    s_out = f"""
- refine the structure step by step:
  [{{"action": "get_recipe", "arguments": {{"name": "refine_structure"}}}}]
- go through the parameters one by one, refine each and keep it only if chi_sq gets better:
  [{{"action": "{STEP_BY_STEP}", "arguments": {{}}}}]"""
    if "suggest_recipes" in D_TOOLS:
        s_out += """
- analyse all the data of the file by the recipes:
  [{"action": "get_recipe", "arguments": {"name": "choose_recipes"}}]"""
    if "call_method" in D_TOOLS:
        s_out += """
- define the background points of the powder experiments:
  [{"action": "call_method", "arguments": {"method": "define_background_points"}}]"""
    if WRITE_RECIPE in D_TOOLS:
        s_out += f"""
- write a recipe: fix all, refine the scale, then the positions, undo when R_F2 is worse:
  [{{"action": "{WRITE_RECIPE}", "arguments": {{}}}}]"""
    return s_out


def fit_messages(messages: list, max_tokens: int, n_ctx: int, count_tokens: Callable) -> list:
    """Shorten the messages so that the prompt and the answer fit the
    context of n_ctx tokens: first the oldest history is dropped (the
    system message and the last message stay), then the longest message is
    cut from its end; the system message (the actions and the rules of the
    answer) only when the others are short, and in its middle, so that the
    rules at its end stay."""
    budget = n_ctx - max_tokens - TOKENS_PER_MESSAGE * len(messages) - 16  # the chat template adds a few
    if budget <= 0:
        raise ValueError(
            f"The maximal answer length ({max_tokens} tokens) leaves no room for the question in the context "
            f"of {n_ctx} tokens. Increase the context or decrease the answer length in "
            "AI assistant -> Load model.")
    messages = [dict(message) for message in messages]
    l_tokens = [count_tokens(message["content"]) for message in messages]
    while sum(l_tokens) > budget and len(messages) > 2:
        del messages[1], l_tokens[1]
    while sum(l_tokens) > budget:
        l_index = [i for i in range(1, len(messages)) if l_tokens[i] > N_MIN_CUT_TOKENS] or range(len(messages))
        ind = max(l_index, key=lambda i: l_tokens[i])
        excess = sum(l_tokens) - budget
        content = messages[ind]["content"]
        n_keep = max(0, int(len(content) * (1 - (excess + 8) / l_tokens[ind])) - 1)
        if n_keep == 0 or n_keep >= len(content):
            n_keep = len(content) // 2
        if ind == 0:  # the rules of the answer are at the end of the system message: the middle is cut
            n_tail = min(len(content) // 4, n_keep // 2)
            messages[0]["content"] = content[:n_keep - n_tail] + "\n[...cut...]\n" + content[len(content) - n_tail:]
        else:
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


def announces_more(answer: str) -> bool:
    """The answer says what the assistant will do next instead of the
    result ("I will check the attributes and add..."): small models answer
    so after the first actions of a request that needs several."""
    return bool(RE_MORE.search(answer or ""))


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
        from cryspy_editor.widgets.assistant_models import take_gguf_thinking
        self.flag_thinking_model = take_gguf_thinking(model_path)
        self.on_thinking = None  # set by the window: see ServerModel
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

    @property
    def flag_thinking(self) -> bool:
        """The model thinks before each answer: its thinking is shown."""
        return getattr(self, "flag_thinking_model", False) and self.settings.get("thinking", False)

    def chat(self, messages: List[Dict[str, str]], flag_json: bool = False,
             schema: Optional[dict] = None, flag_think: Optional[bool] = None) -> str:
        """Reply of the model; with flag_json it is a JSON object, with
        schema it follows the JSON schema (grammar of llama.cpp). A grammar
        lets the model write only JSON, so a thinking model gets none: its
        <think> block goes to on_thinking as it comes and the JSON is found
        after it. A thinking longer than max_thinking_tokens is stopped and
        the model answers from it (flag_think False: that answer)."""
        from cryspy_editor.widgets.assistant_models import (
            add_thinking_rule,
            form_cut_text,
            form_decide_messages,
            form_stop_text,
            split_thinking,
        )
        flag_thinking = self.flag_thinking if flag_think is None else flag_think
        kwargs = {}
        if flag_json and not flag_thinking:
            kwargs["response_format"] = {"type": "json_object"}
            if schema is not None:
                kwargs["response_format"]["schema"] = schema
        max_tokens = self.settings["max_tokens"]
        messages = fit_messages(messages, max_tokens, self.llm.n_ctx(), self.count_tokens)
        if not flag_thinking:
            result = self.llm.create_chat_completion(
                messages=messages, max_tokens=max_tokens,
                temperature=self.settings["temperature"], **kwargs)
            text = result["choices"][0]["message"]["content"] or ""
            if flag_think is False:  # a <think> block written in spite of the request
                text = split_thinking(text)[1]
            return text.strip()
        max_thinking_tokens = self.settings["max_thinking_tokens"]
        on_thinking = getattr(self, "on_thinking", None) or (lambda text: None)
        on_thinking("")
        chunks = self.llm.create_chat_completion(
            messages=add_thinking_rule(messages, max_thinking_tokens), max_tokens=max_tokens,
            temperature=self.settings["temperature"], stream=True)
        text, n_thinking, finish_reason, flag_stopped = "", 0, None, False
        try:
            for chunk in chunks:
                d_choice = chunk["choices"][0]
                finish_reason = d_choice.get("finish_reason") or finish_reason
                delta = d_choice.get("delta", {}).get("content") or ""
                if "</think>" in text:  # the answer
                    text += delta
                    continue
                text += delta
                if "</think>" in text:
                    on_thinking(delta.split("</think>", 1)[0])
                    continue
                on_thinking(delta.replace("<think>", ""))
                n_thinking += 1  # a chunk is a token
                if n_thinking > max_thinking_tokens:
                    flag_stopped = True
                    break
        finally:
            if hasattr(chunks, "close"):
                chunks.close()
        if flag_stopped:
            on_thinking(form_stop_text(max_thinking_tokens))
            thinking = text.replace("<think>", "", 1)
            return self.chat(form_decide_messages(messages, thinking), flag_json, schema, flag_think=False)
        thinking, answer = split_thinking(text)
        if "</think>" not in text and "<think>" in text:  # cut inside the thinking
            answer = ""
        if answer == "" and finish_reason == "length":
            raise ValueError(form_cut_text(max_tokens))
        return answer


class Assistant:
    """Chat with a model (an object with chat(messages, flag_json) -> str,
    such as LocalModel) that chooses the actions of CrysPy."""

    def __init__(self, model):
        self.model = model
        self.history: List[Dict[str, str]] = []
        self.dialog: Optional[Dialog] = None  # questions of an action to the user
        self.flag_dialog_changed = False  # the action of the dialog changes the CrysPy object
        self.flag_stop = False  # set from the window (request_stop): the agent loop stops
        self.agent: Optional[Agent] = None  # the agent loop that waits for the answers of the dialog

    @property
    def model_name(self) -> str:
        return getattr(self.model, "model_name", "model")

    @property
    def model_path(self) -> str:
        return getattr(self.model, "model_path", "")

    def clear_history(self):
        self.history = []
        self.dialog = None
        self.agent = None

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

    def answer_dialog(self, answer: str, on_action: Optional[Callable] = None,
                      on_step: Optional[Callable] = None) -> dict:
        """The answer of the user to the question of the dialog: read without
        the model; the action is done when all values are known. When the
        dialog was asked by the agent loop (e.g. ask_user in the middle of
        writing a recipe), the loop goes on with the result of the action."""
        dialog = self.dialog
        name, l_action = dialog.name, []
        if is_cancel(answer):
            self.dialog, self.agent = None, None
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
                elif self.agent is not None:
                    return self.resume_agent(answer, message, result, on_action, on_step)
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

    def ask(self, question: str, cryspy_object=None, on_action: Optional[Callable] = None,
            on_step: Optional[Callable] = None) -> dict:
        """Process a request: the model chooses the actions (at most
        MAX_STEPS) and the answer at once; after the actions of a question
        (assistant_tools.is_answer_tool) it answers from their results.
        on_action(name): called before each action; on_step(text): the steps
        of the work by a recipe as they go (see ask_step_by_step).

        Returns {"text": reply for the user, "actions": [(name, arguments,
        result), ...], "flag_object_changed": the CrysPy object was
        modified, "question": the assistant asks a question (a tool returned
        an assistant_dialog.Dialog); the next request is its answer}."""
        if self.dialog is not None:
            return self.answer_dialog(question, on_action, on_step)
        if is_capability_question(question):
            text = form_capabilities_text()
            self._remember(question, text)
            return {"text": text, "actions": [], "flag_object_changed": False, "question": False}
        command = parse_command(question)
        if command is not None:
            return self.run_command(command[0], command[1], question, cryspy_object, on_action, on_step)
        if self.model is None:
            return {"text": NO_MODEL, "actions": [], "flag_object_changed": False, "question": False}
        messages = [{"role": "system", "content": form_system_prompt(cryspy_object)}]
        messages.extend(self.history[-MAX_HISTORY_MESSAGES:])
        messages.append({"role": "user", "content": question})
        raw = self.model.chat(messages, flag_json=True)
        decision = take_decision(raw)
        if any(action in AGENT_ACTIONS for action, _ in decision["actions"]) and "get_recipe" in D_TOOLS:
            return self.ask_step_by_step(question, cryspy_object, decision["actions"], on_action, on_step)
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
        if self.dialog is None and not flag_failed and announces_more(answer) and "get_recipe" in D_TOOLS:
            # "I will check ... and add ...": the work goes on step by step from these results
            return self.ask_step_by_step(question, cryspy_object, [], on_action, on_step,
                                         l_done=l_action, flag_changed=flag_object_changed)
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

    def run_command(self, name: str, text: str, question: str, cryspy_object,
                    on_action: Optional[Callable] = None, on_step: Optional[Callable] = None) -> dict:
        """'@name text' (assistant_commands): a recipe or an action without
        the model choosing it; a recipe runs literally without a model."""
        if name in take_recipe_names():
            if self.model is not None:
                request = text or f"Follow the recipe {name} for the opened file."
                return self.ask_step_by_step(request, cryspy_object, [("get_recipe", {"name": name})],
                                             on_action, on_step)
            return self.run_recipe_without_model(name, question, cryspy_object, on_step)
        if name not in D_TOOLS:
            text = (f"Error: '@{name}' is neither a recipe nor an action. Type @ to see the names, "
                    "or ask 'what can you do?'.")
            return {"text": text, "actions": [], "flag_object_changed": False, "question": False}
        try:
            arguments = parse_command_arguments(name, text)
        except ValueError as error:
            return {"text": f"Error: {error}.", "actions": [], "flag_object_changed": False,
                    "question": False}
        if on_action is not None:
            on_action(name)
        result, flag_changed = run_tool(name, cryspy_object, arguments, flag_user=True)
        if isinstance(result, Dialog):  # the next requests are the answers to its questions
            self.dialog = result
            self.flag_dialog_changed = bool(getattr(D_TOOLS.get(name), "flag_object_changed", flag_changed))
            result = result.start()
            flag_changed = False
        text = f"[{name}] {result}"
        self._remember(question, text)
        return {"text": text, "actions": [(name, arguments, result)],
                "flag_object_changed": flag_changed and not result.startswith("Error"),
                "question": self.is_asking()}

    def run_recipe_without_model(self, name: str, question: str, cryspy_object,
                                 on_step: Optional[Callable] = None) -> dict:
        """The recipe as it is written (cryspy.run_recipe): every step is
        shown when it is done."""
        from cryspy import run_recipe
        if cryspy_object is None:
            return {"text": "Error: no file is opened.", "actions": [], "flag_object_changed": False,
                    "question": False}
        self.flag_stop = False

        def show_step(step_name, status, text):
            if on_step is not None:
                on_step(f"Step {step_name}: {status}\n{form_step_result_text(step_name, text)}")

        result = run_recipe(cryspy_object, name, callback=show_step)
        text = f"No model is loaded: the recipe {name} was run as it is written.\n{result['text']}"
        self._remember(question, text)
        return {"text": text, "actions": [(name, {}, result["text"])], "flag_object_changed": True,
                "question": False}

    def ask_step_by_step(self, question: str, cryspy_object, l_first: list,
                         on_action: Optional[Callable] = None,
                         on_step: Optional[Callable] = None, l_done: Optional[list] = None,
                         flag_changed: bool = False) -> dict:
        """The request is done by the agent loop (assistant_agent.Agent):
        one action at a time, each chosen after the result of the previous
        one. l_first: the actions chosen already (get_recipe); l_done:
        [(name, arguments, result)] of the actions done already for this
        request (flag_changed: they changed the object). on_step(text):
        the steps are shown to the user as they go; the reply then has only
        the end (its "text"), the history of the chat keeps all."""
        self.flag_stop = False
        l_first = [(action, arguments) for action, arguments in l_first
                   if action in AGENT_ACTIONS and action != STEP_BY_STEP][:1]
        max_steps = getattr(self.model, "settings", {}).get("max_steps", MAX_AGENT_STEPS)
        l_action = list(D_TOOLS)
        if len(l_first) == 0:  # the steps of the user, not a recipe: no recipe in the middle of them
            l_action = [action for action in l_action if action != "get_recipe"]
        elif l_first[0][0] == WRITE_RECIPE:  # writing a recipe changes nothing in the file
            l_action = [action for action in l_action if not D_TOOLS[action].flag_object_changed]
        agent = Agent(self.model, run_tool, l_action, take_json_object, max_steps=max_steps)
        out = agent.run(form_system_prompt(cryspy_object), self.history[-MAX_HISTORY_MESSAGES:], question,
                        cryspy_object, on_action=on_action, should_stop=lambda: self.flag_stop,
                        l_first=l_first, on_step=on_step, l_done=l_done)
        out["flag_object_changed"] = out["flag_object_changed"] or flag_changed
        return self.form_agent_reply(agent, question, out, on_step)

    def resume_agent(self, answer: str, message: str, result: str, on_action: Optional[Callable] = None,
                     on_step: Optional[Callable] = None) -> dict:
        """The agent loop goes on after the user answered all questions of
        its dialog: result is the text of the action done with the answers."""
        agent, self.agent = self.agent, None
        self.flag_stop = False
        message = message.replace(f"\n{ALL_INFORMATION}", "")
        if on_step is not None:
            on_step(message)
        out = agent.resume(result, flag_changed=self.flag_dialog_changed, on_action=on_action,
                           should_stop=lambda: self.flag_stop, on_step=on_step)
        reply = self.form_agent_reply(agent, answer, out, on_step)
        if on_step is None:
            reply["text"] = f"{message}\n\n{reply['text']}"
        return reply

    def form_agent_reply(self, agent: Agent, question: str, out: dict,
                         on_step: Optional[Callable] = None) -> dict:
        """The reply of the agent loop (Agent.run or resume); a loop that
        asks the user waits in self.agent for the answers."""
        l_action = [(action, arguments, result) for _, action, arguments, result in out["steps"]]
        answer = out["answer"]
        if out["dialog"] is not None:
            self.dialog, self.agent = out["dialog"], agent
            self.flag_dialog_changed = bool(getattr(D_TOOLS.get(self.dialog.name), "flag_object_changed", True))
            answer = ""
        elif not any(not str(result).startswith("Error") for _, _, result in l_action) and claims_done(answer):
            answer = NOTHING_DONE
        ls_out = []
        if out["stopped"]:
            ls_out.append(f"{out['stopped']} The results above are those of the actions done.")
        if answer:
            ls_out.append(answer)
        s_steps = form_steps_text(out["steps"]) if out["steps"] else ""
        text_all = "\n\n".join([s_steps] + ls_out if s_steps else ls_out) or "No answer: try to ask in other words."
        self._remember(question, text_all)
        text = text_all
        if self.agent is not None:  # the questions of the dialog are the reply
            text = self.dialog.start() if on_step is not None else text_all
        elif on_step is not None:  # the steps are shown already
            text = "\n\n".join(ls_out) or ("Done." if out["steps"] else text_all)
        return {"text": text, "actions": l_action, "flag_object_changed": out["flag_object_changed"],
                "question": self.is_asking()}

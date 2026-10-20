"""Local LLM assistant for CrysPy Editor.

The model is any chat model in GGUF format loaded by llama-cpp-python
(optional dependency: pip install cryspy_editor[ai]). Nothing is sent
to the internet: the model file is chosen by the user and runs locally.
"""
import json
import os
from typing import Callable, Dict, List, Optional

# tools and help pages are in CrysPy, the editor only talks to the model
from cryspy import assistant_tools_as_text, call_assistant_tool

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
# tool calls for one question: e.g. refine_parameters, refine, answer
MAX_TOOL_CALLS = 4
# characters of a tool result kept in the chat history
MAX_RESULT_IN_HISTORY = 2000

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


def form_system_prompt() -> str:
    s_tools = assistant_tools_as_text()
    return f"""You are the assistant of CrysPy Editor, a program for crystallographic
analysis of neutron and X-ray diffraction data with the CrysPy library.
The user may have a CrysPy object loaded (crystal structures, experiments, data).

You can call one tool of CrysPy per reply:
{s_tools}

Rules:
- For questions on how to describe something in rcif or what a category
  means (thermal vibrations, multipoles, extinction, twins, ...), call
  get_help first and answer from its text only.
- To change or refine the model use the tools; never invent results.
- After a tool result you may call another tool or give the final answer.

Respond ONLY with a JSON object:
{{"tool": "<tool name or none>", "arguments": {{...}}, "answer": "<short text for the user>"}}
Use "tool": "none" for the final answer."""


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

    def decide(self, messages: List[Dict[str, str]]) -> dict:
        """Ask the model for the next step: {'tool', 'arguments', 'answer'}."""
        raw = self.chat(messages, flag_json=True)
        decision = take_json_object(raw)
        if decision is None:
            return {"tool": "none", "arguments": {}, "answer": raw, "raw": raw}
        # "action" is the key of the first version of the prompt
        tool = str(decision.get("tool", decision.get("action", "none"))).strip()
        if tool == "":
            tool = "none"
        arguments = decision.get("arguments", {})
        if not isinstance(arguments, dict):
            arguments = {}
        return {"tool": tool, "arguments": arguments,
                "answer": str(decision.get("answer", "")), "raw": raw}

    def answer(self, question: str, cryspy_object=None,
               callback_action: Optional[Callable[[str], None]] = None) -> dict:
        """Process the user question with the tools of CrysPy.

        Returns dict with keys 'text' (reply for the user),
        'flag_object_changed' (the CrysPy object was modified) and
        'tools' (names of the called tools).
        """
        messages = [{"role": "system", "content": form_system_prompt()}]
        messages.extend(self.history[-MAX_HISTORY_MESSAGES:])
        messages.append({"role": "user", "content": question})
        ls_result, l_tool = [], []
        flag_object_changed = False
        answer = ""
        for _ in range(MAX_TOOL_CALLS + 1):
            decision = self.decide(messages)
            tool, answer = decision["tool"], decision["answer"]
            if tool.lower() == "none" or len(l_tool) >= MAX_TOOL_CALLS:
                break
            if callback_action is not None:
                callback_action(tool)
            result = call_assistant_tool(
                cryspy_object, tool, decision["arguments"])
            flag_object_changed = flag_object_changed or \
                result["flag_object_changed"]
            l_tool.append(tool)
            ls_result.append(f"[{tool}]\n{result['text']}")
            messages.append({"role": "assistant", "content": decision["raw"]})
            messages.append({"role": "user", "content":
                f"Result of {tool}:\n{result['text']}\n\n"
                "Call another tool if needed, otherwise give the final "
                "answer with \"tool\": \"none\"."})
        text = "\n\n".join(ls_result + ([answer] if answer != "" else []))
        if text == "":
            text = "(no answer)"
        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant",
                             "content": text[:MAX_RESULT_IN_HISTORY]})
        return {"text": text, "flag_object_changed": flag_object_changed,
                "tools": l_tool}

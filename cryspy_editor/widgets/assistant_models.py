"""Models of the AI assistant other than the GGUF file, and the context
length, without Qt.

- read_gguf_metadata: the header of a GGUF file (context length the model
  was trained with, layers, attention heads), read without llama.cpp.
- take_context_range: the context the model accepts, how much of it fits in
  the memory of this computer and the recommended value.
- ServerModel: a chat model served by Ollama or by an OpenAI-compatible
  server (LM Studio, llama.cpp server, ...) on this or another computer. It
  has the methods of LocalModel (chat, count_tokens, close), so the
  assistant and the agent work with it as with a local GGUF file. Only the
  standard library is used (urllib): no new packages.
"""
import json
import os
import struct
import urllib.error
import urllib.request
from typing import Dict, List, Optional

SOURCE_GGUF = "gguf"
SOURCE_OLLAMA = "ollama"
SOURCE_OPENAI = "openai"
D_SOURCE_NAMES = {
    SOURCE_GGUF: "Local GGUF file (llama-cpp-python)",
    SOURCE_OLLAMA: "Ollama",
    SOURCE_OPENAI: "OpenAI-compatible server (LM Studio, llama.cpp server, vLLM)",
}
D_DEFAULT_URL = {SOURCE_OLLAMA: "http://localhost:11434", SOURCE_OPENAI: "http://localhost:1234/v1"}

MIN_CONTEXT = 2048
RECIPE_CONTEXT = 8192  # the step-by-step work by recipes needs this or more
MAX_RECOMMENDED_CONTEXT = 32768  # a longer prompt makes every answer slow
MEMORY_FRACTION = 0.75  # of the memory, for the model and its context
OVERHEAD_GB = 0.5  # compute buffers of llama.cpp
CHARACTERS_PER_TOKEN = 3.  # a token is about 3-4 characters: count tokens with a margin
TIMEOUT_CHAT = 600
TIMEOUT_INFO = 10

# value types of the GGUF metadata: struct format and size
D_GGUF_TYPES = {0: ("<B", 1), 1: ("<b", 1), 2: ("<H", 2), 3: ("<h", 2), 4: ("<I", 4), 5: ("<i", 4),
                6: ("<f", 4), 7: ("<?", 1), 10: ("<Q", 8), 11: ("<q", 8), 12: ("<d", 8)}
GGUF_STRING, GGUF_ARRAY = 8, 9
# metadata keys (after "<architecture>.") needed for the context
L_ARCH_KEYS = ("context_length", "block_count", "embedding_length", "attention.head_count",
               "attention.head_count_kv", "attention.key_length", "attention.value_length")


def _read_gguf_value(file, value_type: int, flag_keep: bool = True):
    if value_type in D_GGUF_TYPES:
        fmt, size = D_GGUF_TYPES[value_type]
        return struct.unpack(fmt, file.read(size))[0]
    if value_type == GGUF_STRING:
        length = struct.unpack("<Q", file.read(8))[0]
        data = file.read(length)
        return data.decode("utf-8", errors="replace") if flag_keep else None
    if value_type == GGUF_ARRAY:
        item_type, length = struct.unpack("<IQ", file.read(12))
        if item_type in D_GGUF_TYPES:  # skipped at once
            file.seek(D_GGUF_TYPES[item_type][1] * length, os.SEEK_CUR)
        else:  # strings (the vocabulary) or nested arrays
            for _ in range(length):
                _read_gguf_value(file, item_type, flag_keep=False)
        return None
    raise ValueError(f"Unknown GGUF value type {value_type}.")


def read_gguf_metadata(file_name: str) -> dict:
    """Metadata of a GGUF model needed for its context: 'architecture' and
    the keys of L_ARCH_KEYS (without the architecture prefix), for those
    present in the file. Reading stops when all of them are found.
    Raises ValueError for a file that is not GGUF."""
    d_meta = {}
    with open(file_name, "rb") as file:
        if file.read(4) != b"GGUF":
            raise ValueError(f"'{file_name}' is not a GGUF file.")
        version = struct.unpack("<I", file.read(4))[0]
        if version < 2:
            raise ValueError(f"GGUF version {version} is not supported.")
        _, n_kv = struct.unpack("<QQ", file.read(16))
        arch = None
        for _ in range(n_kv):
            key = _read_gguf_value(file, GGUF_STRING)
            value_type = struct.unpack("<I", file.read(4))[0]
            value = _read_gguf_value(file, value_type)
            if key == "general.architecture":
                arch = value
                d_meta["architecture"] = value
            elif "." in key and value is not None:
                prefix, name = key.split(".", 1)
                if name in L_ARCH_KEYS and (arch is None or prefix == arch):
                    d_meta[name] = value
            if arch is not None and all(name in d_meta for name in L_ARCH_KEYS):
                break
    return d_meta


def calc_kv_bytes_per_token(d_meta: dict) -> Optional[float]:
    """Memory of the context (keys and values in f16) for one token, from
    the metadata of the model; None when the metadata is not enough."""
    try:
        n_layer = int(d_meta["block_count"])
        n_head = int(d_meta["attention.head_count"])
        n_head_kv = int(d_meta.get("attention.head_count_kv", n_head))
        head_dim = int(d_meta.get("embedding_length", 0)) // n_head
        key_length = int(d_meta.get("attention.key_length", head_dim))
        value_length = int(d_meta.get("attention.value_length", head_dim))
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None
    if n_layer <= 0 or key_length + value_length <= 0:
        return None
    return 2. * n_layer * n_head_kv * (key_length + value_length)


def take_context_range(d_meta: dict, model_size_gb: Optional[float],
                       memory_gb: Optional[float]) -> dict:
    """Context of the model for this computer.

    Returns dict with 'n_train' (the context the model is trained with, None
    if unknown: the largest value that makes sense), 'n_memory' (the largest
    context that fits in MEMORY_FRACTION of the memory with the model,
    None if unknown) and 'n_recommended' (a multiple of 1024 not larger than
    both and than MAX_RECOMMENDED_CONTEXT, at least MIN_CONTEXT)."""
    n_train = d_meta.get("context_length")
    n_train = int(n_train) if isinstance(n_train, (int, float)) and n_train > 0 else None
    n_memory = None
    kv_bytes = calc_kv_bytes_per_token(d_meta)
    if kv_bytes is not None and memory_gb is not None:
        free_gb = MEMORY_FRACTION * memory_gb - (model_size_gb or 0.) - OVERHEAD_GB
        n_memory = max(0, int(free_gb * 1024**3 / kv_bytes))
    l_limit = [MAX_RECOMMENDED_CONTEXT] + [n for n in (n_train, n_memory) if n is not None]
    n_recommended = max(MIN_CONTEXT, min(l_limit) // 1024 * 1024)
    if n_train is not None:
        n_recommended = min(n_recommended, n_train)
    return {"n_train": n_train, "n_memory": n_memory, "n_recommended": n_recommended}


def form_context_text(d_range: dict, memory_gb: Optional[float]) -> str:
    """Explanation of the context range for the dialog of the settings."""
    n_train, n_memory = d_range["n_train"], d_range["n_memory"]
    if n_train is None:
        s_model = "The trained context of this model is unknown."
    else:
        s_model = f"This model accepts a context from {MIN_CONTEXT} to {n_train} tokens."
    if n_memory is None:
        s_memory = ""
    elif n_train is not None and n_memory >= n_train:
        s_memory = f" With {memory_gb:.0f} GB of memory the whole context fits."
    else:
        s_memory = f" With {memory_gb:.0f} GB of memory up to about {n_memory} tokens fit."
    s_recipe = ""
    if d_range["n_recommended"] < RECIPE_CONTEXT:
        s_recipe = f" Step-by-step recipes need {RECIPE_CONTEXT} or more."
    return (f"{s_model}{s_memory} Recommended for this computer: {d_range['n_recommended']} "
            f"(longer is slower).{s_recipe}")


def take_gguf_context(file_name: str, memory_gb: Optional[float]) -> Optional[dict]:
    """take_context_range of a GGUF file, None if it cannot be read."""
    try:
        d_meta = read_gguf_metadata(file_name)
        size_gb = os.path.getsize(file_name) / 1024**3
    except (OSError, ValueError, struct.error):
        return None
    return take_context_range(d_meta, size_gb, memory_gb)


def _request_json(url: str, data: Optional[dict] = None, timeout: float = TIMEOUT_INFO) -> dict:
    body = None if data is None else json.dumps(data).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"},
        method="GET" if data is None else "POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")[:500]
        raise ConnectionError(f"The server answered {error.code}: {message}") from error
    except (urllib.error.URLError, OSError) as error:
        raise ConnectionError(
            f"No connection to {url}: {getattr(error, 'reason', error)}. Is the server running?") from error


def list_server_models(source: str, url: str) -> List[str]:
    """Names of the models of the server. Raises ConnectionError."""
    url = url.rstrip("/")
    if source == SOURCE_OLLAMA:
        return [d_model["name"] for d_model in _request_json(f"{url}/api/tags").get("models", [])]
    return [d_model["id"] for d_model in _request_json(f"{url}/models").get("data", [])]


def take_ollama_capabilities(url: str, model: str) -> List[str]:
    """Capabilities of an Ollama model from /api/show ('completion', 'tools',
    'thinking', ...); empty when the server does not tell them."""
    try:
        return list(_request_json(f"{url.rstrip('/')}/api/show", {"model": model}).get("capabilities", []))
    except ConnectionError:
        return []


def take_ollama_context(url: str, model: str, memory_gb: Optional[float]) -> Optional[dict]:
    """take_context_range of an Ollama model from /api/show; None when the
    server does not tell it."""
    url = url.rstrip("/")
    try:
        d_info = _request_json(f"{url}/api/show", {"model": model}).get("model_info", {})
        size = next((d_model.get("size", 0) for d_model in _request_json(f"{url}/api/tags").get("models", [])
                     if d_model.get("name") == model), 0)
    except ConnectionError:
        return None
    arch = d_info.get("general.architecture", "")
    d_meta = {name: d_info[f"{arch}.{name}"] for name in L_ARCH_KEYS if f"{arch}.{name}" in d_info}
    if "context_length" not in d_meta:
        return None
    return take_context_range(d_meta, size / 1024**3, memory_gb)


class ServerModel:
    """A chat model of Ollama or of an OpenAI-compatible server.

    settings: those of the assistant (n_ctx, max_tokens, temperature); the
    context n_ctx is given to Ollama as num_ctx."""

    def __init__(self, source: str, url: str, model: str, settings: Optional[dict] = None):
        from cryspy_editor.widgets.assistant import take_settings
        if source not in (SOURCE_OLLAMA, SOURCE_OPENAI):
            raise ValueError(f"Unknown model server '{source}'.")
        if model.strip() == "":
            raise ValueError("Give the name of the model of the server.")
        self.source = source
        self.url = (url.strip() or D_DEFAULT_URL[source]).rstrip("/")
        self.model = model.strip()
        self.settings = take_settings(settings)
        self.model_path = ""  # no file: see model_name
        list_server_models(source, self.url)  # fails now, not at the first question
        # a thinking model (qwen3, deepseek-r1, ...) would spend max_tokens on
        # thinking and leave the answer empty: thinking is turned off for it
        self.flag_thinking = (source == SOURCE_OLLAMA
                              and "thinking" in take_ollama_capabilities(self.url, self.model))

    @property
    def model_name(self) -> str:
        return f"{self.model} ({D_SOURCE_NAMES[self.source].split(' (')[0]}, {self.url})"

    def n_ctx(self) -> int:
        return self.settings["n_ctx"]

    def count_tokens(self, text: str) -> int:
        """Approximate: the server has the tokenizer."""
        return int(len(text) / CHARACTERS_PER_TOKEN) + 1

    def close(self):
        """The server keeps or frees the model itself."""

    def chat(self, messages: List[Dict[str, str]], flag_json: bool = False,
             schema: Optional[dict] = None) -> str:
        from cryspy_editor.widgets.assistant import fit_messages
        max_tokens = self.settings["max_tokens"]
        messages = fit_messages(messages, max_tokens, self.n_ctx(), self.count_tokens)
        if self.source == SOURCE_OLLAMA:
            data = {"model": self.model, "messages": messages, "stream": False,
                    "options": {"temperature": self.settings["temperature"], "num_ctx": self.n_ctx(),
                                "num_predict": max_tokens}}
            if flag_json:
                data["format"] = schema if schema is not None else "json"
            if self.flag_thinking:
                data["think"] = False
            result = _request_json(f"{self.url}/api/chat", data, timeout=TIMEOUT_CHAT)
            return str(result.get("message", {}).get("content", "")).strip()
        data = {"model": self.model, "messages": messages, "max_tokens": max_tokens,
                "temperature": self.settings["temperature"]}
        if flag_json and schema is not None:
            data["response_format"] = {"type": "json_schema",
                                       "json_schema": {"name": "reply", "schema": schema}}
        result = _request_json(f"{self.url}/chat/completions", data, timeout=TIMEOUT_CHAT)
        return str(result["choices"][0]["message"]["content"] or "").strip()


def create_model(d_model: dict, settings: Optional[dict] = None):
    """LocalModel or ServerModel for d_model: 'source' (SOURCE_*),
    'model_path' (GGUF file), 'url' and 'model' (server)."""
    source = d_model.get("source", SOURCE_GGUF)
    if source == SOURCE_GGUF:
        from cryspy_editor.widgets.assistant import LocalModel
        return LocalModel(d_model.get("model_path", ""), settings)
    return ServerModel(source, d_model.get("url", ""), d_model.get("model", ""), settings)

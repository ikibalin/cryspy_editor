"""Context length from the model and models of Ollama or another server."""
import json
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from cryspy_editor.widgets import assistant_models
from cryspy_editor.widgets.assistant import Assistant
from cryspy_editor.widgets.assistant_models import (
    SOURCE_OLLAMA,
    SOURCE_OPENAI,
    ServerModel,
    calc_kv_bytes_per_token,
    create_model,
    form_context_text,
    read_gguf_metadata,
    recommend_max_tokens,
    split_thinking,
    take_context_range,
    take_gguf_context,
    take_gguf_thinking,
)

# Qwen2.5-7B-Instruct
D_QWEN_7B = {"architecture": "qwen2", "context_length": 32768, "block_count": 28,
             "embedding_length": 3584, "attention.head_count": 28, "attention.head_count_kv": 4}


def pack_string(text: str) -> bytes:
    data = text.encode("utf-8")
    return struct.pack("<Q", len(data)) + data


def write_gguf(file_name, d_meta: dict, chat_template: str = ""):
    """A GGUF header with the metadata and a vocabulary array before it."""
    l_kv = [pack_string("general.architecture") + struct.pack("<I", 8) + pack_string(d_meta["architecture"]),
            pack_string("tokenizer.ggml.tokens") + struct.pack("<IIQ", 9, 8, 3)
            + b"".join(pack_string(token) for token in ("a", "bb", "ccc")),
            pack_string("tokenizer.ggml.scores") + struct.pack("<IIQ", 9, 6, 2) + struct.pack("<ff", 1., 2.)]
    for key, value in d_meta.items():
        if key != "architecture":
            l_kv.append(pack_string(f"{d_meta['architecture']}.{key}") + struct.pack("<II", 4, value))
    if chat_template != "":
        l_kv.append(pack_string("tokenizer.chat_template") + struct.pack("<I", 8) + pack_string(chat_template))
    with open(file_name, "wb") as file:
        file.write(b"GGUF" + struct.pack("<IQQ", 3, 0, len(l_kv)) + b"".join(l_kv))


def test_gguf_metadata(tmp_path):
    f_model = tmp_path / "model.gguf"
    write_gguf(f_model, D_QWEN_7B)
    assert read_gguf_metadata(str(f_model)) == D_QWEN_7B
    f_text = tmp_path / "text.gguf"
    f_text.write_text("not a model")
    with pytest.raises(ValueError):
        read_gguf_metadata(str(f_text))
    assert take_gguf_context(str(f_text), 16.) is None
    assert not take_gguf_thinking(str(f_model)) and not take_gguf_thinking(str(f_text))
    f_thinking = tmp_path / "qwen3.gguf"
    write_gguf(f_thinking, D_QWEN_7B, "{{- '<think>' }}{{ message.content }}")
    assert read_gguf_metadata(str(f_thinking))["chat_template"].startswith("{{")
    assert take_gguf_thinking(str(f_thinking))


def test_thinking_and_answer_length():
    assert split_thinking('<think>a is fine</think>\n{"x": 1}') == ("a is fine", '{"x": 1}')
    assert split_thinking('a is fine</think>{"x": 1}') == ("a is fine", '{"x": 1}')  # <think> in the prompt
    assert split_thinking('{"x": 1}') == ("", '{"x": 1}')
    assert recommend_max_tokens(False, 8192) == 1024
    assert recommend_max_tokens(True, 32768) == 9216  # the thinking and the answer
    assert recommend_max_tokens(True, 32768, 2048) == 3072
    assert recommend_max_tokens(True, 8192, 8192) == 4096  # half of the context stays for the question
    assert recommend_max_tokens(False, 512) == 256


def test_context_range_for_the_memory():
    # 2 (K, V) * 28 layers * 4 heads * 2 * 128 values * 2 bytes
    assert calc_kv_bytes_per_token(D_QWEN_7B) == 57344
    d_range = take_context_range(D_QWEN_7B, 4.7, 16.)
    assert d_range["n_train"] == 32768
    assert d_range["n_memory"] > 32768
    assert d_range["n_recommended"] == 32768
    text = form_context_text(d_range, 16.)
    assert "from 2048 to 32768 tokens" in text and "whole context fits" in text
    # a small computer: the context left after the model
    d_range = take_context_range(D_QWEN_7B, 4.7, 8.)
    assert d_range["n_recommended"] == d_range["n_memory"] // 1024 * 1024 < 32768
    assert "up to about" in form_context_text(d_range, 8.)
    # nothing fits: the minimum, with the note on recipes
    d_range = take_context_range(D_QWEN_7B, 7., 8.)
    assert d_range["n_recommended"] == assistant_models.MIN_CONTEXT
    assert "recipes need 8192" in form_context_text(d_range, 8.)
    # unknown memory and model
    assert take_context_range({}, None, None) == {
        "n_train": None, "n_memory": None, "n_recommended": assistant_models.MAX_RECOMMENDED_CONTEXT}


class FakeServer(BaseHTTPRequestHandler):
    """Ollama and OpenAI-compatible answers; requests and their
    Authorization headers are kept."""
    l_request = []
    l_authorization = []

    def log_message(self, *args):
        pass

    def answer(self, d_out: dict):
        data = json.dumps(d_out).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/tags":
            self.answer({"models": [{"name": "qwen2.5:7b", "size": 4.7 * 1024**3}]})
        elif self.path == "/v1/models":
            FakeServer.l_authorization.append(self.headers.get("Authorization"))
            self.answer({"data": [{"id": "qwen2.5-7b-instruct"}]})
        elif self.path == "/gemini/models":
            self.answer({"data": [{"id": "models/gemini-2.5-pro"}, {"id": "models/gemini-2.5-flash"}]})
        else:
            self.send_error(404)

    def do_POST(self):
        d_in = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeServer.l_request.append((self.path, d_in))
        s_reply = json.dumps({"actions": [], "answer": "Hello"})
        if self.path == "/api/chat" and d_in["stream"]:
            # a thinking model: the thinking, then the answer, line by line
            l_part = [{"message": {"thinking": "The user "}}, {"message": {"thinking": "greets me."}}]
            if d_in["model"] == "qwen3:long":  # thinks without end
                l_part = [{"message": {"thinking": "Shall I refine the scale or not? "}}] * 200
            elif d_in["model"] == "qwen3:cut":
                l_part.append({"done": True, "done_reason": "length", "message": {}})
            else:
                l_part += [{"message": {"content": s_reply[:10]}}, {"message": {"content": s_reply[10:]}},
                           {"done": True, "done_reason": "stop", "message": {}}]
            data = b"".join(json.dumps(d_part).encode("utf-8") + b"\n" for d_part in l_part)
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path == "/api/chat":
            self.answer({"message": {"role": "assistant", "content": s_reply}})
        elif self.path == "/api/show":
            l_capability = ["completion", "thinking"] if d_in["model"].startswith("qwen3") else ["completion"]
            self.answer({"capabilities": l_capability, "model_info": {"general.architecture": "qwen2", **{
                f"qwen2.{key}": value for key, value in D_QWEN_7B.items() if key != "architecture"}}})
        elif self.path == "/v1/chat/completions":
            FakeServer.l_authorization.append(self.headers.get("Authorization"))
            d_format = d_in.get("response_format", {})
            if d_in["model"] == "no-schema" and d_format.get("type") == "json_schema":
                self.send_error(400, "response_format json_schema is not supported")
            else:
                self.answer({"choices": [{"message": {"content": s_reply}}]})
        else:
            self.send_error(404)


@pytest.fixture
def server_url():
    server = HTTPServer(("127.0.0.1", 0), FakeServer)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    FakeServer.l_request.clear()
    FakeServer.l_authorization.clear()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_ollama_model_answers(server_url):
    model = create_model({"source": SOURCE_OLLAMA, "url": server_url, "model": "qwen2.5:7b"},
                         {"n_ctx": 8192, "max_tokens": 256})
    assert "qwen2.5:7b" in model.model_name
    result = Assistant(model).ask("hello", None)
    assert result["text"] == "Hello"
    path, d_in = FakeServer.l_request[-1]
    assert path == "/api/chat" and d_in["model"] == "qwen2.5:7b" and not d_in["stream"]
    assert d_in["options"]["num_ctx"] == 8192 and d_in["options"]["num_predict"] == 256
    assert d_in["format"] is not None  # JSON or the schema of the reply
    assert "think" not in d_in  # not a thinking model
    assert assistant_models.list_server_models(SOURCE_OLLAMA, server_url) == ["qwen2.5:7b"]
    d_range = assistant_models.take_ollama_context(server_url, "qwen2.5:7b", 16.)
    assert d_range["n_train"] == 32768


def test_ollama_thinking_model(server_url):
    """A thinking model thinks only when it is turned on; the thinking goes
    to on_thinking as it comes, the answer is returned."""
    model = ServerModel(SOURCE_OLLAMA, server_url, "qwen3:8b")
    assert model.flag_thinking_model and not model.flag_thinking
    assert model.chat([{"role": "user", "content": "hi"}], flag_json=True).startswith("{")
    path, d_in = FakeServer.l_request[-1]
    assert path == "/api/chat" and d_in["think"] is False and not d_in["stream"]

    model = ServerModel(SOURCE_OLLAMA, server_url, "qwen3:8b", {"thinking": True, "max_tokens": 4096, "n_ctx": 16384})
    l_thinking = []
    model.on_thinking = l_thinking.append
    result = Assistant(model).ask("hello", None)
    assert result["text"] == "Hello"
    path, d_in = FakeServer.l_request[-1]
    assert d_in["think"] is True and d_in["stream"] and d_in["options"]["num_predict"] == 4096
    assert "".join(l_thinking) == "The user greets me." and l_thinking[0] == ""

    model = ServerModel(SOURCE_OLLAMA, server_url, "qwen3:cut", {"thinking": True})
    with pytest.raises(ValueError, match="cut at the maximal answer length"):
        model.chat([{"role": "user", "content": "hi"}])
    assert assistant_models.take_ollama_capabilities("http://127.0.0.1:9", "qwen3:8b") == []


def test_ollama_thinking_is_stopped_at_its_limit(server_url):
    """A thinking longer than max_thinking_tokens is stopped; the model
    answers from it without thinking again."""
    model = ServerModel(SOURCE_OLLAMA, server_url, "qwen3:long",
                        {"thinking": True, "max_thinking_tokens": 256, "max_tokens": 1024, "n_ctx": 8192})
    l_thinking = []
    model.on_thinking = l_thinking.append
    messages = [{"role": "system", "content": "You help."}, {"role": "user", "content": "hi"}]
    assert model.chat(messages, flag_json=True).startswith("{")
    (path_1, d_think), (path_2, d_decide) = FakeServer.l_request[-2:]
    assert d_think["stream"] and d_think["think"] is True
    assert "Think briefly" in d_think["messages"][0]["content"]
    assert d_decide["think"] is False and not d_decide["stream"]
    assert "reached its limit" in d_decide["messages"][-1]["content"]
    assert d_decide["messages"][-2]["role"] == "assistant"
    s_thinking = "".join(l_thinking)
    assert "limit of 256 tokens" in s_thinking
    assert len(s_thinking) < 256 * 4 + 200  # about the limit, not all 200 parts
    assert messages[0]["content"] == "You help."  # the messages of the assistant stay


def test_gguf_thinking_streamed_and_stopped():
    """A GGUF model: the <think> block is streamed to on_thinking, the
    answer comes after it; a too long thinking is stopped."""
    from cryspy_editor.widgets.assistant import LocalModel, take_settings

    class StreamLlama:
        def __init__(self, l_stream):
            self.l_stream = l_stream
            self.l_kwargs = []

        def n_ctx(self):
            return 8192

        def tokenize(self, data, add_bos=False):
            return data.split()

        def create_chat_completion(self, messages, **kwargs):
            self.l_kwargs.append(dict(kwargs, messages=messages))
            if kwargs.get("stream"):
                return iter([{"choices": [{"delta": {"content": part}}]} for part in self.l_stream])
            return {"choices": [{"message": {"content": '{"answer": "decided"}'}}]}

    model = LocalModel.__new__(LocalModel)
    model.flag_thinking_model = True
    model.settings = take_settings({"thinking": True, "max_thinking_tokens": 5})
    l_thinking = []
    model.on_thinking = l_thinking.append
    model.llm = StreamLlama(["<think>", "Scale ", "first.", "</think>", '{"answer": ', '"ok"}'])
    assert model.chat([{"role": "user", "content": "hi"}], flag_json=True) == '{"answer": "ok"}'
    assert "".join(l_thinking) == "Scale first."
    assert "response_format" not in model.llm.l_kwargs[-1]  # a grammar forbids the thinking

    l_thinking.clear()
    model.llm = StreamLlama(["<think>"] + ["again "] * 50)
    assert model.chat([{"role": "user", "content": "hi"}], flag_json=True) == '{"answer": "decided"}'
    assert "limit of 5 tokens" in "".join(l_thinking)
    d_decide = model.llm.l_kwargs[-1]
    assert "response_format" in d_decide and "reached its limit" in d_decide["messages"][-1]["content"]


def test_openai_compatible_model(server_url):
    model = ServerModel(SOURCE_OPENAI, f"{server_url}/v1", "qwen2.5-7b-instruct")
    assert model.chat([{"role": "user", "content": "hi"}], flag_json=True,
                      schema={"type": "object"}).startswith("{")
    path, d_in = FakeServer.l_request[-1]
    assert path == "/v1/chat/completions"
    assert d_in["response_format"]["json_schema"]["schema"] == {"type": "object"}


def test_cloud_service(server_url, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert set(assistant_models.D_CLOUD) <= set(assistant_models.D_SOURCE_NAMES)
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        create_model({"source": "groq", "url": f"{server_url}/v1", "model": "llama"})
    model = create_model({"source": "groq", "url": f"{server_url}/v1", "model": "llama", "api_key": "secret"})
    assert "internet" in model.model_name
    assert model.chat([{"role": "user", "content": "hi"}], flag_json=True, schema={"type": "object"}) != ""
    assert FakeServer.l_authorization[-1] == "Bearer secret"
    # the key of the environment variable
    monkeypatch.setenv("GROQ_API_KEY", "from-env")
    model = ServerModel("groq", f"{server_url}/v1", "llama")
    model.chat([{"role": "user", "content": "hi"}])
    assert FakeServer.l_authorization[-1] == "Bearer from-env"
    assert "internet" in assistant_models.form_internet_text("groq")
    # a local server gets no key
    assert assistant_models.list_server_models(SOURCE_OPENAI, f"{server_url}/v1") == ["qwen2.5-7b-instruct"]
    assert FakeServer.l_authorization[-1] is None
    # Gemini names its models "models/..."
    assert assistant_models.list_server_models("gemini", f"{server_url}/gemini", "key") == [
        "gemini-2.5-flash", "gemini-2.5-pro"]


def test_server_without_json_schema(server_url):
    model = ServerModel(SOURCE_OPENAI, f"{server_url}/v1", "no-schema")
    assert model.chat([{"role": "user", "content": "hi"}], flag_json=True, schema={"type": "object"}) != ""
    assert FakeServer.l_request[-1][1]["response_format"] == {"type": "json_object"}
    assert model.l_response_format == ["json_object", ""]  # not asked with a schema again
    model.chat([{"role": "user", "content": "hi"}], flag_json=True, schema={"type": "object"})
    assert [path for path, _ in FakeServer.l_request].count("/v1/chat/completions") == 3


def test_server_not_running():
    with pytest.raises(ConnectionError, match="Is the server running"):
        ServerModel(SOURCE_OLLAMA, "http://127.0.0.1:9", "qwen2.5:7b")


def test_dialog_sources_and_context(qapp, tmp_path, server_url):
    from cryspy_editor.widgets.ui_assistant import ModelSettingsDialog
    f_model = tmp_path / "model.gguf"
    write_gguf(f_model, D_QWEN_7B)
    dialog = ModelSettingsDialog(str(f_model), {"n_ctx": 4096})
    try:
        assert dialog.settings()["n_ctx"] == 4096  # the saved value stays at opening
        assert "from 2048 to 32768 tokens" in dialog.label_context.text()
        dialog.memory_gb = 64.
        dialog.update_context()
        assert dialog.settings()["n_ctx"] == 32768
        dialog.cb_source.setCurrentIndex(dialog.cb_source.findData(SOURCE_OLLAMA))
        assert dialog.line_url.text() == assistant_models.D_DEFAULT_URL[SOURCE_OLLAMA]
        dialog.line_url.setText(server_url)
        dialog.refresh_server_models()
        assert dialog.server_model() == "qwen2.5:7b"
        assert dialog.model_description() == {
            "source": SOURCE_OLLAMA, "model_path": str(f_model), "url": server_url, "model": "qwen2.5:7b",
            "api_key": ""}
        assert "32768" in dialog.label_context.text()
        # not a thinking model: the thinking cannot be turned on
        assert not dialog.check_thinking.isEnabled()
        dialog.cb_server_model.setEditText("qwen3:8b")
        dialog.update_context()
        assert dialog.check_thinking.isEnabled()
        dialog.check_thinking.setChecked(True)
        assert dialog.settings()["thinking"] is True
        assert dialog.settings()["max_tokens"] == recommend_max_tokens(
            True, dialog.settings()["n_ctx"], dialog.settings()["max_thinking_tokens"])
        dialog.sb_max_thinking.setValue(1024)
        assert dialog.settings()["max_tokens"] == recommend_max_tokens(True, dialog.settings()["n_ctx"], 1024)
        assert "thinking" in dialog.label_max_tokens.text()
        dialog.check_thinking.setChecked(False)
        assert dialog.settings()["max_tokens"] == recommend_max_tokens(False, dialog.settings()["n_ctx"], 1024)
    finally:
        dialog.close()


def test_dialog_cloud_service(qapp):
    from cryspy_editor.widgets.ui_assistant import ModelSettingsDialog
    dialog = ModelSettingsDialog("", {}, d_model={"source": SOURCE_OPENAI, "api_key": "local"},
                                 d_api_keys={"gemini": "g-key"})
    try:
        assert not dialog.label_internet.isVisibleTo(dialog)
        assert dialog.api_key() == "local"
        dialog.cb_source.setCurrentIndex(dialog.cb_source.findData("gemini"))
        assert dialog.label_internet.isVisibleTo(dialog)
        assert "internet" in dialog.label_internet.text()
        assert "aistudio.google.com" in dialog.label_api_key.text()
        assert dialog.line_url.text() == assistant_models.D_CLOUD["gemini"]["url"]
        assert dialog.server_model() == assistant_models.D_CLOUD["gemini"]["model"]
        assert dialog.api_key() == "g-key"
        assert dialog.settings()["n_ctx"] == assistant_models.MAX_RECOMMENDED_CONTEXT
        dialog.line_api_key.setText("g-new")
        assert dialog.model_description()["api_key"] == "g-new"
        assert dialog.api_keys() == {SOURCE_OPENAI: "local", "gemini": "g-new"}
        dialog.cb_source.setCurrentIndex(dialog.cb_source.findData(SOURCE_OLLAMA))
        assert dialog.model_description()["api_key"] == ""
        assert not dialog.line_api_key.isVisibleTo(dialog)
    finally:
        dialog.close()


def test_controller_keeps_the_server_model(qapp, server_url):
    from PyQt5 import QtWidgets

    from cryspy_editor.widgets.ui_assistant import AssistantController
    main_window = QtWidgets.QMainWindow()
    d_setup = {"llm_source": SOURCE_OLLAMA, "llm_server_url": server_url,
               "llm_server_model": "qwen2.5:7b", "llm_autoload": True}
    controller = AssistantController(main_window, d_setup, lambda: True, lambda: None, lambda: None)
    try:
        controller.autoload_model()
        for _ in range(500):
            qapp.processEvents()
            if controller.window.assistant is not None:
                break
            time.sleep(0.01)
        assert controller.window.assistant is not None
        assert "qwen2.5:7b" in controller.window.label_model.text()
        assert d_setup["llm_autoload"] is True
    finally:
        controller.shutdown()
        controller.window.close()
        main_window.close()


def test_window_shows_the_thinking(qapp, server_url):
    from cryspy_editor.widgets.ui_assistant import AssistantWindow
    window = AssistantWindow()
    try:
        model = ServerModel(SOURCE_OLLAMA, server_url, "qwen3:8b", {"thinking": True})
        window.on_model_loaded(Assistant(model))
        assert "(thinking)" in window.label_model.text() and window.button_thoughts.isChecked()
        window.input_line.setText("hello")
        window.on_send()
        for _ in range(500):
            qapp.processEvents()
            if window.thread is None:
                break
            time.sleep(0.01)
        assert window.thoughts_view.toPlainText() == "The user greets me."
        assert "Hello" in window.history_view.toPlainText()
        assert model.on_thinking is None  # the window takes the thinking only while it asks
        window.input_line.setText("hello again")
        window.on_send()  # the thoughts of the last request only
        for _ in range(500):
            qapp.processEvents()
            if window.thread is None:
                break
            time.sleep(0.01)
        assert window.thoughts_view.toPlainText() == "The user greets me."
        window.append_thinking("")
        window.append_thinking("Next.")
        assert window.thoughts_view.toPlainText().endswith("-" * 40 + "\nNext.")
        window.clear_chat()
        assert window.thoughts_view.toPlainText() == ""
    finally:
        window.shutdown()
        window.close()

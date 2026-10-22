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
    take_context_range,
    take_gguf_context,
)

# Qwen2.5-7B-Instruct
D_QWEN_7B = {"architecture": "qwen2", "context_length": 32768, "block_count": 28,
             "embedding_length": 3584, "attention.head_count": 28, "attention.head_count_kv": 4}


def pack_string(text: str) -> bytes:
    data = text.encode("utf-8")
    return struct.pack("<Q", len(data)) + data


def write_gguf(file_name, d_meta: dict):
    """A GGUF header with the metadata and a vocabulary array before it."""
    l_kv = [pack_string("general.architecture") + struct.pack("<I", 8) + pack_string(d_meta["architecture"]),
            pack_string("tokenizer.ggml.tokens") + struct.pack("<IIQ", 9, 8, 3)
            + b"".join(pack_string(token) for token in ("a", "bb", "ccc")),
            pack_string("tokenizer.ggml.scores") + struct.pack("<IIQ", 9, 6, 2) + struct.pack("<ff", 1., 2.)]
    for key, value in d_meta.items():
        if key != "architecture":
            l_kv.append(pack_string(f"{d_meta['architecture']}.{key}") + struct.pack("<II", 4, value))
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
    """Ollama and OpenAI-compatible answers; requests are kept."""
    l_request = []

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
            self.answer({"data": [{"id": "qwen2.5-7b-instruct"}]})
        else:
            self.send_error(404)

    def do_POST(self):
        d_in = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeServer.l_request.append((self.path, d_in))
        s_reply = json.dumps({"actions": [], "answer": "Hello"})
        if self.path == "/api/chat":
            self.answer({"message": {"role": "assistant", "content": s_reply}})
        elif self.path == "/api/show":
            l_capability = ["completion", "thinking"] if d_in["model"].startswith("qwen3") else ["completion"]
            self.answer({"capabilities": l_capability, "model_info": {"general.architecture": "qwen2", **{
                f"qwen2.{key}": value for key, value in D_QWEN_7B.items() if key != "architecture"}}})
        elif self.path == "/v1/chat/completions":
            self.answer({"choices": [{"message": {"content": s_reply}}]})
        else:
            self.send_error(404)


@pytest.fixture
def server_url():
    server = HTTPServer(("127.0.0.1", 0), FakeServer)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    FakeServer.l_request.clear()
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


def test_ollama_thinking_model_does_not_think(server_url):
    """qwen3 and other thinking models would spend max_tokens on thinking."""
    model = ServerModel(SOURCE_OLLAMA, server_url, "qwen3:8b")
    assert model.flag_thinking
    assert model.chat([{"role": "user", "content": "hi"}], flag_json=True).startswith("{")
    path, d_in = FakeServer.l_request[-1]
    assert path == "/api/chat" and d_in["think"] is False
    assert assistant_models.take_ollama_capabilities("http://127.0.0.1:9", "qwen3:8b") == []


def test_openai_compatible_model(server_url):
    model = ServerModel(SOURCE_OPENAI, f"{server_url}/v1", "qwen2.5-7b-instruct")
    assert model.chat([{"role": "user", "content": "hi"}], flag_json=True,
                      schema={"type": "object"}).startswith("{")
    path, d_in = FakeServer.l_request[-1]
    assert path == "/v1/chat/completions"
    assert d_in["response_format"]["json_schema"]["schema"] == {"type": "object"}


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
            "source": SOURCE_OLLAMA, "model_path": str(f_model), "url": server_url, "model": "qwen2.5:7b"}
        assert "32768" in dialog.label_context.text()
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

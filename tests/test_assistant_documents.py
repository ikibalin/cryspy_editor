"""Documents of the user for the AI assistant (assistant_documents.py,
documents_dialog.py): the search itself is done by CrysPy."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import cryspy
import pytest

from cryspy_editor.widgets import assistant_documents
from cryspy_editor.widgets.assistant_documents import (
    KEY_FOLDER,
    KEY_MODEL,
    KEY_PATH,
    KEY_SOURCE,
    KEY_URL,
    SOURCE_NONE,
    create_embedding,
    form_embedding_functions,
    init_documents,
    take_prefixes,
)
from cryspy_editor.widgets.assistant_models import (
    SOURCE_GGUF,
    SOURCE_OLLAMA,
    SOURCE_OPENAI,
)

pytestmark = pytest.mark.skipif(not assistant_documents.FLAG_DOCUMENTS,
                                reason="CrysPy without the search in documents")

TEXT_EXTINCTION = "The extinction of strong reflections of TbTe3 is described by the Becker-Coppens model."
TEXT_MAGNETIC = "The magnetic moments of Tb order along the c axis below 5.4 K."


@pytest.fixture(autouse=True)
def no_documents():
    yield
    if assistant_documents.FLAG_DOCUMENTS:
        cryspy.set_document_folder(None)
        cryspy.set_document_embedding(None)
    assistant_documents.close_embedding()


@pytest.fixture
def folder(tmp_path):
    path = tmp_path / "papers"
    path.mkdir()
    (path / "extinction.txt").write_text(TEXT_EXTINCTION, encoding="utf-8")
    (path / "magnetic.md").write_text(TEXT_MAGNETIC, encoding="utf-8")
    return path


def embed_words(l_text):
    """Vectors of a fake model: 'extinction' (or 'погасание') and 'magnetic'."""
    return [[text.lower().count("extinction") + text.lower().count("погасан") + 0.01,
             text.lower().count("magnet") + 0.01] for text in l_text]


class FakeEmbeddingServer(BaseHTTPRequestHandler):
    l_request = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        d_in = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeEmbeddingServer.l_request.append((self.path, d_in))
        l_vector = embed_words(d_in["input"])
        if self.path == "/api/embed":
            d_out = {"embeddings": l_vector}
        elif self.path == "/v1/embeddings":  # in another order, with the index
            d_out = {"data": [{"index": ind, "embedding": vector}
                              for ind, vector in reversed(list(enumerate(l_vector)))]}
        else:
            self.send_error(404)
            return
        data = json.dumps(d_out).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def server_url():
    server = HTTPServer(("127.0.0.1", 0), FakeEmbeddingServer)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    FakeEmbeddingServer.l_request.clear()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_prefixes_of_models():
    assert take_prefixes("nomic-embed-text:latest") == ("search_document: ", "search_query: ")
    assert take_prefixes("/models/multilingual-e5-small-Q8_0.gguf") == ("passage: ", "query: ")
    assert take_prefixes("bge-m3") == ("", "")


def test_create_embedding_of_the_settings(tmp_path):
    assert create_embedding({}) is None
    assert create_embedding({KEY_SOURCE: SOURCE_NONE}) is None
    with pytest.raises(ValueError, match="name of the embedding model"):
        create_embedding({KEY_SOURCE: SOURCE_OLLAMA, KEY_MODEL: ""})
    with pytest.raises(FileNotFoundError):
        create_embedding({KEY_SOURCE: SOURCE_GGUF, KEY_PATH: str(tmp_path / "none.gguf")})
    embedding = create_embedding({KEY_SOURCE: SOURCE_OLLAMA, KEY_MODEL: "bge-m3"})
    assert embedding.url == "http://localhost:11434" and embedding.name == "bge-m3 (ollama)"


@pytest.mark.parametrize("source, path", [(SOURCE_OLLAMA, "/api/embed"), (SOURCE_OPENAI, "/v1/embeddings")])
def test_server_embedding_with_prefixes(server_url, source, path):
    url = server_url + ("/v1" if source == SOURCE_OPENAI else "")
    embedding = create_embedding({KEY_SOURCE: source, KEY_URL: url, KEY_MODEL: "nomic-embed-text"})
    embed_documents, embed_query = form_embedding_functions(embedding)
    assert embed_documents(["extinction", "magnetic"]) == [[1.01, 0.01], [0.01, 1.01]]
    assert FakeEmbeddingServer.l_request[-1] == (
        path, {"model": "nomic-embed-text", "input": ["search_document: extinction", "search_document: magnetic"]})
    embed_query(["magnetic"])
    assert FakeEmbeddingServer.l_request[-1][1]["input"] == ["search_query: magnetic"]


def test_init_documents_gives_cryspy_the_folder_and_model(folder, server_url, settings_dir):
    d_setup = {KEY_FOLDER: str(folder), KEY_SOURCE: SOURCE_OLLAMA, KEY_URL: server_url, KEY_MODEL: "bge-m3"}
    assert init_documents(d_setup) == ""
    assert assistant_documents.take_document_folder() == str(folder)
    text = assistant_documents.update_index()
    assert "2 files" in text and "2 of 2 fragments" in text
    # the index is kept in the settings folder of CrysPy Editor
    assert (settings_dir / "documents_index" / "documents_index.json").is_file()
    # a Russian question finds the English fragment by meaning
    result = cryspy.call_assistant_tool(None, "search_documents", {"query": "погасание"})
    assert "[1] extinction.txt, line 1:" in result["text"]
    # a wrong model leaves the search by words
    assert "name of the embedding model" in init_documents(dict(d_setup, **{KEY_MODEL: ""}))
    assert "BM25 (words only)" in cryspy.call_assistant_tool(
        None, "search_documents", {"query": "extinction"})["text"]


def test_system_prompt_has_the_rule_only_with_a_folder(folder):
    from cryspy_editor.widgets import assistant as assistant_module
    init_documents({})
    assert "search_documents\" (query" not in assistant_module.form_system_prompt()
    init_documents({KEY_FOLDER: str(folder)})
    prompt = assistant_module.form_system_prompt()
    assert "folder of documents" in prompt and "[file, page]" in prompt


def test_model_answers_from_the_documents(folder):
    from test_assistant import make_assistant, reply
    init_documents({KEY_FOLDER: str(folder)})
    assistant = make_assistant([
        reply(("search_documents", {"query": "extinction TbTe3"})),
        json.dumps({"actions": [], "answer": "Becker-Coppens [extinction.txt, line 1]."}),
    ])
    result = assistant.ask("What do my papers say about extinction in TbTe3?", None)
    assert [action[0] for action in result["actions"]] == ["search_documents"]
    assert "[extinction.txt, line 1]" in result["text"]
    # the model got the fragment and the rule to cite it
    l_messages = assistant.model.llm.l_messages[-1]
    assert any("Becker-Coppens model" in message["content"] and "cite" in message["content"]
               for message in l_messages)


def test_progress_text_of_documents():
    from cryspy_editor.widgets.ui_assistant import form_progress_text
    assert form_progress_text({"label": "Reading documents", "step": 3, "n_step": 40}) == \
        "Reading documents 3/40 ... (Stop ends it)"
    assert form_progress_text({"iteration": 2}).startswith("Iteration 2")


def test_documents_dialog_saves_and_indexes(qapp, qtbot, folder):
    from cryspy_editor.widgets.documents_dialog import DocumentsDialog
    d_setup, l_saved = {}, []
    dialog = DocumentsDialog(d_setup, lambda: l_saved.append(True))
    qtbot.addWidget(dialog)
    # only the fields of the chosen source are shown
    dialog.show()
    assert not dialog.line_url.isVisible() and not dialog.line_path.isVisible()
    dialog.cb_source.setCurrentIndex(dialog.cb_source.findData(SOURCE_OLLAMA))
    assert dialog.line_url.isVisible() and dialog.line_url.text() == "http://localhost:11434"
    dialog.cb_source.setCurrentIndex(dialog.cb_source.findData(SOURCE_NONE))
    dialog.line_folder.setText(str(folder / "none"))
    assert not dialog.apply() and "not found" in dialog.label_status.text()
    dialog.line_folder.setText(str(folder))
    dialog.update_index()
    qtbot.waitUntil(lambda: not dialog.is_busy(), timeout=10000)
    assert "2 files" in dialog.label_status.text()
    assert d_setup[KEY_FOLDER] == str(folder) and d_setup[KEY_SOURCE] == SOURCE_NONE and l_saved
    assert assistant_documents.take_document_folder() == str(folder)


def test_folder_given_in_the_chat_is_kept(qapp, folder):
    from PyQt5 import QtWidgets

    from cryspy_editor.widgets.ui_assistant import AssistantController
    main_window = QtWidgets.QMainWindow()
    d_setup = {}
    controller = AssistantController(main_window, d_setup, lambda: True, lambda: None, lambda: None)
    try:
        menu = controller.init_menu(main_window.menuBar())
        assert "Documents..." in [action.text() for action in menu.actions()]
        cryspy.call_assistant_tool(None, "list_documents", {"folder": str(folder)})
        controller.save_window_state()
        assert d_setup[KEY_FOLDER] == str(folder)
    finally:
        controller.shutdown()
        main_window.deleteLater()

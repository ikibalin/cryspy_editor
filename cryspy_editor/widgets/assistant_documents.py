"""Documents of the user for the AI assistant (retrieval-augmented
generation), without Qt.

The search is done by CrysPy (cryspy.procedure_assistant.documents: the
fragments, BM25, the cache of the index, the tools search_documents,
list_documents and index_documents); CrysPy Editor gives it the folder
of the user, the cache folder in the settings folder and, optionally, the
embedding model for the search by meaning:

- Ollama (/api/embed), e.g. bge-m3 (many languages) or nomic-embed-text;
- an OpenAI-compatible server (/v1/embeddings: LM Studio, llama.cpp server);
- a GGUF embedding model loaded by llama-cpp-python (embedding=True).

A chat model gives poor vectors, so the embedding model is a separate one
(small: 0.1-1 GB). Only the standard library is used for the servers.
"""
import os
from collections.abc import Callable

import cryspy

from cryspy_editor.settings import take_config_dir
from cryspy_editor.widgets.assistant_models import (
    D_DEFAULT_URL,
    SOURCE_GGUF,
    SOURCE_OLLAMA,
    SOURCE_OPENAI,
    _request_json,
)

# CrysPy with the search in documents (newer than 0.20)
FLAG_DOCUMENTS = hasattr(cryspy, "set_document_folder")

SOURCE_NONE = "none"
D_EMBEDDING_SOURCE_NAMES = {
    SOURCE_NONE: "No embedding model: search by words only (BM25)",
    SOURCE_OLLAMA: "Ollama",
    SOURCE_OPENAI: "OpenAI-compatible server (LM Studio, llama.cpp server)",
    SOURCE_GGUF: "Local GGUF embedding model (llama-cpp-python)",
}
S_INDEX_FOLDER = "documents_index"
TIMEOUT_EMBEDDING = 300
GGUF_CONTEXT = 2048  # a fragment of 180 words is 250-400 tokens

# keys of the settings of CrysPy Editor (d_setup of the main window)
KEY_FOLDER = "documents_folder"
KEY_SOURCE = "embedding_source"
KEY_URL = "embedding_url"
KEY_MODEL = "embedding_model"
KEY_PATH = "embedding_path"

# (model, what it is): proposed in the dialog
L_RECOMMENDED_EMBEDDINGS = (
    ("bge-m3", "many languages (Russian, French, ...), 1.2 GB; Ollama: ollama pull bge-m3"),
    ("nomic-embed-text", "English, 0.3 GB, fast; Ollama: ollama pull nomic-embed-text"),
    ("multilingual-e5-small", "many languages, 0.1 GB: a GGUF file for llama-cpp-python"),
)

# models trained with prefixes of the fragment and of the question
L_PREFIXES = (
    ("nomic-embed", "search_document: ", "search_query: "),
    ("e5", "passage: ", "query: "),
)


def take_prefixes(model_name: str) -> tuple:
    """(prefix of a fragment, prefix of a question) for the model."""
    name = os.path.basename(model_name).lower()
    for part, prefix_document, prefix_query in L_PREFIXES:
        if part in name:
            return prefix_document, prefix_query
    return "", ""


class ServerEmbedding:
    """Vectors of texts from Ollama or an OpenAI-compatible server."""

    def __init__(self, source: str, url: str, model: str):
        if model.strip() == "":
            raise ValueError("Give the name of the embedding model of the server.")
        self.source = source
        self.url = (url.strip() or D_DEFAULT_URL[source]).rstrip("/")
        self.model = model.strip()

    @property
    def name(self) -> str:
        return f"{self.model} ({self.source})"

    def __call__(self, l_text: list[str]) -> list[list[float]]:
        if self.source == SOURCE_OLLAMA:
            result = _request_json(f"{self.url}/api/embed", {"model": self.model, "input": l_text},
                                   timeout=TIMEOUT_EMBEDDING)
            return result["embeddings"]
        result = _request_json(f"{self.url}/embeddings", {"model": self.model, "input": l_text},
                               timeout=TIMEOUT_EMBEDDING)
        return [d_item["embedding"] for d_item in sorted(result["data"], key=lambda d: d.get("index", 0))]


class GgufEmbedding:
    """Vectors of texts from a GGUF embedding model; the model is loaded at
    the first use, not when the program starts."""

    def __init__(self, model_path: str):
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"Embedding model file '{model_path}' is not found.")
        self.model_path = model_path
        self.llm = None

    @property
    def name(self) -> str:
        return os.path.basename(self.model_path)

    def __call__(self, l_text: list[str]) -> list[list[float]]:
        if self.llm is None:
            from llama_cpp import Llama
            self.llm = Llama(model_path=self.model_path, embedding=True, n_ctx=GGUF_CONTEXT,
                             n_batch=GGUF_CONTEXT, verbose=False)
        return self.llm.embed(l_text, truncate=True)

    def close(self):
        llm, self.llm = self.llm, None
        if llm is not None and hasattr(llm, "close"):
            llm.close()


def create_embedding(d_setup: dict):
    """ServerEmbedding, GgufEmbedding or None (search by words only) for
    the settings."""
    source = d_setup.get(KEY_SOURCE, SOURCE_NONE)
    if source in (SOURCE_OLLAMA, SOURCE_OPENAI):
        return ServerEmbedding(source, d_setup.get(KEY_URL, ""), d_setup.get(KEY_MODEL, ""))
    if source == SOURCE_GGUF:
        return GgufEmbedding(d_setup.get(KEY_PATH, ""))
    return None


def form_embedding_functions(embedding) -> tuple:
    """(embed of the fragments, embed of the question) with the prefixes
    the model was trained with."""
    prefix_document, prefix_query = take_prefixes(embedding.name)

    def embed_documents(l_text: list[str]):
        return embedding([prefix_document + text for text in l_text])

    def embed_query(l_text: list[str]):
        return embedding([prefix_query + text for text in l_text])
    return embed_documents, embed_query


def take_index_folder() -> str:
    """The index of the documents is kept in the settings folder."""
    return os.path.join(take_config_dir(), S_INDEX_FOLDER)


D_EMBEDDING = {"object": None}


def init_documents(d_setup: dict) -> str:
    """Give CrysPy the folder of the documents and the embedding model of
    the settings. Returns an error text ("" when all is fine): a wrong
    embedding model leaves the search by words."""
    if not FLAG_DOCUMENTS:
        return ""
    close_embedding()
    folder = str(d_setup.get(KEY_FOLDER, "") or "")
    cryspy.set_document_folder(folder if folder else None, cache_folder=take_index_folder())
    try:
        embedding = create_embedding(d_setup)
    except (ValueError, OSError) as error:
        cryspy.set_document_embedding(None)
        return str(error)
    D_EMBEDDING["object"] = embedding
    if embedding is None:
        cryspy.set_document_embedding(None)
    else:
        embed_documents, embed_query = form_embedding_functions(embedding)
        cryspy.set_document_embedding(embed_documents, embedding.name, embed_query=embed_query)
    return ""


def close_embedding():
    """Free a GGUF embedding model (before the program exits)."""
    embedding, D_EMBEDDING["object"] = D_EMBEDDING["object"], None
    if embedding is not None and hasattr(embedding, "close"):
        embedding.close()


def take_document_folder() -> str | None:
    """The folder CrysPy searches in (it may be given in the chat)."""
    if not FLAG_DOCUMENTS:
        return None
    from cryspy.procedure_assistant.documents import take_document_folder as take_folder
    return take_folder()


def update_index(progress: Callable | None = None) -> str:
    """Read the changed documents and make the vectors: the text of the
    tool index_documents of CrysPy."""
    from cryspy.procedure_assistant.tools_documents import tool_index_documents
    return tool_index_documents(None, progress=progress)


def form_documents_rule() -> str:
    """Rule of the system prompt when the user has a folder of documents."""
    if take_document_folder() is None:
        return ""
    return """

The user has a folder of documents (papers, books, reports). A question about
their content, about physics or a compound they may describe, or "what do my
papers say about ..." is answered with the action "search_documents" (query:
the key words, in the language of the documents) and only from the fragments
it gives; cite every fact as [file, page] and say so when they do not answer,
e.g. what do my papers say about extinction in TbTe3?:
  [{"action": "search_documents", "arguments": {"query": "TbTe3 extinction"}}]"""

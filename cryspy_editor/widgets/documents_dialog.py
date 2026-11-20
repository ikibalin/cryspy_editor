"""Dialog "AI assistant: documents": the folder of the papers, books and
reports of the user that the assistant searches (search_documents of
CrysPy), the embedding model for the search by meaning, and the update of
the index in a background thread."""
import html
import os
import time

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from cryspy_editor import error_guard

from cryspy_editor.widgets.assistant_documents import (
    D_EMBEDDING_SOURCE_NAMES,
    KEY_FOLDER,
    KEY_MODEL,
    KEY_PATH,
    KEY_SOURCE,
    KEY_URL,
    L_RECOMMENDED_EMBEDDINGS,
    SOURCE_NONE,
    init_documents,
    update_index,
)
from cryspy_editor.widgets.assistant_models import (
    D_DEFAULT_URL,
    SOURCE_GGUF,
    list_server_models,
)

WINDOW_TITLE = "AI assistant: documents"
PROGRESS_INTERVAL = 0.3
L_KEYS = (KEY_FOLDER, KEY_SOURCE, KEY_URL, KEY_MODEL, KEY_PATH)


def form_documents_hint_html() -> str:
    ls_model = "".join(f"<li><b>{html.escape(name)}</b>: {html.escape(text)}</li>"
                       for name, text in L_RECOMMENDED_EMBEDDINGS)
    return (
        "<p>The assistant answers from your papers, books and reports (PDF, txt, md; "
        "subfolders too) and cites the file and the page. Ask it e.g. <i>what do my papers "
        "say about the extinction in TbTe3?</i></p>"
        "<p>The search by words (BM25) needs nothing. An <b>embedding model</b> also finds "
        "fragments by meaning and in another language; it is a small model apart from the "
        "chat model:</p>"
        f"<ul>{ls_model}</ul>"
        "<p>The first update makes a vector for every fragment (minutes for many files); "
        "later only new and changed files are read. PDF needs <code>pip install pypdf</code> "
        "(<code>cryspy[pdf]</code>).</p>")


class IndexWorker(QObject):
    """Updates the index of the documents in a background thread."""

    finished = pyqtSignal(str)
    progress_text = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.flag_stop = False
        self.time_progress = 0.

    def on_progress(self, info: dict):
        now = time.monotonic()
        if now - self.time_progress > PROGRESS_INTERVAL:
            self.time_progress = now
            self.progress_text.emit(f"{info.get('label', 'Working')} {info.get('step', 0)}/"
                                    f"{info.get('n_step', 0)} ...")
        return not self.flag_stop

    def run(self):
        try:
            text = update_index(progress=self.on_progress)
        except BaseException as error:  # noqa: BLE001 - the thread must end with a signal
            text = f"Error: {type(error).__name__}: {error}"
        self.finished.emit(text)


class DocumentsDialog(QtWidgets.QDialog):
    """d_setup: the settings of CrysPy Editor, changed on Save;
    save_settings() writes them."""

    def __init__(self, d_setup: dict, save_settings=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(WINDOW_TITLE)
        self.d_setup = d_setup
        self.save_settings = save_settings
        self.thread = None
        self.worker = None

        layout = QtWidgets.QVBoxLayout(self)
        hint = QtWidgets.QTextBrowser(self)
        hint.setHtml(form_documents_hint_html())
        hint.setMinimumHeight(220)
        layout.addWidget(hint)

        self.form = QtWidgets.QFormLayout()
        layout_folder = QtWidgets.QHBoxLayout()
        self.line_folder = QtWidgets.QLineEdit(str(d_setup.get(KEY_FOLDER, "")), self)
        self.line_folder.setMinimumWidth(400)
        layout_folder.addWidget(self.line_folder)
        button_folder = QtWidgets.QPushButton("Browse...", self)
        button_folder.clicked.connect(self.browse_folder)
        layout_folder.addWidget(button_folder)
        self.form.addRow("Folder of documents", layout_folder)

        self.cb_source = QtWidgets.QComboBox(self)
        for source, name in D_EMBEDDING_SOURCE_NAMES.items():
            self.cb_source.addItem(name, source)
        index = self.cb_source.findData(d_setup.get(KEY_SOURCE, SOURCE_NONE))
        self.cb_source.setCurrentIndex(max(index, 0))
        self.form.addRow("Embedding model", self.cb_source)

        self.line_url = QtWidgets.QLineEdit(str(d_setup.get(KEY_URL, "")), self)
        self.form.addRow("Server address", self.line_url)
        layout_model = QtWidgets.QHBoxLayout()
        self.cb_model = QtWidgets.QComboBox(self)
        self.cb_model.setEditable(True)
        self.cb_model.setMinimumWidth(300)
        self.cb_model.setEditText(str(d_setup.get(KEY_MODEL, "")))
        layout_model.addWidget(self.cb_model)
        self.button_list = QtWidgets.QPushButton("List models", self)
        self.button_list.clicked.connect(self.list_models)
        layout_model.addWidget(self.button_list)
        self.form.addRow("Model of the server", layout_model)

        layout_path = QtWidgets.QHBoxLayout()
        self.line_path = QtWidgets.QLineEdit(str(d_setup.get(KEY_PATH, "")), self)
        layout_path.addWidget(self.line_path)
        button_path = QtWidgets.QPushButton("Browse...", self)
        button_path.clicked.connect(self.browse_model)
        layout_path.addWidget(button_path)
        self.form.addRow("Model file (*.gguf)", layout_path)
        self.l_server_fields = [self.line_url, layout_model]
        self.l_gguf_fields = [layout_path]
        layout.addLayout(self.form)

        self.label_status = QtWidgets.QLabel("", self)
        self.label_status.setWordWrap(True)
        self.label_status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.label_status)

        buttons = QtWidgets.QDialogButtonBox(self)
        self.button_update = buttons.addButton("Save and update index", QtWidgets.QDialogButtonBox.ActionRole)
        self.button_update.clicked.connect(self.update_index)
        self.button_stop = buttons.addButton("Stop", QtWidgets.QDialogButtonBox.ActionRole)
        self.button_stop.clicked.connect(self.stop)
        self.button_stop.setEnabled(False)
        buttons.addButton(QtWidgets.QDialogButtonBox.Save)
        buttons.addButton(QtWidgets.QDialogButtonBox.Close)
        buttons.accepted.connect(self.save_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.cb_source.currentIndexChanged.connect(self.on_source_changed)
        self.on_source_changed()

    def source(self) -> str:
        return self.cb_source.currentData()

    def _set_row_visible(self, field, flag: bool):
        label = self.form.labelForField(field)
        if label is not None:
            label.setVisible(flag)
        if isinstance(field, QtWidgets.QLayout):
            for ind in range(field.count()):
                widget = field.itemAt(ind).widget()
                if widget is not None:
                    widget.setVisible(flag)
        else:
            field.setVisible(flag)

    def on_source_changed(self, *args):
        source = self.source()
        for field in self.l_server_fields:
            self._set_row_visible(field, source in D_DEFAULT_URL)
        for field in self.l_gguf_fields:
            self._set_row_visible(field, source == SOURCE_GGUF)
        if source in D_DEFAULT_URL and self.line_url.text().strip() in [""] + list(D_DEFAULT_URL.values()):
            self.line_url.setText(D_DEFAULT_URL[source])

    def browse_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Folder of documents", self.line_folder.text() or os.path.expanduser("~"))
        if folder:
            self.line_folder.setText(folder)

    def browse_model(self):
        f_dir = os.path.dirname(self.line_path.text())
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose embedding model", f_dir if os.path.isdir(f_dir) else os.path.expanduser("~"),
            "GGUF models (*.gguf);; All Files (*)")
        if file_name:
            self.line_path.setText(file_name)

    def list_models(self):
        try:
            l_model = list_server_models(self.source(), self.line_url.text().strip())
        except ConnectionError as error:
            self.label_status.setText(str(error))
            return
        text = self.cb_model.currentText()
        self.cb_model.clear()
        self.cb_model.addItems(l_model)
        self.cb_model.setEditText(text if text or not l_model else l_model[0])

    def values(self) -> dict:
        return {KEY_FOLDER: self.line_folder.text().strip(), KEY_SOURCE: self.source(),
                KEY_URL: self.line_url.text().strip(), KEY_MODEL: self.cb_model.currentText().strip(),
                KEY_PATH: self.line_path.text().strip()}

    def apply(self) -> bool:
        """Save the values in the settings and give them to CrysPy; False
        (with the reason shown) when they are wrong."""
        d_value = self.values()
        if d_value[KEY_FOLDER] and not os.path.isdir(os.path.expanduser(d_value[KEY_FOLDER])):
            self.label_status.setText(f"Error: the folder '{d_value[KEY_FOLDER]}' is not found.")
            return False
        self.d_setup.update(d_value)
        if self.save_settings is not None:
            self.save_settings()
        error = init_documents(self.d_setup)
        if error:
            self.label_status.setText(f"Error: {error} The search is by words only.")
            return False
        return True

    def save_and_close(self):
        if self.is_busy():
            return
        if self.apply():
            self.accept()

    def is_busy(self) -> bool:
        return self.thread is not None

    def update_index(self):
        if self.is_busy() or not self.apply():
            return
        if not self.d_setup.get(KEY_FOLDER):
            self.label_status.setText("Error: choose the folder of documents.")
            return
        self.button_update.setEnabled(False)
        self.button_stop.setEnabled(True)
        self.label_status.setText("Reading documents ...")
        self.thread = QThread(self)
        error_guard.prepare_thread(self.thread)  # 512 KB on macOS by default
        self.worker = IndexWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress_text.connect(self.label_status.setText)
        self.worker.finished.connect(self.on_index_finished)
        self.thread.start()

    def stop(self):
        if self.worker is not None:
            self.worker.flag_stop = True

    def on_index_finished(self, text: str):
        self.label_status.setText(text)
        self.thread.quit()
        self.thread.wait()
        self.thread = None
        self.worker = None
        self.button_update.setEnabled(True)
        self.button_stop.setEnabled(False)

    def wait(self):
        """Stop the update and wait for it (the dialog is closed)."""
        if self.thread is not None:
            self.stop()
            self.thread.quit()
            self.thread.wait()

    def reject(self):
        if self.is_busy():
            self.stop()
            return
        super().reject()

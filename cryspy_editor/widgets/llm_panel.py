"""Panel with a chat to a local LLM working on the current CrysPy object."""
import html

from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal

from cryspy_editor.widgets.llm_worker import LLMWorker, LLMLoadWorker

PLACEHOLDER = ("Ask a question or request an action, e.g. 'refine the cell', "
               "'how to describe thermal vibrations?'")


class LLMPanel(QtWidgets.QWidget):
    """Chat panel. The model is loaded in background by load_model."""

    signal_object_changed = pyqtSignal()
    signal_model_loaded = pyqtSignal(str)  # model path, empty if failed

    def __init__(self, take_cryspy_obj=None, parent=None):
        super().__init__(parent)
        self.llm = None
        self.take_cryspy_obj = take_cryspy_obj
        self.thread = None
        self.worker = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout_title = QtWidgets.QHBoxLayout()
        self.label_model = QtWidgets.QLabel("AI assistant: no model loaded")
        layout_title.addWidget(self.label_model, 1)
        self.button_clear = QtWidgets.QPushButton("Clear chat")
        self.button_clear.clicked.connect(self.clear_chat)
        layout_title.addWidget(self.button_clear)
        layout.addLayout(layout_title)

        self.history_view = QtWidgets.QTextEdit(self)
        self.history_view.setReadOnly(True)
        layout.addWidget(self.history_view)

        self.input_line = QtWidgets.QLineEdit(self)
        self.input_line.setPlaceholderText(PLACEHOLDER)
        self.input_line.returnPressed.connect(self.on_send)
        self.input_line.setEnabled(False)
        layout.addWidget(self.input_line)

    def is_busy(self) -> bool:
        return self.thread is not None

    def _start_thread(self, worker, on_finished, on_error):
        self.thread = QThread()
        self.worker = worker
        worker.moveToThread(self.thread)
        self.thread.started.connect(worker.run)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.finished.connect(self.thread.quit)
        worker.error.connect(self.thread.quit)
        self.thread.finished.connect(self._thread_done)
        self.thread.start()

    def _thread_done(self):
        self.thread.deleteLater()
        self.thread = None
        self.worker = None

    def load_model(self, model_path: str, settings: dict = None):
        if self.is_busy():
            return
        self.llm = None
        self.input_line.setEnabled(False)
        self.label_model.setText(f"AI assistant: loading {model_path} ...")
        self._start_thread(
            LLMLoadWorker(model_path, settings), self.on_model_loaded,
            self.on_model_error)

    def unload_model(self):
        if self.is_busy():
            return
        self.llm = None
        self.input_line.setEnabled(False)
        self.label_model.setText("AI assistant: no model loaded")

    def on_model_loaded(self, llm):
        self.llm = llm
        self.label_model.setText(f"AI assistant: {llm.model_name}")
        self.input_line.setEnabled(True)
        self.input_line.setFocus()
        self.signal_model_loaded.emit(llm.model_path)

    def on_model_error(self, msg: str):
        self.label_model.setText("AI assistant: no model loaded")
        self.append_history("Error", msg)
        self.signal_model_loaded.emit("")

    def clear_chat(self):
        self.history_view.clear()
        if self.llm is not None:
            self.llm.clear_history()

    def append_history(self, role: str, text: str):
        # escape: replies contain CIF text and '<' signs
        self.history_view.append(
            f"<b>{html.escape(role)}:</b>"
            f"<pre style='white-space: pre-wrap'>{html.escape(text)}</pre>")

    def on_send(self):
        question = self.input_line.text().strip()
        if question == "" or self.llm is None or self.is_busy():
            return
        self.append_history("User", question)
        self.input_line.clear()
        self.input_line.setEnabled(False)
        self.input_line.setPlaceholderText("Thinking...")
        cryspy_obj = None
        if self.take_cryspy_obj is not None:
            cryspy_obj = self.take_cryspy_obj()
        worker = LLMWorker(self.llm, question, cryspy_obj)
        worker.action_started.connect(
            lambda tool: self.input_line.setPlaceholderText(
                f"Running '{tool}'..."))
        self._start_thread(worker, self.on_reply, self.on_error)

    def _ready_for_input(self):
        self.input_line.setEnabled(True)
        self.input_line.setPlaceholderText(PLACEHOLDER)
        self.input_line.setFocus()

    def on_reply(self, result: dict):
        self.append_history("AI", result["text"])
        self._ready_for_input()
        if result.get("flag_object_changed", False):
            self.signal_object_changed.emit()

    def on_error(self, msg: str):
        self.append_history("Error", msg)
        self._ready_for_input()

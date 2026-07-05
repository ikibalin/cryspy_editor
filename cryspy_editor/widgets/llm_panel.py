# ai_panel.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QApplication
)
from PyQt5.QtCore import Qt, QThread
import sys
import cryspy
from .llm_local import LLMLocal
from .llm_worker import LLMWorker


class LLMPanel(QWidget):
    def __init__(self, model_path:str="Llama-3-8B-Instruct-GGUF-Q4_K_M.gguf", take_cryspy_obj=None, output_text_editor=None,parent=None):
        super().__init__(parent)
        self.setWindowTitle("CrysPy AI Assistant")

        self.llm = LLMLocal(model_path)
        self.take_cryspy_obj = take_cryspy_obj

        self.layout = QVBoxLayout(self)

        if output_text_editor is None:
            self.history_view = QTextEdit(self)
            self.history_view.setReadOnly(True)
        else:
            self.history_view = output_text_editor

        self.input_line = QLineEdit(self)
        self.input_line.setPlaceholderText("Ask a question or request an action...")

        # Pressing Enter triggers send
        self.input_line.returnPressed.connect(self.on_send)

        self.layout.addWidget(self.history_view)
        self.layout.addWidget(self.input_line)

        self.thread = None

    def append_history(self, role: str, text: str):
        self.history_view.append(f"{role}: {text}")

    def on_send(self):
        question = self.input_line.text().strip()
        if not question:
            return
        self.history_view.clear()
        self.append_history("User", question)
        self.input_line.clear()

        # Disable button during processing
        self.input_line.setEnabled(False)
        self.input_line.setPlaceholderText("Thinking...")

        # Create worker thread
        self.thread = QThread()
        self.worker = LLMWorker(self.llm, question, self.take_cryspy_obj())
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_reply)
        self.worker.error.connect(self.on_error)

        # Cleanup
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_reply(self, reply: str):
        self.append_history("AI", reply)
        self.input_line.setEnabled(True)
        self.input_line.setPlaceholderText("Ask a question or request an action...")

    def on_error(self, msg: str):
        self.append_history("AI", f"[Error] {msg}")
        self.input_line.setEnabled(True)
        self.input_line.setPlaceholderText("Ask a question or request an action...")


def main(cryspy_obj=None):
    app = QApplication(sys.argv)
    def take_cryspy_obj():
        return cryspy.file_to_globaln(r'/Users/ikibalin/Library/Mobile Documents/com~apple~CloudDocs/exp_D3/CH30_35K.rcif')
    panel = LLMPanel(take_cryspy_obj=take_cryspy_obj, model_path=f"../llm_models/Llama-3-8B-Instruct-GGUF-Q4_K_M.gguf")
    panel.resize(600, 400)
    panel.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

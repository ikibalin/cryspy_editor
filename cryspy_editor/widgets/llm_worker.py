"""Background workers for the local LLM: loading a model and answering."""
import traceback

from PyQt5.QtCore import QObject, pyqtSignal


class LLMLoadWorker(QObject):
    finished = pyqtSignal(object)  # emits LLMLocal
    error = pyqtSignal(str)

    def __init__(self, model_path: str):
        super().__init__()
        self.model_path = model_path

    def run(self):
        try:
            from cryspy_editor.widgets.llm_local import LLMLocal
            self.finished.emit(LLMLocal(self.model_path))
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}")


class LLMWorker(QObject):
    finished = pyqtSignal(dict)  # emits result of LLMLocal.answer
    error = pyqtSignal(str)
    action_started = pyqtSignal(str)

    def __init__(self, llm, question, cryspy_obj):
        super().__init__()
        self.llm = llm
        self.question = question
        self.cryspy_obj = cryspy_obj

    def run(self):
        try:
            result = self.llm.answer(
                self.question, self.cryspy_obj,
                callback_action=self.action_started.emit)
            self.finished.emit(result)
        except Exception as e:
            traceback.print_exc()
            self.error.emit(f"{type(e).__name__}: {e}")

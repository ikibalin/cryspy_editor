# worker.py
from PyQt5.QtCore import QObject, pyqtSignal

class LLMWorker(QObject):
    finished = pyqtSignal(str)     # emits the AI reply
    error = pyqtSignal(str)        # emits error text

    def __init__(self, llm, question, cryspy_obj):
        super().__init__()
        self.llm = llm
        self.question = question
        self.cryspy_obj = cryspy_obj

    def run(self):
        try:
            decision = self.llm.decide_if_action_required(self.question)

            if decision["requires_action"] and self.cryspy_obj is not None:
                print('The action is required')
                reply = self.llm.decide_and_execute(self.question, self.cryspy_obj)
            else:
                print('The action is not required')
                reply = self.llm.ask(self.question)

            self.finished.emit(reply)

        except Exception as e:
            self.error.emit(str(e))

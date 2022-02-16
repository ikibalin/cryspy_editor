"""WEditCif class."""
from typing import Callable, NoReturn
from PyQt5 import QtWidgets, QtCore, QtGui


# class WEditCif(QtWidgets.QScrollArea):
class WEditCif(QtWidgets.QTextEdit):
    """WFunction class."""

    def __init__(self, text: str, rewrite_item: Callable, parent=None):
        super(WEditCif, self).__init__(parent)

        self.setAcceptRichText(True)
        self.setSizePolicy(
                QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                      QtWidgets.QSizePolicy.Expanding))
        self.setFont(QtGui.QFont("Courier", 8, QtGui.QFont.Normal))
        self.setAlignment(QtCore.Qt.AlignTop)
        self.setStyleSheet("background-color:white;")
        self.setText(text)
        self.text_changed = False
        self.textChanged.connect(lambda : setattr(self, "text_changed", True))
        self.rewrite_item = rewrite_item

    def focusOutEvent(self, event):
        """Submit changes just before focusing out."""
        QtWidgets.QTextEdit.focusOutEvent(self, event)
        if self.text_changed:
            s_text = self.toPlainText()
            self.rewrite_item(s_text)
            self.text_changed = False


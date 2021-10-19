"""WEditCif class."""
from typing import Callable, NoReturn
from PyQt5 import QtWidgets, QtCore, QtGui


# class WEditCif(QtWidgets.QScrollArea):
class WEditCif(QtWidgets.QTextEdit):
    """WFunction class."""

    def __init__(self, parent=None):
        super(WEditCif, self).__init__(parent)

        self.setAcceptRichText(True)
        self.setSizePolicy(
                QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                      QtWidgets.QSizePolicy.Expanding))
        self.setFont(QtGui.QFont("Courier", 8, QtGui.QFont.Normal))
        self.setAlignment(QtCore.Qt.AlignTop)
        self.setStyleSheet("background-color:white;")
        self.text_changed = False
        self.textChanged.connect(lambda : setattr(self, "text_changed", True))
        self.object = None

    def set_function_object_refresh(
            self, function_object_refresh: Callable) -> NoReturn:
        """Set function when the object representation has to be refreshed."""
        self.func_object_refresh = function_object_refresh

    def set_object(self, obj):
        """Set object."""
        self.setText(str(obj))
        self.setToolTip(obj.__doc__)
        self.object = obj
        self.text_changed = False

    def save_object(self):
        stext = self.toPlainText()
        obj2 = self.object.from_cif(stext)
        if obj2 is not None:
            self.object.copy_from(obj2)

    def focusOutEvent(self, event):
        """Submit changes just before focusing out."""
        QtWidgets.QTextEdit.focusOutEvent(self, event)
        if self.text_changed:
            self.save_object()
            # self.func_object_refresh()

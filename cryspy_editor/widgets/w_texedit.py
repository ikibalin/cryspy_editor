
from typing import Callable, NoReturn
from PyQt5 import QtWidgets, QtCore, QtGui
import cryspy_editor.widgets.ui_setting as ui_setting

class WTextEdit(QtWidgets.QTextEdit):
    """WFunction class."""

    def __init__(self, parent=None):
        super(WTextEdit, self).__init__(parent)

        self.setAcceptRichText(True)
        self.setSizePolicy(
                QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                      QtWidgets.QSizePolicy.Expanding))
        font_size = ui_setting.get_font_size()
        self.setFont(QtGui.QFont("Courier", font_size, QtGui.QFont.Normal))
        self.setAlignment(QtCore.Qt.AlignTop)
        # self.setStyleSheet("background-color:white;")
    
    def upload_font_size(self):
        current_font = self.font()
        font_size = ui_setting.get_font_size()
        current_font.setPointSize(font_size)
        self.setFont(current_font)
        
    def wheelEvent(self, e):
        if e is None:
            pass
        elif e.modifiers() == QtCore.Qt.ControlModifier:
            delta = e.angleDelta().y()
            current_font = self.font()
            current_size = current_font.pointSize()
            if delta > 0:
                new_size = current_size + 1
            else:
                new_size = current_size - 1
            if new_size < 5 or new_size > 60:
                return
            current_font.setPointSize(new_size)
            self.setFont(current_font)
            ui_setting.save_font_size(new_size)

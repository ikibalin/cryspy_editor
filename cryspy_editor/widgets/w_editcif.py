"""WEditCif class."""
from typing import Callable, NoReturn
from PyQt5 import QtWidgets, QtCore, QtGui
import cryspy_editor.widgets.ui_setting as ui_setting

# class WEditCif(QtWidgets.QScrollArea):
class WEditCif(QtWidgets.QTextEdit):
    """WFunction class."""

    def __init__(self, text: str, rewrite_item: Callable, parent=None, text_placeholder:str="", s_info:str=""):
        super(WEditCif, self).__init__(parent)

        self.setAcceptRichText(True)
        self.setSizePolicy(
                QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                      QtWidgets.QSizePolicy.Expanding))
        font_size = ui_setting.get_font_size()
        self.setFont(QtGui.QFont("Courier", font_size, QtGui.QFont.Normal))

        self.setAlignment(QtCore.Qt.AlignTop)
        self.setPlaceholderText(s_info+"\n\n"+text_placeholder)
        # self.setStyleSheet("background-color:white;")
        self.setText(text)
        self.text_changed = False
        self.textChanged.connect(lambda : setattr(self, "text_changed", True))
        self.rewrite_item = rewrite_item

    def focusOutEvent(self, event):
        """Submit changes just before focusing out."""
        QtWidgets.QTextEdit.focusOutEvent(self, event)
        self.rewrite_item_by_printed_text()

    def rewrite_item_by_printed_text(self):
        if self.text_changed:
            s_text = self.toPlainText()
            self.rewrite_item(s_text)
            self.text_changed = False

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
            current_font.setPointSize(new_size)
            # font = QtGui.QFont("Courier New")
            # font.setPointSize(new_size)
            ui_setting.save_font_size(new_size)
            ui_setting.write_to_setup_file()
            self.setFont(current_font)
            # event.accept()
        else:
            super().wheelEvent(e)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.exec_(event.globalPos())
        event.accept()


        
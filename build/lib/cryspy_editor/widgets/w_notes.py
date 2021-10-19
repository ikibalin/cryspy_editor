"""Notes widget."""
import os
from PyQt5 import QtWidgets, QtCore, QtGui

from cryspy import md_to_html

class WNotes(QtWidgets.QTextEdit):
    """WFunction class."""

    def __init__(self, parent=None):
        super(WNotes, self).__init__(parent)

        self.setAcceptRichText(True)
        self.setSizePolicy(
                QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                      QtWidgets.QSizePolicy.Expanding))
        self.setFont(QtGui.QFont("Courier", 8, QtGui.QFont.Normal))
        self.setAlignment(QtCore.Qt.AlignTop)
        self.setStyleSheet("background-color:white;")

        self.flag_text_changed = False
        self.textChanged.connect(lambda : setattr(self, "flag_text_changed",
                                                  True))
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)        
        self.customContextMenuRequested.connect(self.open_menu)
        self.file_name = None
        self.function_save_as = None
        self.function_open = None
        self.function_close_notes = None
        self.function_notes_to_html = None

    def set_function_save_as(self, function_save_as):
        """Set function for "Save notes as..." action."""
        self.function_save_as = function_save_as

    def set_function_open(self, function_open):
        """Set function for "Open notes" action."""
        self.function_open = function_open

    def set_function_close_notes(self, function_close_notes):
        """Set function for "Close notes" action."""
        self.function_close_notes = function_close_notes

    def set_function_notes_to_html(self, function_notes_to_html):
        """Internal function to display notes in Tab 'Notes'."""
        self.function_notes_to_html = function_notes_to_html

    def set_file_name(self, file_name:str):
        """Set object."""
        self.file_name = file_name

    def open_menu(self, position):
        """Context menu."""
        menu = QtWidgets.QMenu(self)
        open_notes = QtWidgets.QAction('Open notes', menu)
        open_notes.triggered.connect(self.open_new_notes)
        menu.addAction(open_notes)

        save_as = QtWidgets.QAction('Save notes as...', menu)
        save_as.triggered.connect(self.save_as)
        menu.addAction(save_as)

        close_notes = QtWidgets.QAction('Close notes', menu)
        close_notes.triggered.connect(self.close_notes)
        menu.addAction(close_notes)

        export_to_html = QtWidgets.QAction('Export to html', menu)
        export_to_html.triggered.connect(self.export_to_html)
        menu.addAction(export_to_html)

        menu.exec_(self.viewport().mapToGlobal(position))

    def close_notes(self):
        self.file_name = None
        self.clear()
        if self.function_close_notes is not None:
            self.function_close_notes()

    def open_new_notes(self):
        if self.function_open is not None:
            self.function_open()

    def open_notes(self):
        if self.file_name is None:
            return
        if os.path.isfile(self.file_name):
            with open(self.file_name, "r") as fid:
                s_text = fid.read()
            self.setText(s_text)
            if self.function_notes_to_html is not None:
                self.function_notes_to_html(md_to_html(s_text))

        self.flag_text_changed = False

    def save_as(self):
        if self.function_save_as is not None:
            self.function_save_as()
        self.flag_text_changed = False

    def save(self):

        s_text = self.toPlainText().strip()
        if s_text == "":
            return
        
        if self.function_notes_to_html is not None:
            self.function_notes_to_html(md_to_html(s_text))

        file_name = self.file_name 
        if file_name is None:
            return

        with open(file_name, "w") as fid:
            fid.write(s_text)
        self.flag_text_changed = False

    def focusOutEvent(self, event):
        """Submit changes just before focusing out."""
        QtWidgets.QTextEdit.focusOutEvent(self, event)
        if  self.flag_text_changed:
            self.save()
        
    def export_to_html(self):
        s_text = self.toPlainText().strip()
        if s_text == "":
            return
        file_name = self.file_name 
        if file_name is None:
            self.save_as()
            file_name = self.file_name 
        ind_point = file_name.rfind(".")
        file_name_pdf = f"{file_name[:ind_point]:}.html"
        s_html = md_to_html(s_text)
        with open(file_name_pdf, "w") as fid:
            fid.write(s_html)
        

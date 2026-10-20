"""Window with the help of CrysPy (works without the AI assistant)."""
from PyQt5 import QtWidgets

from cryspy import get_help, help_topics


class HelpDialog(QtWidgets.QDialog):
    """Search line and the text of the found CrysPy help pages."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CrysPy help")
        self.resize(800, 600)
        layout = QtWidgets.QVBoxLayout(self)
        self.line_query = QtWidgets.QLineEdit(self)
        self.line_query.setPlaceholderText(
            "Topic, category or question, e.g. 'thermal vibrations', "
            "'atom_site_aniso', 'how to describe multipoles'")
        self.line_query.returnPressed.connect(self.show_help)
        layout.addWidget(self.line_query)
        self.text_help = QtWidgets.QTextBrowser(self)
        self.text_help.setOpenExternalLinks(True)
        layout.addWidget(self.text_help)
        self.text_help.setMarkdown(help_topics().replace("\n", "\n\n"))

    def show_help(self):
        query = self.line_query.text().strip()
        if query == "":
            return
        self.text_help.setMarkdown(get_help(query))

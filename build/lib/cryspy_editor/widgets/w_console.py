"""WConsole class."""
from PyQt5 import QtWidgets, QtCore, QtGui


class WConsole(QtWidgets.QScrollArea):
    """WFunction class."""

    def __init__(self, parent=None):
        super(WConsole, self).__init__(parent)

        self.setWidgetResizable(True)

        self.wlabel = QtWidgets.QLabel()
        self.wlabel.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                  QtWidgets.QSizePolicy.Expanding))
        self.wlabel.setFont(QtGui.QFont("Courier", 8, QtGui.QFont.Normal))
        self.wlabel.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.wlabel.setAlignment(QtCore.Qt.AlignTop)
        self.wlabel.setWordWrap(True)
        self.wlabel.setStyleSheet("background-color:white;")

        self.setWidget(self.wlabel)

    def setText(self, text: str):
        """Set text."""
        self.wlabel.setText(text)

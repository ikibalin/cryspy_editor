from PyQt5 import QtCore, QtGui, QtWidgets, Qt
from cryspy_editor.widgets.w_output import WOutput


def text_from_d_info(d_info: dict = None):
    """Take text from print key of d_info."""
    s_out = ""
    if d_info is not None:
        s_out = d_info["print"]
        if "d_info" in d_info.keys():
            s_out_2 = text_from_d_info(d_info["d_info"])
            s_out += "\n\n" + s_out_2
    return s_out


class CCalcWindow(QtWidgets.QMainWindow):
    """During calculations."""

    def __init__(self, parent=None):
        super(CCalcWindow, self).__init__(parent)
        self.d_info = None
        self.init_widget()
        self.setWindowTitle(
            'Calculations are running ... (DO NOT CLOSE THE WINDOW)')

    def init_widget(self):
        """Init widget."""
        cw = QtWidgets.QWidget(self)
        self.layout = QtWidgets.QHBoxLayout()
        lay_v = QtWidgets.QVBoxLayout()

        self.label = WOutput(cw)
        self.btn = QtWidgets.QPushButton()
        self.btn.clicked.connect(self.stop_calc)
        lay_v.addWidget(self.label)
        lay_v.addWidget(self.btn)

        self.layout.addLayout(lay_v)
        cw.setLayout(self.layout)
        self.setCentralWidget(cw)
        self.timer = QtCore.QBasicTimer()

    def timerEvent(self, e):
        s_text = text_from_d_info(self.d_info)
        self.label.setText(s_text)

    def set_d_info(self, d_info: dict = None):
        self.d_info = d_info
        if self.d_info is not None:
            self.btn.setEnabled(True)
            self.btn.setText("Stop")
            self.label.setText(self.d_info["print"])

    def stop_calc(self):
        if self.d_info is not None:
            self.d_info["stop"] = True
            self.btn.setText("Wait a second.")
            self.btn.setEnabled(False)


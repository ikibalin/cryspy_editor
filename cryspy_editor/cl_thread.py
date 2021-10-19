import traceback

from cryspy_editor.cl_calc_window import CCalcWindow
from PyQt5 import QtCore, QtGui, QtWidgets, Qt

class CThread(QtCore.QThread):
    """CThread class."""
    signal_start = QtCore.pyqtSignal()
    signal_end = QtCore.pyqtSignal()
    signal_refresh = QtCore.pyqtSignal()
    signal_take_attributes = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.message = None
        self.function = None
        self.arguments = None
        self.output = None
        self.d_info = None
        self.function_run_calculations = None
        self.function_end_calculations = None

    def run(self):
        """Run."""
        func = self.function
        arg = self.arguments
        n_row_need = func.__code__.co_argcount
        l_var_name = func.__code__.co_varnames[:n_row_need]

        self.signal_start.emit()

        try:
            out = func(*arg)
        except Exception:
            out = "MISTAKE DURING PROGRAM EXECUTION\n\n" + \
                str(traceback.format_exc())
        print(80*"*")
        print("Calculations stopped")
        print(80*"*")
        if out is not None:
            print("Result of function is \n")
            print(out)
        self.signal_end.emit()
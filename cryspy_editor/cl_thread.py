
import traceback

from PyQt5 import QtCore

import cryspy

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
        flag_out = False
        if len(arg) >= 1:
            if not(isinstance(arg[0], cryspy.GlobalN)):
                flag_out = True
        try:
            out = func(*arg)
        except Exception:
            flag_out = True
            out = "ERROR DURING PROGRAM EXECUTION\n\n" + \
                str(traceback.format_exc())
        print(80*"*")
        print("Calculations are completed.")
        print(80*"*")
        if ((out is not None) and flag_out):
            print("Result of function is \n")
            print(out)
        self.signal_end.emit()


import io
import os
from contextlib import redirect_stdout


import traceback

from PyQt5 import QtCore

import cryspy


class CalculationStopped(Exception):
    """Raised in the calculation thread when the user presses Stop."""


class COutputLogget(QtCore.QObject):
    signal_refresh = QtCore.pyqtSignal()
    def __init__(self):
        super(COutputLogget, self).__init__()
        self.out_terminal = io.StringIO()
        self.l_text_permanent = []
        self.text_last = ""
        self.flag_stop = False

    def write(self,*arg):
        # Python code cannot be interrupted from another thread; procedures
        # print their progress, so the next print ends the calculation
        if self.flag_stop:
            self.flag_stop = False
            raise CalculationStopped("Calculation is stopped by the user.")
        if len(arg) > 0:
            text = str(arg[0])
            if "\r" in text:
                pass
            elif "\r" in text:
                self.text_last = text
            elif "\n" in text:
                if self.text_last != "\n":
                    self.l_text_permanent.append(self.text_last.strip())
                self.text_last = text
            else:
                self.text_last = text
        self.signal_refresh.emit()
        return self.out_terminal.write(*arg)

    def flush(self,*arg):
        return self.out_terminal.flush(*arg)

    def getvalue(self,*arg):
        return self.out_terminal.getvalue(*arg)

    def read(self,*arg):
        return self.out_terminal.read(*arg)

    def close(self,*arg):
        return self.out_terminal.close(*arg)


    def detach(self,*arg):
        return self.out_terminal.detach(*arg)
        
    def encoding(self,*arg):
        return self.out_terminal.encoding(*arg)
        
    def errors(self,*arg):
        return self.out_terminal.errors(*arg)
        
    def fileno(self,*arg):
        return self.out_terminal.fileno(*arg)
        
    def isatty(self,*arg):
        return self.out_terminal.isatty(*arg)
        
    def line_buffering(self,*arg):
        return self.out_terminal.line_buffering(*arg)
        
    def newlines(self,*arg):
        return self.out_terminal.newlines(*arg)
        
    def readable(self,*arg):
        return self.out_terminal.readable(*arg)
        
    def readline(self,*arg):
        return self.out_terminal.readline(*arg)
        
    def seek(self,*arg):
        return self.out_terminal.seek(*arg)
        
    def seekable(self,*arg):
        return self.out_terminal.seekable(*arg)
    def tell(self,*arg):
        return self.out_terminal.tell(*arg)
    def truncate(self,*arg):
        return self.out_terminal.truncate(*arg)
    def writable(self,*arg):
        return self.out_terminal.writable(*arg)
    def writelines(self,*arg):
        return self.out_terminal.writelines(*arg)

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
        # folder of the opened file: CrysPy procedures write their output
        # files (.den, sections, ...) to relative paths
        self.work_dir = None
        self.function_run_calculations = None
        self.function_end_calculations = None

    def request_stop(self):
        """Stop the running calculation at its next printed message."""
        out_terminal = getattr(self, "out_terminal", None)
        if out_terminal is not None and self.isRunning():
            out_terminal.flag_stop = True

    def run(self):
        """Run."""
        func = self.function
        arg = self.arguments
        n_row_need = func.__code__.co_argcount
        l_var_name = func.__code__.co_varnames[:n_row_need]
        
        self.out_terminal = COutputLogget()
        self.flag_stopped = False
        self.signal_start.emit()
        flag_out = False
        if len(arg) >= 1:
            if not(isinstance(arg[0], cryspy.GlobalN)):
                flag_out = True
        cwd = os.getcwd()
        try:
            flag_out = True
            if self.work_dir is not None and os.path.isdir(self.work_dir):
                os.chdir(self.work_dir)
            with redirect_stdout(self.out_terminal):
                out = func(*arg)
        except CalculationStopped as e:
            self.flag_stopped = True
            out = str(e)
        except Exception:
            flag_out = True
            out = "ERROR DURING PROGRAM EXECUTION\n\n" + \
                str(traceback.format_exc())
        finally:
            os.chdir(cwd)
        self.out_terminal.write(45*"*"+"\n")
        self.out_terminal.write("Calculations are completed.\n")
        self.out_terminal.write(45*"*"+"\n")
        if ((out is not None) and flag_out):
            self.out_terminal.write("Result of function is \n")
            self.out_terminal.write(str(out))
        self.signal_end.emit()
        
        

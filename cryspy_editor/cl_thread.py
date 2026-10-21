
import io
import logging
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
        self.flag_last_progress = False
        self.flag_stop = False

    def check_stop(self):
        # Python code cannot be interrupted from another thread; procedures
        # print their progress, so the next print ends the calculation
        if self.flag_stop:
            self.flag_stop = False
            raise CalculationStopped("Calculation is stopped by the user.")

    def write_progress(self, text: str):
        """A progress line replaces the previous progress line (one line per
        iteration would make the output long), as print(..., end="\r")."""
        self.check_stop()
        if not self.flag_last_progress and self.text_last.strip() != "":
            self.l_text_permanent.append(self.text_last.strip())
        self.text_last = text
        self.flag_last_progress = True
        self.signal_refresh.emit()
        return self.out_terminal.write(text + "\n")

    def write(self,*arg):
        self.check_stop()
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
                self.flag_last_progress = False
            else:
                self.text_last = text
                self.flag_last_progress = False
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

class OutputLoggingHandler(logging.Handler):
    """Write CrysPy log messages into the output window.

    CrysPy reports progress with the logging module instead of print. The
    messages go to the same COutputLogget as printed text, so the Stop
    button still ends the calculation at the next message.
    """

    def __init__(self, out_terminal: COutputLogget):
        super().__init__(level=logging.INFO)
        self.out_terminal = out_terminal

    def emit(self, record):
        # no try/except here: CalculationStopped raised by write() must
        # reach the procedure that logged the message.
        # CrysPy marks a line of each iteration with progress=True
        # (cryspy.is_progress_record): it replaces the previous such line.
        if getattr(record, "progress", False):
            self.out_terminal.write_progress(self.format(record))
        else:
            self.out_terminal.write(self.format(record) + "\n")


def accepts_callback(func) -> bool:
    """Return True if func takes the keyword-only argument 'callback'.

    CrysPy refinement procedures (cryspy >= 0.15) accept callback(info) and
    stop cleanly, keeping the last refined parameters, when it returns False.
    """
    code = getattr(func, "__code__", None)
    if code is None:
        return False
    names_kwonly = code.co_varnames[
        code.co_argcount:code.co_argcount + code.co_kwonlyargcount]
    return "callback" in names_kwonly


class CThread(QtCore.QThread):
    """CThread class."""
    signal_start = QtCore.pyqtSignal()
    signal_end = QtCore.pyqtSignal()
    signal_refresh = QtCore.pyqtSignal()
    signal_take_attributes = QtCore.pyqtSignal()
    signal_progress = QtCore.pyqtSignal(str)

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
        # called in the main thread just before the calculation starts,
        # e.g. to apply the text typed in the RCIF tab to the object
        self.functions_before_start = []
        self.function_end_calculations = None

    def request_stop(self):
        """Stop the running calculation.

        A procedure with a callback stops after the current iteration and
        keeps its result; any other procedure is interrupted at its next
        printed or logged message.
        """
        if not self.isRunning():
            return
        if getattr(self, "flag_use_callback", False):
            self.flag_stop_by_callback = True
            return
        out_terminal = getattr(self, "out_terminal", None)
        if out_terminal is not None:
            out_terminal.flag_stop = True

    def refinement_callback(self, info: dict):
        """Report refinement progress; return False when Stop was pressed."""
        try:
            text = (f"Iteration {info['iteration']:}: "
                    f"chi_sq/n = {info['chi_sq_per_n']:.4g}")
        except (KeyError, TypeError, ValueError):
            text = ""
        if text:
            self.signal_progress.emit(text)
        if self.flag_stop_by_callback:
            return False
        return None

    def start(self, *args, **kwargs):
        for func in self.functions_before_start:
            func()
        super().start(*args, **kwargs)

    def run(self):
        """Run."""
        func = self.function
        arg = self.arguments
        n_row_need = func.__code__.co_argcount
        l_var_name = func.__code__.co_varnames[:n_row_need]
        
        self.out_terminal = COutputLogget()
        self.flag_stopped = False
        self.flag_use_callback = accepts_callback(func)
        self.flag_stop_by_callback = False
        kwargs = {}
        if self.flag_use_callback:
            kwargs["callback"] = self.refinement_callback
        logger_cryspy = logging.getLogger("cryspy")
        handler = OutputLoggingHandler(self.out_terminal)
        level_old = logger_cryspy.level
        logger_cryspy.addHandler(handler)
        if logger_cryspy.getEffectiveLevel() > logging.INFO:
            logger_cryspy.setLevel(logging.INFO)
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
                out = func(*arg, **kwargs)
            if (self.flag_stop_by_callback and isinstance(out, dict)
                    and out.get("stopped", False)):
                self.flag_stopped = True
                self.out_terminal.write(
                    "Refinement is stopped by the user. The parameters of "
                    "the last completed iteration are kept.\n")
        except CalculationStopped as e:
            self.flag_stopped = True
            out = str(e)
        except Exception:
            flag_out = True
            out = "ERROR DURING PROGRAM EXECUTION\n\n" + \
                str(traceback.format_exc())
        finally:
            os.chdir(cwd)
            logger_cryspy.removeHandler(handler)
            logger_cryspy.setLevel(level_old)
        self.out_terminal.write(45*"*"+"\n")
        self.out_terminal.write("Calculations are completed.\n")
        self.out_terminal.write(45*"*"+"\n")
        if ((out is not None) and flag_out):
            self.out_terminal.write("Result of function is \n")
            self.out_terminal.write(str(out))
        self.signal_end.emit()
        
        

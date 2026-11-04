"""Unexpected errors are shown in a window, the editor is never closed.

PyQt5 aborts the whole program (qFatal) on an exception raised in a slot
while sys.excepthook is the default one. Here every exception that nothing
caught, in a slot, in a QThread or in a Python thread, from CrysPy or any
other library, goes to one handler instead: the traceback is printed to
stderr and written in the output window, and a window tells the user that
the editor keeps running and that File > History gives back the states
before the last changes.
"""
import sys
import threading
import traceback

from PyQt5 import QtCore, QtWidgets

MESSAGE = (
    "An unexpected error happened, the editor keeps running.\n\n"
    "{error}\n\n"
    "Your work is not lost: File > History goes back to the states before "
    "the last changes, and File > Save as keeps the current one in a file.")


class ErrorReporter(QtCore.QObject):
    """Shows errors in the GUI thread, whatever thread they come from."""

    signal_error = QtCore.pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.main_window = None
        self.message_box = None
        self.l_error = []  # every error caught, for the tests
        self.signal_error.connect(self.show_error, QtCore.Qt.QueuedConnection)

    def report(self, exc_type, exc_value, exc_traceback):
        """Called by the hooks, in any thread."""
        if issubclass(exc_type, SystemExit):
            return
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        s_traceback = "".join(traceback.format_exception(
            exc_type, exc_value, exc_traceback))
        try:
            sys.stderr.write(s_traceback)
        except Exception:  # no console in the standalone builds
            pass
        self.l_error.append(s_traceback)
        s_error = f"{exc_type.__name__}: {exc_value}"
        self.signal_error.emit(s_error, s_traceback)

    def show_error(self, s_error: str, s_traceback: str):
        """GUI thread: output window and one message window."""
        main_window = self.main_window
        try:
            if main_window is not None:
                main_window.text_edit.append(
                    f"ERROR (unexpected): {s_error}\n{s_traceback}")
        except Exception:  # the window is already closed
            pass
        if self.message_box is not None and self.message_box.isVisible():
            # several errors in a row: one window, the newest text
            self.message_box.setText(MESSAGE.format(error=s_error))
            self.message_box.setDetailedText(s_traceback)
            return
        parent = main_window if isinstance(
            main_window, QtWidgets.QWidget) else None
        box = QtWidgets.QMessageBox(parent)
        box.setIcon(QtWidgets.QMessageBox.Critical)
        box.setWindowTitle("CrysPy Editor: unexpected error")
        box.setText(MESSAGE.format(error=s_error))
        box.setDetailedText(s_traceback)
        box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        box.open()  # not exec_: no nested event loop inside the handler
        self.message_box = box


REPORTER = None


def install(main_window=None) -> ErrorReporter:
    """Install the handler (once) for the main thread and every other one."""
    global REPORTER
    if REPORTER is None:
        REPORTER = ErrorReporter()
        sys.excepthook = REPORTER.report
        threading.excepthook = lambda args: REPORTER.report(
            args.exc_type, args.exc_value, args.exc_traceback)
    if main_window is not None:
        REPORTER.main_window = main_window
    return REPORTER

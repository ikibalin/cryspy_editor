"""Unexpected errors are shown in a window, the editor is never closed.

PyQt5 aborts the whole program (qFatal) on an exception raised in a slot
while sys.excepthook is the default one. Here every exception that nothing
caught, in a slot, in a QThread or in a Python thread, from CrysPy or any
other library, goes to one handler instead: the traceback is printed to
stderr and written in the output window, and a window tells the user that
the editor keeps running and that File > History gives back the states
before the last changes.

Errors below Python (a segmentation fault in a compiled library, an abort
of Qt) cannot be caught: the process is gone. For them faulthandler writes
the Python stack of every thread to crash.log in the settings folder, and
the next start of the editor shows it (enable_crash_log,
show_previous_crash). The calculation threads get a large stack
(prepare_thread): a QThread on macOS has 512 KB only, which numpy, scipy or
deep recursions in CrysPy overflow, while the same code works on Linux
(8 MB).
"""
import faulthandler
import os
import sys
import threading
import traceback

from PyQt5 import QtCore, QtWidgets

MESSAGE = (
    "An unexpected error happened, the editor keeps running.\n\n"
    "{error}\n\n"
    "Your work is not lost: File > History goes back to the states before "
    "the last changes, and File > Save as keeps the current one in a file.")


# stack of the calculation threads (QThread, threading.Thread)
THREAD_STACK_SIZE = 64 * 1024 * 1024

F_CRASH_LOG = "crash.log"
F_CRASH_PREVIOUS = "crash_previous.log"

MESSAGE_CRASH = (
    "The previous session of CrysPy Editor was closed by a fatal error.\n\n"
    "{error}\n\n"
    "The details show the Python stack at the moment of the crash; it is kept "
    "in {file}. Please send it with a description of what you did to the "
    "developers.")


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
FID_CRASH_LOG = None


def prepare_thread(thread=None):
    """A large stack for a QThread (before its start), and for every
    Python thread started later when thread is None."""
    if thread is None:
        try:
            threading.stack_size(THREAD_STACK_SIZE)
        except (ValueError, RuntimeError):  # not supported by the system
            pass
        return
    try:
        thread.setStackSize(THREAD_STACK_SIZE)
    except Exception:  # noqa: BLE001 - the default stack still works mostly
        pass


def enable_crash_log(dir_log: str) -> str:
    """Write the stack of every thread to crash.log in dir_log when the
    process dies (faulthandler); return the text of the crash of the
    previous session, '' when it ended normally."""
    global FID_CRASH_LOG
    f_log = os.path.join(dir_log, F_CRASH_LOG)
    text_previous = ""
    try:
        os.makedirs(dir_log, exist_ok=True)
        if os.path.isfile(f_log):
            with open(f_log, "r", encoding="utf-8", errors="replace") as fid:
                text_previous = fid.read().strip()
            if text_previous:
                os.replace(f_log, os.path.join(dir_log, F_CRASH_PREVIOUS))
        if FID_CRASH_LOG is not None:
            faulthandler.disable()
            FID_CRASH_LOG.close()
        FID_CRASH_LOG = open(f_log, "w", encoding="utf-8")
        faulthandler.enable(file=FID_CRASH_LOG, all_threads=True)
    except OSError:  # the folder cannot be written: the console only
        try:
            faulthandler.enable(all_threads=True)
        except (OSError, RuntimeError, ValueError, AttributeError):
            pass  # no console in the standalone builds
    return text_previous


def take_crash_summary(text: str) -> str:
    """'Fatal Python error: Segmentation fault' and the last call of the
    thread that crashed."""
    l_line = [line.strip() for line in text.splitlines() if line.strip()]
    s_error = next((line for line in l_line if line.startswith("Fatal Python error")),
                   l_line[0] if l_line else "")
    l_file = [line for line in l_line if line.startswith("File ")]
    if l_file:  # faulthandler writes the most recent call first
        s_error += "\nLast call: " + l_file[0]
    return s_error


def show_previous_crash(text: str, dir_log: str, parent=None):
    """Window about the crash of the previous session (non-blocking)."""
    if not text:
        return None
    box = QtWidgets.QMessageBox(parent)
    box.setIcon(QtWidgets.QMessageBox.Warning)
    box.setWindowTitle("CrysPy Editor: the previous session crashed")
    box.setText(MESSAGE_CRASH.format(
        error=take_crash_summary(text),
        file=os.path.join(dir_log, F_CRASH_PREVIOUS)))
    box.setDetailedText(text)
    box.setStandardButtons(QtWidgets.QMessageBox.Ok)
    box.open()
    return box


def install(main_window=None) -> ErrorReporter:
    """Install the handler (once) for the main thread and every other one."""
    global REPORTER
    if REPORTER is None:
        REPORTER = ErrorReporter()
        sys.excepthook = REPORTER.report
        threading.excepthook = lambda args: REPORTER.report(
            args.exc_type, args.exc_value, args.exc_traceback)
        prepare_thread()
    if main_window is not None:
        REPORTER.main_window = main_window
    return REPORTER

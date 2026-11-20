"""Whatever a method, a procedure or the assistant does, the editor keeps
running: errors end as text in the output window, crashes below Python
leave their stack in crash.log, shown at the next start."""
import os
import subprocess
import sys
import time

import cryspy
import pytest
from PyQt5 import QtWidgets

from cryspy_editor import error_guard
from cryspy_editor.cl_thread import CThread


def run_on_thread(function, arguments=()) -> CThread:
    thread = CThread()
    l_end = []
    thread.signal_end.connect(lambda: l_end.append(True),
                              type=__import__("PyQt5").QtCore.Qt.DirectConnection)
    thread.function = function
    thread.arguments = arguments
    thread.start()
    assert thread.wait(60000)
    thread.l_end = l_end
    return thread


def test_sys_exit_in_a_method_is_an_error():
    def method():
        """A library that calls sys.exit()."""
        sys.exit(3)

    thread = run_on_thread(method)
    text = thread.out_terminal.getvalue()
    assert "ERROR DURING PROGRAM EXECUTION" in text and "SystemExit" in text
    assert thread.l_end == [True]


def test_result_that_cannot_be_printed():
    class Result:
        def __str__(self):
            raise ValueError("cannot convert float NaN to integer")

    thread = run_on_thread(lambda: Result())
    text = thread.out_terminal.getvalue()
    assert "The result cannot be shown as text" in text
    assert "cannot convert float NaN to integer" in text
    assert thread.l_end == [True]


def test_end_signal_after_an_error_before_the_start():
    """A function without __code__ (a builtin) used to break run() before
    its try: the editor stayed in "Calculations are running"."""
    thread = run_on_thread(len, ([1, 2],))
    assert thread.l_end == [True]
    assert "Result of function is \n2" in thread.out_terminal.getvalue()


def test_threads_get_a_large_stack():
    thread = CThread()
    assert thread.stackSize() == error_guard.THREAD_STACK_SIZE


def deep_recursion(depth: int) -> int:
    return 0 if depth == 0 else 1 + deep_recursion(depth - 1)


def test_deep_recursion_in_a_method():
    """5000 nested Python calls (deepcopy of a big object) need more than
    the 512 KB stack of a QThread on macOS."""
    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(10000)
    try:
        thread = run_on_thread(deep_recursion, (5000,))
    finally:
        sys.setrecursionlimit(limit)
    assert "Result of function is \n5000" in thread.out_terminal.getvalue()


def test_report_magnetic_models_from_the_menu(qapp, editor_window, monkeypatch):
    """The method of the crystal reported by the user: menu Methods →
    window of its parameters → thread → the table in the output."""
    from cryspy_editor import ceditor

    def exec_(dialog):
        for name, value in (("k_1", "0.5"), ("k_2", "0"), ("k_3", "0"),
                            ("magnetic_atoms", "Ho")):
            dialog.d_widget[name].setText(value)
        dialog.accept_if_valid()
        return dialog.result()

    monkeypatch.setattr(ceditor.ProcedureDialog, "exec_", exec_)
    reporter = error_guard.install()
    reporter.l_error.clear()
    crystal = editor_window.rcif_object.items[0]
    assert type(crystal).__name__ == "Crystal"
    editor_window.run_method_of_item((crystal.get_name(),), "report_magnetic_models")
    time_start = time.time()
    while editor_window.cthread.isRunning() and time.time() - time_start < 300:
        qapp.processEvents()
        time.sleep(0.02)
    for _ in range(20):
        qapp.processEvents()
    text = editor_window.text_edit.toPlainText()
    assert "# Magnetic models of k = (0.5, 0, 0)" in text
    assert "ERROR" not in text
    assert reporter.l_error == []


def test_crash_log_of_the_previous_session(tmp_path):
    """A segmentation fault cannot be caught; its stack is in crash.log
    and the next start gets it."""
    code = (
        "import faulthandler, sys\n"
        "from cryspy_editor import error_guard\n"
        f"error_guard.enable_crash_log({str(tmp_path)!r})\n"
        "def calculate_in_cryspy():\n"
        "    faulthandler._sigsegv()\n"
        "calculate_in_cryspy()\n")
    result = subprocess.run([sys.executable, "-c", code], capture_output=True,
                            timeout=120)
    assert result.returncode != 0
    text = error_guard.enable_crash_log(str(tmp_path))
    assert "Fatal Python error" in text and "calculate_in_cryspy" in text
    assert os.path.isfile(tmp_path / error_guard.F_CRASH_PREVIOUS)
    summary = error_guard.take_crash_summary(text)
    assert summary.startswith("Fatal Python error: Segmentation fault")
    assert "Last call: File" in summary
    # this session ended normally: nothing for the next start
    assert error_guard.enable_crash_log(str(tmp_path)) == ""


def test_window_about_the_previous_crash(qapp, tmp_path):
    assert error_guard.show_previous_crash("", str(tmp_path)) is None
    box = error_guard.show_previous_crash(
        "Fatal Python error: Segmentation fault\n\nCurrent thread:\n"
        '  File "x.py", line 5 in calculate\n', str(tmp_path))
    try:
        assert isinstance(box, QtWidgets.QMessageBox)
        assert "Segmentation fault" in box.text()
        assert error_guard.F_CRASH_PREVIOUS in box.text()
    finally:
        box.close()


@pytest.fixture(autouse=True)
def restore_faulthandler():
    yield
    import faulthandler
    faulthandler.disable()
    if error_guard.FID_CRASH_LOG is not None:
        error_guard.FID_CRASH_LOG.close()
        error_guard.FID_CRASH_LOG = None

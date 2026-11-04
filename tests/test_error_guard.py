"""An unexpected error shows a window, the editor is never closed.

Without the handler PyQt5 aborts the program on an exception in a slot
(as after a failed refinement: ValueError in str() of a loop with nan
sigmas, inside end_calculations).
"""
import os
import threading

import cryspy
import pytest
from PyQt5 import QtCore, QtWidgets

from cryspy_editor import error_guard
from cryspy_editor.widgets import w_structure_view

F_CRYSTAL = os.path.join(
    os.path.dirname(cryspy.__file__), "procedure_simulation",
    "crystal_Ho2Ti2O7.rcif")


class FakeWebView(QtWidgets.QWidget):
    """QtWebEngine needs OpenGL, which a headless test machine lacks."""

    def load(self, url):
        self.url = url


@pytest.fixture
def window(qapp, monkeypatch, tmp_path):
    from cryspy_editor.ceditor import CMainWindow
    monkeypatch.setattr(w_structure_view, "QWebEngineView", FakeWebView)
    monkeypatch.chdir(tmp_path)
    f_name = tmp_path / "crystal.rcif"
    with open(F_CRYSTAL, "r") as fid:
        f_name.write_text("global_test\n" + fid.read())
    main_window = CMainWindow()
    main_window.d_setup["data_file_name"] = str(f_name)
    main_window.take_rcif_object_from_d_setup()
    reporter = error_guard.install()
    reporter.l_error.clear()
    yield main_window
    if reporter.message_box is not None:
        reporter.message_box.close()
        reporter.message_box = None
    main_window.close()


def process_events(qapp, n=5):
    for _ in range(n):
        qapp.processEvents()


def test_exception_in_slot_shows_window(qapp, window):
    def slot():
        raise ValueError("cannot convert float NaN to integer")

    QtCore.QTimer.singleShot(0, slot)  # an exception in a slot
    process_events(qapp)

    reporter = error_guard.install()
    assert len(reporter.l_error) == 1
    assert "ValueError: cannot convert float NaN to integer" in \
        reporter.l_error[0]
    assert reporter.message_box.isVisible()
    assert "File > History" in reporter.message_box.text()
    assert "ERROR (unexpected): ValueError" in window.text_edit.toPlainText()
    assert window.isVisible()  # the editor keeps running


def test_exception_in_thread_shows_window(qapp, window):
    def work():
        raise RuntimeError("error in a library thread")

    thread = threading.Thread(target=work)
    thread.start()
    thread.join()
    process_events(qapp)  # the window is shown in the GUI thread

    reporter = error_guard.install()
    assert "RuntimeError: error in a library thread" in reporter.l_error[-1]
    assert reporter.message_box.isVisible()


def test_errors_in_a_row_use_one_window(qapp, window):
    for ind in range(3):
        QtCore.QTimer.singleShot(0, lambda ind=ind: 1 / 0)
    process_events(qapp)

    reporter = error_guard.install()
    assert len(reporter.l_error) == 3
    l_box = [w for w in qapp.topLevelWidgets()
             if isinstance(w, QtWidgets.QMessageBox) and w.isVisible()]
    assert len(l_box) == 1


def test_object_text_error_after_refinement(qapp, window, monkeypatch):
    """str() of a loop raised in renew_w_item_tabs after a failed
    refinement: the error is written, the other tabs are made."""
    crystal = window.rcif_object.items[0]

    def fail(self, *argv, **kwargs):
        raise ValueError("cannot convert float NaN to integer")

    monkeypatch.setattr(type(crystal.atom_site), "to_cif", fail)
    window.renew_w_item_tabs((crystal.get_name(), "atom_site"))

    assert "ERROR: Text of 'atom_site' is not made: ValueError" in \
        window.text_edit.toPlainText()
    assert window.w_item_tabs.count() > 0

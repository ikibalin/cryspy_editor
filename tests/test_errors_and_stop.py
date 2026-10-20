"""Phase 2: errors are shown in the window, long calculations can be stopped."""
import time

import cryspy

from cryspy_editor.cl_thread import CThread


def long_procedure(cryspy_object: cryspy.GlobalN):
    """Prints its progress like RhoChi does."""
    for ind in range(1000):
        print(f"iteration {ind}", end="\r")
        time.sleep(0.01)
    return "finished"


def test_stop_long_calculation(qapp):
    thread = CThread()
    thread.function = long_procedure
    thread.arguments = (cryspy.GlobalN.make_container((), (), "global"), )
    thread.start()
    time_start = time.time()
    while getattr(thread, "out_terminal", None) is None:
        time.sleep(0.01)
    time.sleep(0.1)
    thread.request_stop()
    assert thread.wait(5000)
    assert thread.flag_stopped
    assert time.time() - time_start < 5
    assert "stopped by the user" in thread.out_terminal.getvalue()


def test_error_is_shown_in_window(qapp, tmp_path):
    from cryspy_editor.ceditor import CMainWindow
    f_script = tmp_path / "broken_script_for_test.py"
    f_script.write_text("raise ValueError('broken user script')\n")
    from cryspy_editor import settings
    settings.take_settings()["file_names_for_external_functions"] = str(f_script)
    window = CMainWindow()
    try:
        text = window.text_edit.toPlainText()
        assert "broken user script" in text
        window.show_error("Plots are not made", RuntimeError("bad data"))
        assert "RuntimeError: bad data" in window.text_edit.toPlainText()
        assert not window.button_stop.isVisible()
    finally:
        window.close()

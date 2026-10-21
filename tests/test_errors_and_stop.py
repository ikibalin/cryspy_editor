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


def refinement_with_callback(cryspy_object: cryspy.GlobalN, *, callback=None):
    """Behaves like cryspy.rhochi_rietveld_refinement with a callback."""
    for ind in range(1000):
        time.sleep(0.01)
        info = {"iteration": ind + 1, "chi_sq": 10.0, "n_point": 5,
                "chi_sq_per_n": 2.0, "parameter_names": [],
                "parameter_values": []}
        if callback is not None and callback(info) is False:
            return {"stopped": True, "iteration": ind + 1}
    return {"stopped": False}


def wait_for_start(thread):
    while getattr(thread, "out_terminal", None) is None:
        time.sleep(0.01)
    time.sleep(0.1)


def test_accepts_callback():
    from cryspy_editor.cl_thread import accepts_callback
    assert accepts_callback(refinement_with_callback)
    assert not accepts_callback(long_procedure)
    assert not accepts_callback(print)


def test_callback_signature_keeps_autorun():
    """The keyword-only callback must not turn into an argument widget."""
    from cryspy_editor.widgets.cryspy_objects import check_function_to_auto_run
    assert check_function_to_auto_run(refinement_with_callback)


def test_stop_refinement_by_callback(qapp):
    """Stop ends the refinement through the callback, the result is kept."""
    thread = CThread()
    thread.function = refinement_with_callback
    thread.arguments = (cryspy.GlobalN.make_container((), (), "global"), )
    l_progress = []
    thread.signal_progress.connect(l_progress.append)
    thread.start()
    wait_for_start(thread)
    thread.request_stop()
    assert thread.wait(5000)
    assert thread.flag_stopped
    text = thread.out_terminal.getvalue()
    assert "'stopped': True" in text
    assert "parameters of the last completed iteration are kept" in text
    assert "ERROR" not in text


def logging_procedure(cryspy_object: cryspy.GlobalN):
    """Reports progress with logging, like CrysPy >= 0.15."""
    import logging
    logger = logging.getLogger("cryspy.procedure_rhochi.test")
    logger.info("first message from logging")
    for ind in range(1000):
        logger.info(f"iteration {ind}")
        time.sleep(0.01)
    return "finished"


def test_logging_is_shown_and_stoppable(qapp):
    import logging
    level_old = logging.getLogger("cryspy").level
    thread = CThread()
    thread.function = logging_procedure
    thread.arguments = (cryspy.GlobalN.make_container((), (), "global"), )
    thread.start()
    wait_for_start(thread)
    thread.request_stop()
    assert thread.wait(5000)
    assert thread.flag_stopped
    text = thread.out_terminal.getvalue()
    assert "first message from logging" in text
    assert "stopped by the user" in text
    logger_cryspy = logging.getLogger("cryspy")
    assert logger_cryspy.level == level_old
    assert not any(type(h).__name__ == "OutputLoggingHandler"
                   for h in logger_cryspy.handlers)

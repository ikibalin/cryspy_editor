"""Buttons in the chat with the assistant: answers of questions, proposed
requests, Undo of the last change; progress of long actions."""
import cryspy
import pytest
from PyQt5 import QtCore

from cryspy_editor.widgets import assistant_tools
from cryspy_editor.widgets.assistant_dialog import Dialog, Question
from cryspy_editor.widgets.assistant_tools import take_options
from cryspy_editor.widgets.ui_assistant import AssistantWindow, form_progress_text, take_link


def test_options_of_questions_of_cryspy():
    assert take_options({"options": ["scale", "cell"]}) == ("scale", "cell")
    assert take_options({"enum": ["gauss", "lorentz"]}) == ("gauss", "lorentz")
    assert take_options({"enum": [str(number) for number in range(9)]}) == ()  # too many: typed
    assert take_options({"type": "boolean"}) == ("yes", "no")
    assert take_options({"type": "string", "options": list("abcdefg")}) == tuple("abcde")


def test_buttons_of_the_current_question():
    l_question = [
        Question("a", "the cell parameter a", float, proposal=5.0, describe=str),
        Question("model", "Which extinction model?", str, options=("gauss", "lorentz"))]
    dialog = Dialog("tool", l_question, lambda values: "done")
    assert dialog.current_options() == [("Yes: 5.0", "yes"), ("Cancel", "cancel")]
    assert dialog.answer("yes")[0]
    assert dialog.current_options() == [("gauss", "gauss"), ("lorentz", "lorentz"), ("Cancel", "cancel")]
    assert dialog.answer("lorentz")[0] and dialog.values["model"] == "lorentz"
    assert dialog.current_options() == []


def test_only_buttons_of_the_last_reply_work():
    assert take_link("act:3:1", 3, 2) == 1
    assert take_link("act:2:1", 3, 2) is None  # an old reply
    assert take_link("act:3:2", 3, 2) is None
    assert take_link("https://example.org", 3, 2) is None


def test_progress_text():
    assert form_progress_text({"iteration": 4, "chi_sq_per_n": 1.23456}) == \
        "Iteration 4, chi²/n = 1.235 ... (Stop ends it)"


def test_requests_without_suggestions_in_cryspy(monkeypatch):
    monkeypatch.delattr(cryspy, "suggest_assistant_requests", raising=False)
    assert ("What can you do?", "What can you do?") in assistant_tools.suggest_requests(None)


def test_progress_is_given_to_cryspy_when_it_takes_it(monkeypatch):
    calls = []

    def call_assistant_tool(cryspy_object, name, arguments, ask_required=False, progress=None):
        calls.append(progress)
        return {"text": "done", "flag_object_changed": False, "missing": []}

    monkeypatch.setattr(assistant_tools, "call_assistant_tool", call_assistant_tool)
    monkeypatch.setattr(assistant_tools, "FLAG_PROGRESS", True)
    assistant_tools.set_progress(print)
    try:
        assert assistant_tools.run_tool("refine", None, {}) == ("done", False)
    finally:
        assistant_tools.set_progress(None)
    assistant_tools.run_tool("refine", None, {})
    assert calls == [print, None]


@pytest.fixture
def window(qapp):
    l_undo = []
    window = AssistantWindow(undo=lambda: l_undo.append(1) or True,
                             peek_cryspy_object=lambda: None)
    window.l_undo = l_undo
    yield window
    window.close()


def click(window, number: int):
    window.history_view.anchorClicked.emit(QtCore.QUrl(f"act:{window.link_token}:{number}"))


def test_click_on_a_proposed_request_sends_it(window, monkeypatch):
    l_sent = []
    monkeypatch.setattr(window, "on_send", lambda: l_sent.append(window.input_line.text()))
    window.show_requests()
    label, request = window.l_link[0][1:]
    text_before = window.history_view.toPlainText()
    click(window, 0)
    assert l_sent == [request]
    assert window.history_view.toPlainText() == text_before  # the link is not opened as a page
    click(window, 0)  # one click per reply
    assert l_sent == [request]


def test_undo_button_after_a_change(window):
    window.on_reply({"text": "Refinement finished.", "flag_object_changed": True, "question": False})
    assert [link[0] for link in window.l_link] == ["undo"]
    click(window, 0)
    assert window.l_undo == [1]
    assert "before the last change" in window.history_view.toPlainText()


def test_main_window_undoes_the_last_request(qapp):
    from cryspy_editor.ceditor import CMainWindow
    main_window = CMainWindow()
    try:
        main_window.rcif_object = cryspy.str_to_globaln(
            "global_\ndata_fe\n_cell_length_a 5.0\n_cell_length_b 5.0\n_cell_length_c 5.0\n"
            "_cell_angle_alpha 90\n_cell_angle_beta 90\n_cell_angle_gamma 90\n"
            "_space_group_name_H-M_alt 'P m -3 m'\n"
            "loop_\n_atom_site_label\n_atom_site_type_symbol\n_atom_site_fract_x\n"
            "_atom_site_fract_y\n_atom_site_fract_z\nFe Fe3+ 0 0 0\n")
        assert not main_window.undo_assistant_change()  # no request yet
        crystal = main_window.take_rcif_object().crystal_fe
        crystal.cell.length_a = 6.0  # the change made by the assistant
        assert main_window.undo_assistant_change()
        assert main_window.rcif_object.crystal_fe.cell.length_a == pytest.approx(5.0)
        assert not main_window.undo_assistant_change()  # nothing more to undo
    finally:
        main_window.close()

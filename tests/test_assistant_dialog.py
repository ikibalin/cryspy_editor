"""Tests of the questions of the AI assistant to the user (assistant_dialog.py
and the dialog in Assistant.ask), without llama-cpp-python."""
import json

import pytest

from cryspy_editor.widgets import assistant_tools
from cryspy_editor.widgets.assistant import Assistant
from cryspy_editor.widgets.assistant_dialog import (
    Dialog,
    Question,
    is_cancel,
    is_no,
    is_yes,
)


class FakeModel:
    """Returns prepared replies; counts the calls."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.n_call = 0

    def chat(self, messages, flag_json=False):
        self.n_call += 1
        return self.replies.pop(0)


def read_cell(text: str) -> tuple:
    l_value = [float(word) for word in text.replace(",", " ").split()]
    if len(l_value) != 6:
        raise ValueError("six numbers are expected")
    return tuple(l_value)


def read_space_group(text: str) -> str:
    d_group = {"63": "63 C m c m", "62": "62 P n m a"}
    word = text.split()[0]
    if word not in d_group:
        raise ValueError(f"unknown space group '{word}'")
    return d_group[word]


def read_geometry(text: str) -> str:
    text = text.lower()
    if "normal" in text:
        return "normal beam"
    if "four" in text or "euler" in text:
        return "four circle"
    raise ValueError("normal beam or four circle")


def describe_cell(cell) -> str:
    return " ".join(f"{value:g}" for value in cell)


def make_dialog(proposal=None, finish=None, values=None) -> Dialog:
    questions = [
        Question("cell", "the unit cell parameters", read_cell, proposal=proposal,
                 hint="a b c alpha beta gamma", describe=describe_cell),
        Question("space_group", "the space group", read_space_group, hint="number"),
        Question("geometry", "the geometry of measurements", read_geometry,
                 hint="normal beam or four circle"),
    ]
    if finish is None:
        def finish(values):
            return f"{len(values)} values: {values['space_group']}, {values['geometry']}"
    return Dialog("plan_measurement", questions, finish, intro="Plan of the measurement.", values=values)


@pytest.mark.parametrize("text", ["yes", "Yes, right", "да", "oui", "Ja", "ok."])
def test_is_yes(text):
    assert is_yes(text) and not is_no(text) and not is_cancel(text)


@pytest.mark.parametrize("text", ["no", "No, it is 5 6 4", "нет", "non", "nein"])
def test_is_no(text):
    assert is_no(text) and not is_yes(text)


@pytest.mark.parametrize("text", ["cancel", "Stop it", "отмена", "annuler", "abbrechen"])
def test_is_cancel(text):
    assert is_cancel(text)


def test_first_word_only():
    assert not is_yes("is it yes?") and not is_no("") and not is_cancel("do not stop")


def test_questions_one_by_one():
    dialog = make_dialog()
    assert dialog.n_left() == 3 and not dialog.is_done()
    assert dialog.start() == (
        "Plan of the measurement.\nI understood, but some information is missing. I have 3 questions; "
        "reply to them one by one ('cancel' to stop).\n"
        "Q1: What is the unit cell parameters (a b c alpha beta gamma)?")
    assert dialog.answer("5 6 4 90 90 90") == (
        True, "Thank you: the the unit cell parameters is 5 6 4 90 90 90.")
    assert dialog.prompt() == "Q2: What is the space group (number)?"
    flag, message = dialog.answer("600")
    assert not flag and message == "Not understood: unknown space group '600'"
    assert dialog.prompt().startswith("Q2:")
    assert dialog.answer("63")[0]
    assert dialog.prompt() == "Q3: What is the geometry of measurements (normal beam or four circle)?"
    flag, message = dialog.answer("Normal beam geometry")
    assert flag and message.endswith("\nNow I have all the information to perform the calculations.")
    assert dialog.is_done() and dialog.n_left() == 0 and dialog.prompt() == ""
    assert dialog.finish() == "3 values: 63 C m c m, normal beam"
    assert dialog.answer("more") == (False, "No question is asked.")


def test_proposal_is_confirmed():
    dialog = make_dialog(proposal=(5, 6, 4, 90, 90, 90))
    assert dialog.prompt() == ("Q1: Am I right that the unit cell parameters is 5 6 4 90 90 90? "
                               "Answer yes or give the correct value (a b c alpha beta gamma).")
    assert dialog.answer("yes") == (True, "Ok: the unit cell parameters is 5 6 4 90 90 90.")
    assert dialog.values["cell"] == (5, 6, 4, 90, 90, 90)


def test_proposal_is_corrected():
    dialog = make_dialog(proposal=(5, 6, 4, 90, 90, 90))
    dialog.questions[0].s_proposal = "a=5, b=6, c=4"
    assert "is a=5, b=6, c=4?" in dialog.prompt()
    assert dialog.answer("5 6 5 90 90 90")[0]
    assert dialog.values["cell"] == (5, 6, 5, 90, 90, 90)


def test_proposal_is_refused():
    dialog = make_dialog(proposal=(5, 6, 4, 90, 90, 90))
    assert dialog.answer("no") == (False, "Then give the correct value.")
    assert dialog.prompt() == "Q1: What is the unit cell parameters (a b c alpha beta gamma)?"
    assert dialog.answer("no")[1].startswith("Not understood:")


def test_skip_and_known_values():
    dialog = make_dialog(values={"cell": (5, 6, 4, 90, 90, 90)})
    dialog.questions[2].skip = lambda values: values["space_group"].startswith("62")
    assert dialog.n_left() == 2
    assert "I have 2 questions" in dialog.start() and "Q1: What is the space group" in dialog.start()
    flag, message = dialog.answer("62")
    assert flag and "Now I have all the information" in message and dialog.is_done()


def test_skip_with_missing_value_is_asked():
    question = Question("geometry", "the geometry", read_geometry,
                        skip=lambda values: values["space_group"] == "62")
    assert not question.is_skipped({})  # KeyError: not skipped
    assert not Question("x", "x", float, skip=lambda values: values + 1).is_skipped({})  # TypeError


# the dialog in Assistant.ask: a test-only tool that returns a Dialog

@pytest.fixture
def dialog_tool(monkeypatch):
    """call_assistant_tool of CrysPy replaced: "plan_measurement" returns a
    Dialog, other names a text."""
    l_finished = []

    def finish(values):
        l_finished.append(values)
        return f"Plan for {values['space_group']} in {values['geometry']} geometry."

    def fake_call(cryspy_object, name, arguments):
        if name == "plan_measurement":
            return {"text": make_dialog(finish=finish), "flag_object_changed": True, "flag_error": False}
        if name == "plan_known":
            return {"text": make_dialog(finish=finish, values={
                "cell": (5, 6, 4, 90, 90, 90), "space_group": "63 C m c m", "geometry": "normal beam"}),
                "flag_object_changed": False, "flag_error": False}
        return {"text": f"done {name}", "flag_object_changed": False, "flag_error": False}

    monkeypatch.setattr(assistant_tools, "call_assistant_tool", fake_call)
    return l_finished


def reply(*names, answer=""):
    return json.dumps({"actions": [{"action": name, "arguments": {}} for name in names], "answer": answer})


def test_assistant_asks_and_finishes(dialog_tool):
    model = FakeModel([reply("plan_measurement", "other", answer="The plan is made.")])
    assistant = Assistant(model)
    l_running = []
    result = assistant.ask("Provide the list of hkl reflections and optimize the time", on_action=l_running.append)
    assert result["question"] is True and assistant.is_asking()
    assert result["text"].startswith("[plan_measurement] Plan of the measurement.\nI understood")
    assert result["text"].endswith("Q1: What is the unit cell parameters (a b c alpha beta gamma)?")
    assert "The plan is made" not in result["text"]  # the answer of the model is dropped
    assert l_running == ["plan_measurement"]  # the actions after the dialog are not run
    assert not result["flag_object_changed"]

    result = assistant.ask("5 6 4 90 90 90")
    assert result["question"] and result["text"] == (
        "Thank you: the the unit cell parameters is 5 6 4 90 90 90.\nQ2: What is the space group (number)?")
    result = assistant.ask("six hundred")
    assert result["question"] and result["text"].startswith("Not understood:")
    assert result["text"].endswith("Q2: What is the space group (number)?")
    assistant.ask("63")
    result = assistant.ask("Normal beam geometry", on_action=l_running.append)
    assert result["question"] is False and not assistant.is_asking()
    assert result["text"].endswith(
        "Now I have all the information to perform the calculations.\n\n"
        "[plan_measurement] Plan for 63 C m c m in normal beam geometry.")
    assert result["flag_object_changed"] is True
    assert result["actions"][0][0] == "plan_measurement"
    assert l_running[-1] == "plan_measurement"
    assert dialog_tool[0]["cell"] == (5, 6, 4, 90, 90, 90)
    assert model.n_call == 1  # the answers are read without the model
    assert len(assistant.history) == 10


def test_assistant_dialog_is_cancelled(dialog_tool):
    model = FakeModel([reply("plan_measurement"), reply(answer="Hello")])
    assistant = Assistant(model)
    assistant.ask("plan the measurement")
    result = assistant.ask("отмена")
    assert result == {"text": "Stopped: plan_measurement is not done.", "actions": [],
                      "flag_object_changed": False, "question": False}
    assert not dialog_tool
    assert assistant.ask("Hi")["text"] == "Hello"  # the model answers again


def test_clear_history_stops_the_dialog(dialog_tool):
    assistant = Assistant(FakeModel([reply("plan_measurement")]))
    assistant.ask("plan the measurement")
    assistant.clear_history()
    assert not assistant.is_asking() and assistant.history == []


def test_dialog_without_questions_is_finished_at_once(dialog_tool):
    assistant = Assistant(FakeModel([reply("plan_known")]))
    result = assistant.ask("plan the measurement")
    assert result["question"] is False
    assert result["text"] == "[plan_known] Plan for 63 C m c m in normal beam geometry."


def test_error_of_finish(monkeypatch):
    def finish(values):
        raise ValueError("no wavelength")
    dialog = Dialog("plan", [Question("x", "x", float)], finish)
    monkeypatch.setattr(assistant_tools, "call_assistant_tool",
                        lambda obj, name, arguments: {"text": dialog, "flag_object_changed": True})
    assistant = Assistant(FakeModel([reply("plan")]))
    assistant.ask("plan")
    result = assistant.ask("1.5")
    assert result["text"].endswith("[plan] Error: no wavelength")
    assert result["flag_object_changed"] is False


def test_request_is_given_to_the_tool(monkeypatch):
    class Tool:
        flag_request = True
        flag_object_changed = False
    monkeypatch.setitem(assistant_tools.D_TOOLS, "find_values", Tool())
    l_arguments = []

    def fake_call(obj, name, arguments):
        l_arguments.append(arguments)
        return {"text": "ok", "flag_object_changed": False}
    monkeypatch.setattr(assistant_tools, "call_assistant_tool", fake_call)
    Assistant(FakeModel([reply("find_values", "other"), reply(answer="ok")])).ask("cell 5 6 4 90 90 90")
    assert l_arguments == [{"request": "cell 5 6 4 90 90 90"}, {}]


def test_placeholder_while_asking(qapp, dialog_tool):
    from cryspy_editor.widgets import ui_assistant
    window = ui_assistant.AssistantWindow()
    try:
        window.assistant = Assistant(FakeModel([reply("plan_measurement")]))
        window.on_reply(window.assistant.ask("plan the measurement"))
        assert window.input_line.placeholderText() == "Answer the question ('cancel' to stop)"
        window.on_error("RuntimeError: x")
        assert window.input_line.placeholderText() == ui_assistant.PLACEHOLDER_ANSWER
        window.on_reply(window.assistant.ask("cancel"))
        assert window.input_line.placeholderText() == "Ask the question or request an action"
    finally:
        window.close()

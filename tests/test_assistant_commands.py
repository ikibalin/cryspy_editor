"""Tests of the '@name' commands and of the answer to "what can you do?"
without llama-cpp-python."""
import cryspy
import pytest

from cryspy_editor.widgets import assistant_commands, assistant_tools
from cryspy_editor.widgets.assistant import Assistant
from cryspy_editor.widgets.assistant_commands import (
    form_capabilities_text, form_completions, is_capability_question, parse_command,
    parse_command_arguments, take_recipe_names)
from cryspy_editor.widgets.assistant_tools import D_TOOLS

from test_assistant import RCIF, make_assistant
from test_assistant_agent import final, step

flag_recipes = "get_recipe" in D_TOOLS and len(take_recipe_names()) > 0


def test_parse_command():
    assert parse_command("@refine_structure") == ("refine_structure", "")
    assert parse_command("  @refine_parameters scale ") == ("refine_parameters", "scale")
    assert parse_command("refine @refine_structure") is None
    assert parse_command("@") is None
    assert parse_command("@1abc") is None


def test_parse_command_arguments():
    assert parse_command_arguments("set_parameter", "") == {}
    assert parse_command_arguments("set_parameter", '{"path": "cell.length_a", "value": 5.4}') == \
        {"path": "cell.length_a", "value": 5.4}
    assert parse_command_arguments("set_parameter", "path=cell.length_a value='5.43'") == \
        {"path": "cell.length_a", "value": "5.43"}
    with pytest.raises(ValueError):
        parse_command_arguments("set_parameter", "{not json")
    with pytest.raises(ValueError):
        parse_command_arguments("set_parameter", "[1, 2]")
    with pytest.raises(ValueError):
        parse_command_arguments("set_parameter", "path=cell.length_a 5.43")


def test_only_argument_is_given_without_name():
    l_name = [name for name, tool in D_TOOLS.items()
              if len(list(tool.required) or list(tool.parameters)) == 1]
    assert l_name, "no action with one argument"
    tool = D_TOOLS[l_name[0]]
    key = (list(tool.required) or list(tool.parameters))[0]
    assert parse_command_arguments(l_name[0], "some value") == {key: "some value"}
    l_several = [name for name, tool in D_TOOLS.items()
                 if not tool.required and len(tool.parameters) > 1]
    if l_several:
        with pytest.raises(ValueError, match="key=value"):
            parse_command_arguments(l_several[0], "some value")


@pytest.mark.parametrize("text", ["What can you do?", "what else can you do", "help", "?", "@",
                                  "Что ты умеешь?", "что можешь делать"])
def test_capability_question(text):
    assert is_capability_question(text)


@pytest.mark.parametrize("text", ["refine the scale", "what can you do with the cell?", "@refine"])
def test_not_capability_question(text):
    assert not is_capability_question(text)


def test_completions_have_recipes_then_actions():
    l_completion = form_completions()
    l_name = [name for name, _ in l_completion]
    assert all(name.startswith("@") for name in l_name)
    assert len(l_name) == len(set(l_name))
    assert set(f"@{name}" for name in D_TOOLS) <= set(l_name)
    for name in take_recipe_names():
        assert l_name.index(f"@{name}") < l_name.index(f"@{next(iter(D_TOOLS))}")
        assert dict(l_completion)[f"@{name}"].startswith("recipe: ")
    assert all(len(description) <= assistant_commands.N_MAX_DESCRIPTION for _, description in l_completion)


def test_capabilities_are_answered_without_model():
    assistant = Assistant(None)
    out = assistant.ask("What can you do?")
    assert out["text"] == form_capabilities_text()
    for name in take_recipe_names():
        assert f"@{name}:" in out["text"]
    assert f"@{next(iter(D_TOOLS))}:" in out["text"]
    assert out["actions"] == []


def test_capabilities_are_answered_without_asking_the_model():
    assistant = make_assistant([])  # the model has no reply: it is not called
    assert "Actions:" in assistant.ask("что ты умеешь?")["text"]


def test_request_without_model():
    out = Assistant(None).ask("refine the scale")
    assert "@" in out["text"] and out["actions"] == []


def test_unknown_command():
    out = Assistant(None).ask("@no_such_name")
    assert out["text"].startswith("Error") and "@" in out["text"]


def test_action_is_run_without_model():
    obj = cryspy.str_to_globaln(RCIF)
    l_action = []
    out = Assistant(None).ask("@set_parameter path=cell.length_a value=5.43", obj, on_action=l_action.append)
    assert l_action == ["set_parameter"]
    assert out["actions"][0][:2] == ("set_parameter", {"path": "cell.length_a", "value": "5.43"})
    assert out["text"].startswith("[set_parameter]")
    assert not out["actions"][0][2].startswith("Error"), out["text"]
    assert out["flag_object_changed"]
    assert obj.items[0].cell.length_a == pytest.approx(5.43)


def test_wrong_arguments_of_action():
    out = Assistant(None).ask("@set_parameter {bad")
    assert out["text"].startswith("Error") and out["actions"] == []


@pytest.mark.skipif(not flag_recipes, reason="CrysPy without recipes")
def test_recipe_with_model_starts_the_agent():
    name = take_recipe_names()[0]
    assistant = make_assistant([final("done")])
    l_step = []
    out = assistant.ask(f"@{name}", None, on_step=l_step.append)
    assert out["actions"][0][:2] == ("get_recipe", {"name": name})
    assert any("[get_recipe]" in text for text in l_step)


@pytest.mark.skipif(not flag_recipes, reason="CrysPy without recipes")
def test_recipe_without_model_runs_literally(monkeypatch):
    calls = []

    def fake_run_recipe(obj, name, *, callback=None):
        calls.append(name)
        callback("first", "done", "chi_sq/n 10 -> 2")
        return {"text": "Recipe done.", "steps": [("first", "done", "chi_sq/n 10 -> 2")]}

    monkeypatch.setattr(cryspy, "run_recipe", fake_run_recipe)
    name = take_recipe_names()[0]
    l_step = []
    out = Assistant(None).ask(f"@{name}", object(), on_step=l_step.append)
    assert calls == [name]
    assert l_step == ["Step first: done\n[first] chi_sq/n 10 -> 2"]
    assert "Recipe done." in out["text"] and "No model" in out["text"]


@pytest.mark.skipif(not flag_recipes, reason="CrysPy without recipes")
def test_recipe_without_model_needs_a_file():
    out = Assistant(None).ask(f"@{take_recipe_names()[0]}", None)
    assert out["text"].startswith("Error")


def test_input_line_proposes_names(qapp):
    from cryspy_editor.widgets import ui_assistant
    window = ui_assistant.AssistantWindow()
    try:
        assert window.input_line.isEnabled()
        model = window.completer.model()
        l_text = [model.item(row).data(ui_assistant.QtCore.Qt.UserRole) for row in range(model.rowCount())]
        assert l_text == [name for name, _ in form_completions()]
        window.input_line.setText("@set_p")
        window.on_text_edited("@set_p")
        window.completer.setCompletionPrefix("@set_p")
        assert window.completer.currentCompletion() == "@set_parameter"
    finally:
        window.close()


@pytest.mark.skipif(not assistant_tools.flag_ask_required(), reason="CrysPy without ask_required")
def test_missing_arguments_of_action_are_asked():
    obj = cryspy.str_to_globaln(RCIF)
    assistant = Assistant(None)
    out = assistant.ask("@set_parameter path=cell.length_a", obj)
    assert out["question"] and "Q1: What is the value" in out["text"]
    out = assistant.ask("5.43", obj)
    assert not out["question"]
    assert obj.items[0].cell.length_a == pytest.approx(5.43)


@pytest.mark.skipif(not assistant_tools.flag_ask_required(), reason="CrysPy without ask_required")
def test_cod_without_formula_is_asked():
    out = Assistant(None).ask("@add_crystal_from_cod", cryspy.str_to_globaln(RCIF))
    assert out["question"] and "COD number" in out["text"]
    assert not out["text"].startswith("[add_crystal_from_cod] Error")


def test_model_gets_error_for_missing_arguments():
    obj = cryspy.str_to_globaln(RCIF)
    result, _ = assistant_tools.run_tool("set_parameter", obj, {"path": "cell.length_a"})
    assert isinstance(result, str) and result.startswith("Error")

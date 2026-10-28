"""The assistant writes a recipe of the CookBook from an algorithm in words
and asks the user in the middle of its work (ask_user of CrysPy): the agent
loop waits for the answers and goes on."""
import json

import cryspy
import pytest

from cryspy_editor.widgets.assistant_dialog import Dialog, Question
from cryspy_editor.widgets.assistant_tools import D_TOOLS

from test_assistant import RCIF, make_assistant, reply
from test_assistant_agent import final, step

pytestmark = pytest.mark.skipif("ask_user" not in D_TOOLS, reason="CrysPy without ask_user")

RECIPE = """Recipe scale_then_positions: Scale factor, then atomic positions
Requests: refine the scale and then the positions
For: single_crystal, unpolarized

1. start: Fix all parameters and calculate the start model.
   Actions: fix_parameters; calculate
2. scale: Scale factor.
   Actions: refine_parameters {"pattern": "scale"}; refine
3. positions: Free atomic positions.
   Actions: refine_parameters {"pattern": "atomic positions"}; refine

Final answer: chi_sq/n at the start and at the end.
"""


@pytest.fixture
def recipe_folder(tmp_path):
    from cryspy.procedure_assistant import recipes
    recipes.set_user_recipe_folder(str(tmp_path))
    yield tmp_path
    recipes.set_user_recipe_folder(None)


def test_question_of_the_model_is_asked_as_written():
    dialog = Dialog("ask_user", [Question("answer_1", "Which parameters after the scale?", str,
                                          hint="1: adp; 2: positions")], lambda values: "")
    assert dialog.prompt() == "Q1: Which parameters after the scale? (1: adp; 2: positions)"
    assert dialog.answer("2") == (True, "Thank you: 2.\nNow I have all the information to perform the calculations.")


def test_recipe_is_written_with_questions_in_the_middle(recipe_folder):
    obj = cryspy.str_to_globaln(RCIF)
    assistant = make_assistant([
        reply(("get_recipe_guide", {})),
        step("ask_user", {"question": "What after the scale", "options": ["adp", "atomic positions"]},
             thought="The second step is not clear."),
        step("check_recipe_text", {"text": RECIPE}, thought="The user chose the positions."),
        step("ask_user", {"question": "Save the recipe scale_then_positions"}),
        step("save_recipe", {"text": RECIPE}),
        final("The recipe scale_then_positions is saved."),
    ])
    l_shown = []
    result = assistant.ask("write a recipe: fix all, refine the scale, then something", obj,
                           on_step=l_shown.append)
    assert result["question"] is True
    assert "Q1: What after the scale? (1: adp; 2: atomic positions; or your own answer)" in result["text"]
    assert assistant.agent is not None
    # the guide reached the model and the loop waits for the answer
    assert "Recipe <name>: <title>" in assistant.model.llm.l_messages[1][-1]["content"]

    result = assistant.ask("2", obj, on_step=l_shown.append)
    assert result["question"] is True  # the second question of the model
    assert "Q1: Save the recipe scale_then_positions?" in result["text"]
    l_messages = assistant.model.llm.l_messages
    assert "-> atomic positions" in l_messages[2][-1]["content"]
    assert "scale_then_positions is correct: 3 steps" in l_messages[3][-1]["content"]

    result = assistant.ask("yes", obj, on_step=l_shown.append)
    assert result["question"] is False
    assert assistant.agent is None
    assert result["text"] == "The recipe scale_then_positions is saved."
    assert (recipe_folder / "scale_then_positions.txt").read_text() == RECIPE
    assert result["flag_object_changed"] is False
    assert any(text.startswith("Thank you: 2.") for text in l_shown)
    assert any(text.startswith("[save_recipe] Recipe scale_then_positions is saved") for text in l_shown)


def test_writing_a_recipe_changes_nothing_in_the_file(recipe_folder):
    obj = cryspy.str_to_globaln(RCIF)
    assistant = make_assistant([reply(("get_recipe_guide", {})), step("refine"), final("no")])
    assistant.ask("write a recipe", obj)
    l_messages = assistant.model.llm.l_messages
    assert "the action 'refine' cannot be used here" in l_messages[2][-1]["content"]
    assert "ask with the action" in l_messages[1][0]["content"]  # the rule of the questions


def test_cancel_stops_the_waiting_loop():
    obj = cryspy.str_to_globaln(RCIF)
    assistant = make_assistant([reply(("work_step_by_step", {})),
                                step("ask_user", {"question": "Which experiment?"})])
    assistant.ask("refine something step by step", obj)
    assert assistant.is_asking()
    result = assistant.ask("cancel", obj)
    assert result["text"] == "Stopped: ask_user is not done."
    assert assistant.agent is None and not assistant.is_asking()


def test_answer_of_a_model_question_without_steps_shown():
    """Without on_step the reply has the thanks and the end of the loop."""
    obj = cryspy.str_to_globaln(RCIF)
    assistant = make_assistant([
        reply(("ask_user", {"questions": ["Which parameters?", "Undo when worse?"]})),
        final("I will refine the cell and undo when worse."),
    ])
    result = assistant.ask("refine something", obj)
    assert "Q1: Which parameters?" in result["text"]
    result = assistant.ask("cell", obj)
    assert result["text"].startswith("Thank you: cell.\nQ2: Undo when worse?")
    result = assistant.ask("yes", obj)
    assert result["text"].startswith("Thank you: yes.")
    assert result["text"].endswith("I will refine the cell and undo when worse.")
    assert "Which parameters? -> cell" in json.dumps(assistant.model.llm.l_messages[-1])


def test_system_prompt_routes_writing_a_recipe():
    from cryspy_editor.widgets.assistant import form_system_prompt
    s_prompt = form_system_prompt(None)
    assert 'give the single action "get_recipe_guide"' in s_prompt

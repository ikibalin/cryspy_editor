"""The request in English for the search of methods, procedures and help
(assistant_language): no language gets a preference."""
import cryspy
import pytest

from cryspy_editor.widgets.assistant_language import (
    add_english_request,
    is_english,
    take_translation,
    translate_to_english,
)
from cryspy_editor.widgets.assistant_tools import add_request_methods


class EchoModel:
    """Returns the prepared reply and keeps the messages."""

    def __init__(self, reply="", flag_error=False):
        self.reply = reply
        self.flag_error = flag_error
        self.l_call = []

    def chat(self, messages, flag_json=False, schema=None, flag_think=None):
        self.l_call.append((messages, flag_think))
        if self.flag_error:
            raise ValueError("the model failed")
        return self.reply


@pytest.mark.parametrize("text", [
    "How to describe thermal vibrations?",
    "Convert the structure to superspace",
    "refine scale",
    "chi2",
    "Set B_iso of Fe to 0.5 Å²",
    "Add the moment 3 μB along c to Tb",
    "What is χ_11 of Ho?",
])
def test_english_requests(text):
    assert is_english(text)


@pytest.mark.parametrize("text", [
    "как описать тепловые колебания?",
    "Comment décrire les vibrations thermiques ?",
    "Wie beschreibe ich die Mosaizität des Kristalls",
    "wie beschreibe ich die Extinktion im Kristall",
    "Describir la estructura magnética",
    "結晶構造を精密化してください",
])
def test_requests_in_other_languages(text):
    assert not is_english(text)


def test_english_request_needs_no_call():
    model = EchoModel("never used")
    assert translate_to_english(model, "Refine the cell") == "Refine the cell"
    assert model.l_call == []


def test_request_rewritten_in_english_by_one_call():
    model = EchoModel("How to describe thermal vibrations?")
    text = translate_to_english(model, "как описать тепловые колебания?")
    assert text == "How to describe thermal vibrations?"
    assert len(model.l_call) == 1
    messages, flag_think = model.l_call[0]
    assert "English" in messages[0]["content"]
    assert messages[1]["content"] == "как описать тепловые колебания?"
    assert flag_think is False  # a thinking model answers at once


def test_failed_translation_keeps_the_request():
    assert translate_to_english(EchoModel(flag_error=True), "уточни масштаб") == "уточни масштаб"
    assert translate_to_english(EchoModel(""), "уточни масштаб") == "уточни масштаб"
    assert translate_to_english(None, "уточни масштаб") == "уточни масштаб"


def test_translation_is_cleaned():
    assert take_translation('Translation: "Refine the scale"', "x") == "Refine the scale"
    assert take_translation("<think>hm</think>\nRefine the scale\n\nNote: ...", "x") == "Refine the scale"


def test_request_for_the_model_keeps_the_words_of_the_user():
    assert add_english_request("Refine", "Refine") == "Refine"
    text = add_english_request("уточни масштаб", "Refine the scale")
    assert text.startswith("уточни масштаб") and "(In English: Refine the scale)" in text


RCIF_CRYSTAL = """
global_

data_MnSi
_cell_length_a 4.0
_cell_length_b 4.0
_cell_length_c 4.0
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
_space_group_name_H-M_alt "P 1"

loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Mn Mn 0 0 0.5
"""


def test_methods_found_by_the_english_request():
    """A request in Russian found no method: the English text finds them."""
    methods = pytest.importorskip("cryspy.procedure_assistant.methods")
    if not hasattr(methods, "form_matching_methods_text"):
        pytest.skip("CrysPy without form_matching_methods_text")
    obj = cryspy.str_to_globaln(RCIF_CRYSTAL)
    question = "Преобразуй структуру в суперпространство"
    assert "convert_to_superspace" not in add_request_methods(question, obj)
    text = add_request_methods(question, obj, "Convert the structure to superspace")
    assert text.startswith(question)
    assert "(In English: Convert the structure to superspace)" in text
    assert "convert_to_superspace" in text

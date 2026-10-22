"""Window of the recipes of the AI assistant and the recipes in the prompt."""
import os

import cryspy
import pytest
from PyQt5 import QtWidgets

from cryspy_editor.widgets import recipe_editor

RCIF_FLIP_RATIO = """global_

data_fe
_cell_length_a 5.0
_cell_length_b 5.0
_cell_length_c 5.0
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
_space_group_name_H-M_alt "P m -3 m"

loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
_atom_site_adp_type
_atom_site_B_iso_or_equiv
  Fe  Fe3+  0.0  0.0  0.0  1.0  Biso  0.3

data_exp
_setup_wavelength 0.84
_setup_field 1.0
_diffrn_radiation_polarization 0.9
_diffrn_radiation_efficiency 1.0
_diffrn_orient_matrix_UB_11 0.2
_diffrn_orient_matrix_UB_12 0.0
_diffrn_orient_matrix_UB_13 0.0
_diffrn_orient_matrix_UB_21 0.0
_diffrn_orient_matrix_UB_22 0.2
_diffrn_orient_matrix_UB_23 0.0
_diffrn_orient_matrix_UB_31 0.0
_diffrn_orient_matrix_UB_32 0.0
_diffrn_orient_matrix_UB_33 0.2
_phase_label fe

loop_
_diffrn_refln_index_h
_diffrn_refln_index_k
_diffrn_refln_index_l
_diffrn_refln_fr
_diffrn_refln_fr_sigma
  1 0 0 1.1 0.01
  1 1 0 1.2 0.01
"""


@pytest.fixture
def dialog(qapp, monkeypatch):
    monkeypatch.setattr(QtWidgets.QMessageBox, "question",
                        lambda *args, **kwargs: QtWidgets.QMessageBox.Yes)
    window = recipe_editor.RecipeEditorDialog()
    yield window
    window.flag_modified = False
    window.close()
    cryspy.set_user_recipe_folder(None)


def take_names(window):
    return [window.list_widget.item(ind).text() for ind in range(window.list_widget.count())]


def test_recipes_of_cryspy_are_listed(dialog):
    l_name = take_names(dialog)
    assert "refine_structure" in l_name
    assert "refine_flip_ratio_nuclear" in l_name
    assert "\nRecipe " in dialog.text_edit.toPlainText()  # the text of the first recipe
    assert not dialog.button_delete.isEnabled()  # a recipe of CrysPy


def test_new_recipe_is_saved_in_the_settings_folder(dialog):
    dialog.new_recipe()
    dialog.text_edit.setPlainText(dialog.text_edit.toPlainText().replace("my_recipe", "scale_only"))
    assert dialog.check_text()
    dialog.save_recipe()
    path = os.path.join(recipe_editor.take_user_recipe_folder(), "scale_only.txt")
    assert os.path.isfile(path)
    assert "scale_only  [yours]" in take_names(dialog)
    assert dialog.current_file()["name"] == "scale_only"
    assert dialog.button_delete.isEnabled()
    from cryspy.procedure_assistant.recipes import take_recipe
    assert take_recipe("scale_only") is not None
    dialog.delete_recipe()
    assert not os.path.isfile(path)
    assert take_recipe("scale_only") is None


def test_wrong_recipe_is_not_saved(dialog):
    dialog.new_recipe()
    dialog.text_edit.setPlainText("Recipe bad: b\n1. s: g\n   Actions: magic\n")
    assert not dialog.check_text()
    dialog.save_recipe()
    assert "unknown tool magic" in dialog.label_status.text()
    assert not os.path.isfile(os.path.join(recipe_editor.take_user_recipe_folder(), "bad.txt"))


def test_saved_recipe_of_cryspy_replaces_it(dialog):
    index = next(ind for ind, d_file in enumerate(dialog.l_file) if d_file["name"] == "refine_structure")
    dialog.list_widget.setCurrentRow(index)
    dialog.save_recipe()
    l_name = take_names(dialog)
    assert "refine_structure  [yours]" in l_name
    assert "refine_structure  [replaced by yours]" in l_name


def test_prompt_has_the_recipes_of_the_experiments():
    from cryspy_editor.widgets.assistant import form_system_prompt
    obj = cryspy.str_to_globaln(RCIF_FLIP_RATIO)
    prompt = form_system_prompt(obj)
    assert "exp (single_crystal, polarized, flip_ratio, nuclear): refine_flip_ratio_nuclear" in prompt
    assert '"name": "choose_recipes"' in prompt

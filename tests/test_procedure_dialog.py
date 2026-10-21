"""Menus and forms of CrysPy procedures made from their descriptions in
CrysPy (type hints and numpydoc docstrings)."""
import cryspy
import pytest
from PyQt5 import QtWidgets

from cryspy_editor.widgets import w_procedure_dialog
from cryspy_editor.widgets.w_procedure_dialog import (
    ProcedureDialog,
    is_autorun,
    take_description,
)

# CrysPy describes its procedures since the release after 0.16.0
pytestmark = pytest.mark.skipif(
    w_procedure_dialog.describe_procedure is None,
    reason="this CrysPy has no cryspy.procedure_assistant.procedures")

RCIF = """global_

data_fe
_cell_length_a 5.0
_cell_length_b 5.0
_cell_length_c 5.0
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
_space_group_name_H-M_alt "P m -3 m"
"""


def scale_cell(cell: cryspy.Cell, factor: float, flag_round: bool = False):
    """Scale the cell.

    Parameters
    ----------
    cell : Cell
        Unit cell to scale.
    factor : float
        Scale factor of the lengths.
    flag_round : bool, optional
        Round the lengths.
    """
    return factor * cell.length_a


def test_description_and_autorun():
    d_procedure = take_description(cryspy.rhochi_no_refinement)
    assert d_procedure["title"] == "RhoChi No Refinement" and is_autorun(d_procedure)
    assert not is_autorun(take_description(scale_cell))
    assert take_description(len) is None


def test_form_of_parameters(qapp):
    obj = cryspy.str_to_globaln(RCIF + RCIF.replace("global_\n", "").replace("data_fe", "data_fe2"))
    dialog = ProcedureDialog(scale_cell, take_description(scale_cell), obj)
    try:
        assert dialog.windowTitle() == "Scale Cell"
        combo = dialog.d_widget["cell"]
        assert [combo.itemText(i) for i in range(combo.count())] == ["fe.cell", "fe2.cell"]
        assert dialog.d_widget["factor"].toolTip() == "Scale factor of the lengths."
        assert isinstance(dialog.d_widget["flag_round"], QtWidgets.QCheckBox)
        dialog.d_widget["factor"].setText("two")
        dialog.accept_if_valid()
        assert dialog.result() != QtWidgets.QDialog.Accepted
        assert dialog.label_error.text() == "factor: 'two' is not a number."
        combo.setCurrentIndex(1)
        dialog.d_widget["factor"].setText("2 times")
        dialog.accept_if_valid()
        assert dialog.result() == QtWidgets.QDialog.Accepted
        cell, factor, flag_round = dialog.arguments()
        assert cell is obj.items[1].cell and factor == 2. and flag_round is False
    finally:
        dialog.close()


def test_defaults_in_the_form(qapp):
    import cryspy.procedure_mempy.mempy as mempy
    function = mempy.mempy_cycle_with_parameters
    obj = cryspy.str_to_globaln(RCIF)
    dialog = ProcedureDialog(function, take_description(function), obj)
    try:
        assert dialog.d_widget["iteration_max"].text() == "1000"
        assert dialog.d_widget["iteration_max"].toolTip() == "Maximal number of iterations."
        dialog.d_widget["iteration_max"].setText("500")
        dialog.accept_if_valid()
        assert dialog.arguments() == (obj, 1e-5, 500, 1e-9, 1e-5, 10)
    finally:
        dialog.close()


def test_menu_from_descriptions(qapp, monkeypatch, tmp_path):
    from cryspy_editor.ceditor import CMainWindow
    monkeypatch.chdir(tmp_path)
    window = CMainWindow()
    try:
        d_menu = {action.text(): action.menu() for action in window.menu_bar.actions()}
        d_action = {action.text(): action for action in d_menu["MEMPy"].actions()}
        assert "Cycle With Parameters" in d_action
        assert d_action["Cycle With Parameters"].toolTip().startswith(
            "Reconstruct the magnetization density by the maximum entropy method")
        assert "Spin Density Reconstruction (autorun)" in d_action
    finally:
        window.close()

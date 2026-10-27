"""Dialog "Add constraint..." of the object tree: marks and the loop of
constraints are made by CrysPy."""
import cryspy
import pytest
from PyQt5 import QtCore

from cryspy_editor.widgets.w_constraint_dialog import (
    COLUMN_MARK,
    COLUMN_USE,
    ConstraintDialog,
    is_constraint_supported,
)

pytestmark = pytest.mark.skipif(
    not is_constraint_supported(), reason="CrysPy without the loop of constraints")

RCIF = """global_

data_feco
_cell_length_a 5.0
_cell_length_b 5.0
_cell_length_c 5.0
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
_atom_site_occupancy
Fe1 Fe3+ 0.1 0.2 0.3 0.7
Co1 Co2+ 0.1 0.2 0.3 0.3
"""


def take_row(dialog, path: str) -> int:
    return [d_par["path"] for d_par in dialog.l_parameter].index(path)


def test_add_constraint(qapp):
    obj = cryspy.str_to_globaln(RCIF)
    dialog = ConstraintDialog(obj)
    try:
        dialog.line_filter.setText("occupancy")
        assert not dialog.table.isRowHidden(take_row(dialog, "crystal_feco.atom_site[Fe1].occupancy"))
        assert dialog.table.isRowHidden(take_row(dialog, "crystal_feco.atom_site[Fe1].fract_x"))
        for path in ("crystal_feco.atom_site[Fe1].occupancy", "crystal_feco.atom_site[Co1].occupancy"):
            dialog.table.item(take_row(dialog, path), COLUMN_USE).setCheckState(QtCore.Qt.Checked)
        assert dialog.line_expression.text() == "occ1 + occ2 = 1"
        dialog.accept_if_valid()
        assert dialog.result() == dialog.Accepted, dialog.label_error.text()
    finally:
        dialog.close()
    assert cryspy.take_constraints(obj) == ["occ1 + occ2 = 1"]
    atom_site = obj.crystal_feco.atom_site
    assert atom_site["Fe1"].occupancy_refinement and atom_site["Co1"].occupancy_mark == "occ2"
    assert '"occ1 + occ2 = 1"' in obj.to_cif()


def test_error_is_shown(qapp):
    obj = cryspy.str_to_globaln(RCIF)
    dialog = ConstraintDialog(obj)
    try:
        i_row = take_row(dialog, "crystal_feco.atom_site[Fe1].occupancy")
        dialog.table.item(i_row, COLUMN_USE).setCheckState(QtCore.Qt.Checked)
        dialog.table.item(i_row, COLUMN_MARK).setText("x")
        dialog.line_expression.setText("x * y = 1")
        dialog.expression_edited()
        dialog.accept_if_valid()
        assert dialog.result() != dialog.Accepted
        assert "not linear" in dialog.label_error.text()
        dialog.line_expression.setText("x = 0.5")
        dialog.accept_if_valid()
        assert dialog.result() == dialog.Accepted
    finally:
        dialog.close()
    assert cryspy.take_constraints(obj) == ["x = 0.5"]

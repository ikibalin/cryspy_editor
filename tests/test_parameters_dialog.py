"""Window "Parameters": refinement flags, values and favorites of all
parameters in one table."""
import cryspy
from PyQt5 import QtCore

from cryspy_editor.widgets.w_parameters_dialog import (
    COLUMN_FAVORITE,
    COLUMN_REFINE,
    COLUMN_VALUE,
    KEY_FAVORITES,
    ParametersDialog,
)

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
Fe1 Fe3+ 0.1 0.2 0.3 0.7()
Co1 Co2+ 0.1 0.2 0.3 0.3
"""

OCC_FE = "crystal_feco.atom_site[Fe1].occupancy"
OCC_CO = "crystal_feco.atom_site[Co1].occupancy"


def make_dialog(obj, d_setup=None):
    l_change = []
    d_setup = {} if d_setup is None else d_setup
    dialog = ParametersDialog(
        lambda: obj, d_setup, lambda: True,
        lambda label, text_before: l_change.append((label, text_before)))
    return dialog, l_change, d_setup


def take_row(dialog, path: str) -> int:
    return [record.path for record in dialog.l_record].index(path)


def test_refine_and_fix(qapp):
    obj = cryspy.str_to_globaln(RCIF)
    dialog, l_change, _d_setup = make_dialog(obj)
    try:
        atom_site = obj.crystal_feco.atom_site
        i_row = take_row(dialog, OCC_CO)
        dialog.table.item(i_row, COLUMN_REFINE).setCheckState(QtCore.Qt.Checked)
        assert atom_site["Co1"].occupancy_refinement
        # the history gets the text before the change
        assert l_change[-1][0] == f"refine {OCC_CO:}"
        assert "0.7()" in l_change[-1][1]

        dialog.fix_all()
        assert not atom_site["Fe1"].occupancy_refinement
        assert not atom_site["Co1"].occupancy_refinement
        assert dialog.label_count.text().startswith("Refined: 0 of")

        selection = dialog.table.selectionModel()
        for path in (OCC_FE, OCC_CO):
            selection.select(dialog.table.model().index(take_row(dialog, path), 0),
                             selection.Select | selection.Rows)
        dialog.refine_selected()
        assert atom_site["Fe1"].occupancy_refinement and atom_site["Co1"].occupancy_refinement
        assert l_change[-1][0] == "refine 2 parameters"
    finally:
        dialog.close()


def test_edit_value(qapp):
    obj = cryspy.str_to_globaln(RCIF)
    dialog, l_change, _d_setup = make_dialog(obj)
    try:
        dialog.table.item(take_row(dialog, OCC_FE), COLUMN_VALUE).setText("0.65")
        assert abs(obj.crystal_feco.atom_site["Fe1"].occupancy - 0.65) < 1e-12
        n_change = len(l_change)
        # not a number: the old value comes back
        dialog.table.item(take_row(dialog, OCC_FE), COLUMN_VALUE).setText("abc")
        assert dialog.table.item(take_row(dialog, OCC_FE), COLUMN_VALUE).text() == "0.65"
        assert len(l_change) == n_change
    finally:
        dialog.close()


def test_favorites_on_top_and_filter(qapp):
    obj = cryspy.str_to_globaln(RCIF)
    dialog, l_change, d_setup = make_dialog(obj)
    try:
        dialog.table.item(take_row(dialog, OCC_CO), COLUMN_FAVORITE).setCheckState(QtCore.Qt.Checked)
        assert d_setup[KEY_FAVORITES] == [OCC_CO]
        # favorites do not change the object
        assert len(l_change) == 0
        dialog.refresh()
        assert dialog.l_record[0].path == OCC_CO

        dialog.line_filter.setText("fract_x")
        assert not dialog.table.isRowHidden(take_row(dialog, "crystal_feco.atom_site[Fe1].fract_x"))
        assert dialog.table.isRowHidden(take_row(dialog, OCC_FE))
        # a favorite stays in view
        assert not dialog.table.isRowHidden(take_row(dialog, OCC_CO))
        dialog.line_filter.setText("*.occupancy")
        assert not dialog.table.isRowHidden(take_row(dialog, OCC_FE))

        dialog.line_filter.setText("")
        dialog.check_favorites.setChecked(True)
        l_shown = [record.path for i_row, record in enumerate(dialog.l_record)
                   if not dialog.table.isRowHidden(i_row)]
        assert l_shown == [OCC_CO]
        dialog.check_favorites.setChecked(False)
        dialog.check_refined.setChecked(True)
        l_shown = [record.path for i_row, record in enumerate(dialog.l_record)
                   if not dialog.table.isRowHidden(i_row)]
        assert l_shown == [OCC_FE]
    finally:
        dialog.close()

    # favorites come back in a new window
    dialog, l_change, d_setup = make_dialog(cryspy.str_to_globaln(RCIF), d_setup)
    try:
        assert dialog.l_record[0].path == OCC_CO
        assert dialog.table.item(0, COLUMN_FAVORITE).checkState() == QtCore.Qt.Checked
    finally:
        dialog.close()


def test_menu_of_main_window(qapp, monkeypatch, tmp_path):
    from cryspy_editor.ceditor import CMainWindow
    from cryspy_editor.widgets.w_constraint_dialog import is_constraint_supported
    monkeypatch.chdir(tmp_path)
    window = CMainWindow()
    try:
        menu = next(action.menu() for action in window.menu_bar.actions()
                    if action.text() == "Parameters")
        l_text = [action.text() for action in menu.actions()]
        assert "Parameters..." in l_text
        assert ("Add constraint..." in l_text) == is_constraint_supported()

        window.rcif_object = cryspy.str_to_globaln(RCIF)
        window.history.clear()
        window.renew_w_object_panel()
        window.show_parameters()
        dialog = window.parameters_dialog
        assert dialog.isVisible()
        dialog.table.item(take_row(dialog, OCC_CO), COLUMN_REFINE).setCheckState(QtCore.Qt.Checked)
        assert window.rcif_object.crystal_feco.atom_site["Co1"].occupancy_refinement
        assert len(window.history) == 1
        # the window follows the object of the main window (undo, new file)
        window.rcif_object = cryspy.str_to_globaln(RCIF)
        window.renew_w_object_panel()
        assert dialog.table.item(take_row(dialog, OCC_CO), COLUMN_REFINE).checkState() == \
            QtCore.Qt.Unchecked
    finally:
        window.close()

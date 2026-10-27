"""A double click in the RCIF tab gives the next allowed value of a text
value; refinement is set in the window Parameters, not by a double click."""
import cryspy
from PyQt5 import QtCore
from PyQt5.QtTest import QTest

from cryspy_editor.widgets.w_editcif import (
    WEditCif,
    switch_value_in_text,
    take_value_choices,
)

CELL = "_cell_length_a 8.45420(55)\n_cell_length_b 8.45421\n_cell_setting cubic"
SUSCEPTIBILITY = ("loop_\n_atom_site_susceptibility_label\n"
                  "_atom_site_susceptibility_chi_type\n_atom_site_susceptibility_chi_11\n"
                  "Fe3A Ciso 0.10000()\nFe3B Cani 0.20000")
CHOICES = take_value_choices(cryspy.AtomSiteSusceptibilityL)


def double_click(w_edit, position: int):
    cursor = w_edit.textCursor()
    cursor.setPosition(position)
    point = w_edit.cursorRect(cursor).center()
    QTest.mouseDClick(w_edit.viewport(), QtCore.Qt.LeftButton,
                      QtCore.Qt.NoModifier, point)


def test_value_switches_to_next_allowed():
    text = SUSCEPTIBILITY
    result = switch_value_in_text(text, text.index("Ciso") + 1, CHOICES)
    assert result[0].endswith("Fe3A Cani 0.10000()\nFe3B Cani 0.20000")
    result = switch_value_in_text(text, text.index("Cani") + 1, CHOICES)
    assert result[0].endswith("Fe3B Ciso 0.20000")
    # labels and numbers are not changed
    assert switch_value_in_text(text, text.index("Fe3A") + 1, CHOICES) is None
    assert switch_value_in_text(text, text.index("0.20000") + 1, CHOICES) is None
    assert switch_value_in_text(text, text.index("0.10000()") + 1, CHOICES) is None


def test_item_value_switches():
    text = "_extinction_model gauss\n_extinction_radius 1.0"
    result = switch_value_in_text(
        text, text.index("gauss") + 2, take_value_choices(cryspy.Extinction))
    assert result[0].startswith("_extinction_model lorentz\n")


def test_double_click_switches_value_in_widget(qapp):
    l_text = []
    w_edit = WEditCif(SUSCEPTIBILITY, l_text.append, value_choices=CHOICES)
    w_edit.show()
    double_click(w_edit, SUSCEPTIBILITY.index("Ciso") + 2)
    assert "Fe3A Cani 0.10000()" in w_edit.toPlainText()
    w_edit.rewrite_item_by_printed_text()
    assert "Fe3A Cani" in l_text[0]
    w_edit.close()


def test_double_click_on_number_does_not_refine(qapp):
    l_text = []
    w_edit = WEditCif(CELL, l_text.append, value_choices=take_value_choices(cryspy.Cell))
    w_edit.show()
    double_click(w_edit, CELL.index("8.45421") + 2)
    double_click(w_edit, CELL.index("8.45420(55)") + 2)
    assert w_edit.toPlainText() == CELL
    assert not w_edit.text_changed
    w_edit.close()

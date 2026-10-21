"""A double click on a number in the RCIF tab refines or fixes it."""
from PyQt5 import QtCore, QtGui
from PyQt5.QtTest import QTest

import cryspy

from cryspy_editor.widgets.w_editcif import (
    WEditCif, take_refinable_tags, toggle_refinement_in_text)

CELL = "_cell_length_a 8.45420(55)\n_cell_length_b 8.45421\n_cell_setting cubic"
LOOP = ("loop_\n_atom_site_label\n_atom_site_type_symbol\n_atom_site_fract_x\n"
        "_atom_site_fract_y\n_atom_site_fract_z\n"
        "Fe3A Fe3+ 0.12500 0.12500() 0.12500")
TAGS_CELL = take_refinable_tags(cryspy.Cell)
TAGS_LOOP = take_refinable_tags(cryspy.AtomSiteL)


def toggle(text, word, tags, shift=1):
    result = toggle_refinement_in_text(text, text.index(word) + shift, tags)
    return None if result is None else result[0]


def test_item_value_is_refined_and_fixed():
    text = toggle(CELL, "8.45421", TAGS_CELL)
    assert "_cell_length_b 8.45421()" in text
    text = toggle(CELL, "8.45420(55)", TAGS_CELL)
    assert "_cell_length_a 8.45420\n" in text


def test_not_refinable_or_not_a_number():
    assert toggle(CELL, "cubic", TAGS_CELL) is None
    assert toggle(CELL, "_cell_length_a", TAGS_CELL) is None
    assert toggle(LOOP, "Fe3A", TAGS_LOOP) is None


def test_loop_column():
    row = "Fe3A Fe3+ 0.12500 0.12500() 0.12500"
    text = toggle(LOOP, row, TAGS_LOOP, shift=len("Fe3A Fe3+ 0.1"))
    assert text.endswith("Fe3A Fe3+ 0.12500() 0.12500() 0.12500")
    text = toggle(LOOP, row, TAGS_LOOP, shift=len("Fe3A Fe3+ 0.12500 0.1"))
    assert text.endswith("Fe3A Fe3+ 0.12500 0.12500 0.12500")


def test_double_click_in_widget(qapp):
    l_text = []
    w_edit = WEditCif(CELL, l_text.append, refinable_tags=TAGS_CELL)
    w_edit.show()
    cursor = w_edit.textCursor()
    cursor.setPosition(CELL.index("8.45421") + 2)
    point = w_edit.cursorRect(cursor).center()
    QTest.mouseDClick(w_edit.viewport(), QtCore.Qt.LeftButton,
                      QtCore.Qt.NoModifier, point)
    assert "_cell_length_b 8.45421()" in w_edit.toPlainText()
    assert w_edit.text_changed
    w_edit.rewrite_item_by_printed_text()
    assert "8.45421()" in l_text[0]
    w_edit.close()

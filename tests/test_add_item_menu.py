"""Context menu Add of the object panel: a new item is added, no crash.

The action is triggered inside menu.exec_ of the context menu, as when the
user clicks it. The old slot took the class from self.sender(), which there
is the object panel: AttributeError in a slot, and Qt closed the editor.
"""
import os

import cryspy
import pytest
from PyQt5 import QtCore, QtWidgets

from cryspy_editor.widgets import w_structure_view

F_CRYSTAL = os.path.join(
    os.path.dirname(cryspy.__file__), "procedure_simulation",
    "crystal_Ho2Ti2O7.rcif")


class FakeWebView(QtWidgets.QWidget):
    """QtWebEngine needs OpenGL, which a headless test machine lacks."""

    def load(self, url):
        self.url = url


@pytest.fixture
def window(qapp, monkeypatch, tmp_path):
    from cryspy_editor.ceditor import CMainWindow
    monkeypatch.setattr(w_structure_view, "QWebEngineView", FakeWebView)
    monkeypatch.chdir(tmp_path)
    f_name = tmp_path / "crystal.rcif"
    with open(F_CRYSTAL, "r") as fid:
        f_name.write_text("global_test\n" + fid.read())
    main_window = CMainWindow()
    main_window.d_setup["data_file_name"] = str(f_name)
    main_window.take_rcif_object_from_d_setup()
    yield main_window
    main_window.close()


def click_in_context_menu(qapp, window, tree_item, l_menu_text):
    """Open the context menu of tree_item and click the action at the path
    l_menu_text, while the menu is shown (nested event loop)."""
    panel = window.w_object_panel
    l_clicked = []

    def click():
        menu = qapp.activePopupWidget()
        for text in l_menu_text[:-1]:
            menu = next(a.menu() for a in menu.actions() if a.text() == text)
        action = next(a for a in menu.actions() if a.text() == l_menu_text[-1])
        l_clicked.append(action.text())
        action.trigger()
        qapp.activePopupWidget().close()

    QtCore.QTimer.singleShot(100, click)
    panel.customContextMenuRequested.emit(
        panel.visualItemRect(tree_item).center())
    assert l_clicked == [l_menu_text[-1]]


@pytest.mark.parametrize("prefix", ["atom_site_aniso", "atom_site_moment"])
def test_add_loop_to_crystal(qapp, window, prefix):
    crystal = window.rcif_object.items[0]
    assert isinstance(crystal, cryspy.Crystal)
    assert not crystal.is_attribute(prefix)
    tree_item = window.w_object_panel.topLevelItem(0)
    window.item_clicked_on_w_object_panel(tree_item)  # crystal is selected

    click_in_context_menu(qapp, window, tree_item, ["Add", prefix])

    crystal = window.rcif_object.items[0]
    assert crystal.is_attribute(prefix)
    assert "ERROR" not in window.text_edit.toPlainText()
    assert window.history.entries[-1].label == f"add {prefix}"


def test_error_of_new_item_is_shown_not_raised(qapp, window, monkeypatch):
    def fail(self, l_item):
        raise ValueError("no place")
    monkeypatch.setattr(cryspy.Crystal, "add_items", fail)
    tree_item = window.w_object_panel.topLevelItem(0)

    click_in_context_menu(qapp, window, tree_item, ["Add", "atom_site_aniso"])

    assert "ERROR: 'AtomSiteAnisoL' is not added: ValueError: no place" in \
        window.text_edit.toPlainText()

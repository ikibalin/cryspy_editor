"""Tab with the 3D view of a crystal structure (page made by CrysPy)."""
import dataclasses
import os

import pytest
from PyQt5 import QtWidgets

import cryspy
from cryspy_editor.widgets import w_structure_view
from cryspy_editor.widgets.w_structure_view import (
    WStructureView, has_structure_view)

pytest.importorskip("py3Dmol")
pytestmark = pytest.mark.skipif(
    w_structure_view.StructureViewSettings is None,
    reason="CrysPy without the 3D view")

F_CRYSTAL = os.path.join(
    os.path.dirname(cryspy.__file__), "procedure_simulation",
    "crystal_Ho2Ti2O7.rcif")


class FakeWebView(QtWidgets.QWidget):
    """QtWebEngine needs OpenGL, which a headless test machine lacks."""

    def load(self, url):
        self.url = url


@pytest.fixture
def crystal():
    with open(F_CRYSTAL, "r") as fid:
        obj_global = cryspy.str_to_globaln("global_test\n" + fid.read())
    return obj_global.items[0]


@pytest.fixture
def widget(qapp, crystal, monkeypatch):
    monkeypatch.setattr(w_structure_view, "QWebEngineView", FakeWebView)
    monkeypatch.setattr(WStructureView, "settings", None)
    widget = WStructureView(crystal)
    widget.make_view()  # as when the tab is opened
    yield widget
    widget.close()


def read_page(widget):
    with open(widget.w_view.url.toLocalFile(), encoding="utf-8") as fid:
        return fid.read()


def test_web_view_is_made_when_tab_is_opened(qapp, crystal, monkeypatch):
    monkeypatch.setattr(w_structure_view, "QWebEngineView", FakeWebView)
    widget = WStructureView(crystal)
    assert widget.w_view is None
    widget.show()
    assert isinstance(widget.w_view, FakeWebView)
    widget.close()


def test_has_structure_view(crystal):
    assert has_structure_view(crystal)
    assert not has_structure_view(crystal.atom_site)


def test_page_uses_bundled_3dmol(widget):
    html = read_page(widget)
    assert "3Dmol-min.js" in html and "cdn.jsdelivr" not in html
    assert os.path.isfile(w_structure_view.F_JS)
    assert widget.w_message.isHidden()


def test_settings_panel_from_dataclass(widget):
    labels = [w.text() for w in widget.findChildren(QtWidgets.QLabel)]
    for field in dataclasses.fields(WStructureView.settings):
        shown = field.name.replace("_", " ") in labels
        assert shown == (field.name not in w_structure_view.HIDDEN_FIELDS)


def test_change_of_setting_redraws(widget):
    n_atom = read_page(widget).count("addArrow")
    spin = [w for w in widget.findChildren(QtWidgets.QSpinBox)][0]
    spin.setValue(2)  # n_cells_a
    assert WStructureView.settings.n_cells_a == 2
    widget.timer.stop()
    widget.redraw()
    assert read_page(widget).count("addArrow") >= n_atom

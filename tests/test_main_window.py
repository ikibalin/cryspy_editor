"""The main window starts and opens every example file."""
import glob
import os

import pytest

import cryspy_editor
from cryspy_editor.ceditor import CMainWindow

DIR_EXAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "examples")
# *_calc.rcif hold only calculated reflections written next to main.rcif
L_EXAMPLE = sorted(
    f_name for f_name in glob.glob(
        os.path.join(DIR_EXAMPLES, "**", "*.rcif"), recursive=True)
    if not f_name.endswith("_calc.rcif"))
# CrysPy fails on the space group of this old file (UnboundLocalError
# 'centrosymmetry' in SpaceGroup.form_object_by_it_number_it_coordinate_system_code)
SET_KNOWN_FAILURE = {os.path.join("DyAlO3", "test2", "main.rcif")}


def test_version():
    assert isinstance(cryspy_editor.__version__, str)


@pytest.fixture
def window(qapp, monkeypatch, tmp_path):
    # the window changes the working directory when it opens a file
    monkeypatch.chdir(tmp_path)
    main_window = CMainWindow()
    yield main_window
    main_window.close()


def test_window_starts(window):
    assert window.windowTitle().startswith("Cryspy Editor") or \
        window.windowTitle().startswith("CrysPy Editor")
    l_menu = [action.text() for action in window.menu_bar.actions()]
    assert "File" in l_menu
    assert "AI assistant" in l_menu


@pytest.mark.parametrize(
    "file_name", L_EXAMPLE,
    ids=[os.path.relpath(f, DIR_EXAMPLES) for f in L_EXAMPLE])
def test_open_example(window, file_name):
    if os.path.relpath(file_name, DIR_EXAMPLES) in SET_KNOWN_FAILURE:
        pytest.xfail("CrysPy cannot read the space group of this file")
    window.d_setup["data_file_name"] = file_name
    window.take_rcif_object_from_d_setup()
    assert len(window.rcif_object.items) > 0
    assert window.w_object_panel.topLevelItemCount() > 0
    assert "ERROR" not in window.text_edit.toPlainText()


def test_help_dialog(qapp):
    from cryspy_editor.widgets import help_dialog
    dialog = help_dialog.HelpDialog()
    dialog.line_query.setText("thermal vibrations")
    dialog.show_help()
    assert "atom_site_aniso" in dialog.text_help.toPlainText()

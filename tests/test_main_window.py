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


def test_cif_text_is_applied_before_run(window):
    """Text typed in the RCIF tab reaches the object before a procedure
    started from a menu (no focus change) runs in the thread."""
    from cryspy_editor.widgets.w_editcif import WEditCif
    window.d_setup["data_file_name"] = os.path.join(
        DIR_EXAMPLES, "Fe3O4_5T_powder_1d", "main.rcif")
    window.take_rcif_object_from_d_setup()
    crystal = [item for item in window.rcif_object.items
               if item.is_attribute("cell")][0]
    window.renew_w_item_tabs((crystal.get_name(), "cell"))
    w_edit = [window.w_item_tabs.widget(ind)
              for ind in range(window.w_item_tabs.count())
              if isinstance(window.w_item_tabs.widget(ind), WEditCif)][0]
    w_edit.setPlainText(w_edit.toPlainText().replace(
        "_cell_length_a 8.45420", "_cell_length_a 8.50000"))
    l_value = []

    def procedure(rcif_object):
        l_value.append(rcif_object.items[
            window.rcif_object.items.index(crystal)].cell.length_a)

    window.cthread.function = procedure
    window.cthread.arguments = (window.rcif_object, )
    window.cthread.start()
    assert window.cthread.wait(10000)
    assert l_value == [8.5]


def test_refresh_lists_variables_with_parameter_paths(window):
    """Refresh names the refined variables as the window Parameters does."""
    from cryspy.procedure_assistant.parameters import take_parameter_records
    window.d_setup["data_file_name"] = os.path.join(
        DIR_EXAMPLES, "Fe3O4_5T_powder_1d", "main.rcif")
    window.take_rcif_object_from_d_setup()
    window.refresh_view()
    text = window.text_edit.toPlainText()
    n_variable = len(window.rcif_object.get_variable_names())
    assert f"Number of variables is {n_variable}." in text
    l_path = [record.path for record in take_parameter_records(window.rcif_object)
              if record.flag_refinement and not record.flag_constraint]
    assert len(l_path) == n_variable > 0
    for path in l_path:
        assert f" - {path} " in text

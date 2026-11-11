"""Methods of the objects (context menu Methods of the object panel) open
in a separate window, as the procedures of the menus, not in the panel on
top of the main window."""
import numpy
import pytest
from PyQt5 import QtWidgets

from cryspy_editor.widgets import w_procedure_dialog
from cryspy_editor.widgets.w_procedure_dialog import (
    ArgumentsDialog,
    ProcedureDialog,
    split_arguments,
    text_to_value,
)


def test_text_to_value():
    assert text_to_value("3") == 3
    assert text_to_value("0.5") == 0.5
    assert numpy.all(text_to_value("1, 2, 3") == numpy.array([1, 2, 3]))
    assert numpy.allclose(text_to_value("[0.1, 0.2]"), [0.1, 0.2])
    assert text_to_value("True") is True
    assert text_to_value("cell", {"cell": "object"}) == "object"
    assert text_to_value("hello") == "hello"


def test_split_arguments():
    def func(a, b=2, c=3, *, d=4):
        return a, b, c, d
    assert split_arguments(func, {"a": 1}) == ((1,), {})
    assert split_arguments(func, {"a": 1, "c": 5}) == ((1, 2, 5), {})
    assert split_arguments(func, {"a": 1, "d": 7}) == ((1,), {"d": 7})


def run_on_thread(editor_window, monkeypatch):
    l_run = []
    monkeypatch.setattr(editor_window.cthread, "start",
                        lambda: l_run.append((editor_window.cthread.function,
                                              editor_window.cthread.arguments)))
    return l_run


def test_method_without_parameters_runs_at_once(qapp, editor_window, monkeypatch):
    l_run = run_on_thread(editor_window, monkeypatch)
    monkeypatch.setattr(QtWidgets.QDialog, "exec_", lambda self: pytest.fail("no editor_window"))
    cell = editor_window.rcif_object.items[0].cell
    editor_window.run_object_function(cell.report)
    assert len(l_run) == 1
    function, arguments = l_run[0]
    assert function() == cell.report() and arguments == ()


def test_undescribed_method_opens_window(qapp, editor_window, monkeypatch):
    l_run = run_on_thread(editor_window, monkeypatch)
    cell = editor_window.rcif_object.items[0].cell
    l_dialog = []

    def exec_(self):
        assert isinstance(self, ArgumentsDialog)
        l_dialog.append(self)
        self.d_widget["x"].setText("0.5")
        self.d_widget["y"].setText("0")
        self.d_widget["z"].setText("0")
        self.accept_if_valid()
        return QtWidgets.QDialog.Accepted
    monkeypatch.setattr(ArgumentsDialog, "exec_", exec_)
    editor_window.run_object_function(cell.calc_position_by_coordinate)
    assert len(l_dialog) == 1
    function, arguments = l_run[0]
    assert arguments == (0.5, 0, 0)
    assert numpy.allclose(function(*arguments), cell.calc_position_by_coordinate(0.5, 0, 0))


def test_missing_value_is_an_error_in_the_window(qapp, editor_window):
    cell = editor_window.rcif_object.items[0].cell
    dialog = ArgumentsDialog(cell.calc_position_by_coordinate, editor_window.rcif_object)
    dialog.accept_if_valid()
    assert dialog.arguments() is None
    assert "x" in dialog.label_error.text()


def test_described_method_opens_procedure_window(qapp, editor_window, monkeypatch):
    l_run = run_on_thread(editor_window, monkeypatch)
    cell = editor_window.rcif_object.items[0].cell
    if w_procedure_dialog.take_description(cell.calc_sthovl) is None:
        pytest.skip("CrysPy does not describe calc_sthovl")
    l_dialog = []

    def exec_(self):
        l_dialog.append(self)
        for name in ("index_h", "index_k", "index_l"):
            self.d_widget[name].setText("1")
        self.accept_if_valid()
        return QtWidgets.QDialog.Accepted
    monkeypatch.setattr(ProcedureDialog, "exec_", exec_)
    editor_window.run_object_function(cell.calc_sthovl)
    assert len(l_dialog) == 1
    assert l_run[0][1] == (1, 1, 1)


def test_no_function_panel_on_top(qapp, editor_window):
    assert not hasattr(editor_window, "w_function")


def test_method_from_context_menu(qapp, editor_window, monkeypatch):
    """Click Methods > report() in the context menu of the crystal."""
    from test_add_item_menu import click_in_context_menu
    l_run = run_on_thread(editor_window, monkeypatch)
    tree_item = editor_window.w_object_panel.topLevelItem(0)
    editor_window.item_clicked_on_w_object_panel(tree_item)
    crystal = editor_window.rcif_object.items[0]
    click_in_context_menu(qapp, editor_window, tree_item, ["Methods", "report()"])
    assert len(l_run) == 1
    assert l_run[0][0]() == crystal.report()

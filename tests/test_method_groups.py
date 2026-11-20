"""Context menu Methods: methods with the same first word go to a submenu
(calc_ -> Calculate, report_ -> Report) when there are enough of them."""
from types import FunctionType

import cryspy

from cryspy_editor.method_groups import (
    MIN_METHODS_IN_SUBMENU, group_method_names, take_group_title)


def test_titles():
    assert take_group_title("calc_sthovl") == "Calculate"
    assert take_group_title("report_html") == "Report"
    assert take_group_title("report") == "Report"
    assert take_group_title("plots") == "Plot"
    assert take_group_title("refine_all_variables") == "Refine"


def test_submenu_only_for_many_methods():
    names = ["calc_a", "calc_b", "calc_c", "calc_d", "report_a", "report_b",
             "get_x", "calc_e"]
    groups = group_method_names(names, min_methods=4)
    assert groups == [
        ("Calculate", ["calc_a", "calc_b", "calc_c", "calc_d", "calc_e"]),
        (None, ["report_a", "report_b", "get_x"]),
    ]


def test_few_methods_stay_in_the_menu():
    names = ["calc_a", "report", "get_x"]
    assert group_method_names(names) == [(None, names)]


def test_default_threshold():
    names = [f"calc_{i}" for i in range(MIN_METHODS_IN_SUBMENU)]
    assert group_method_names(names) == [("Calculate", names)]
    assert group_method_names(names[:-1]) == [(None, names[:-1])]


def test_each_method_once():
    """No method is lost or doubled for real CrysPy classes."""
    for cls in (cryspy.Crystal, cryspy.Cell, cryspy.AtomSiteL, cryspy.Pd,
                cryspy.Diffrn):
        names = [n for n, f in cls.__dict__.items()
                 if type(f) is FunctionType and not n.startswith("_")]
        groups = group_method_names(names)
        l_name = [n for _, l_n in groups for n in l_n]
        assert sorted(l_name) == sorted(names)


def methods_menu_path(item, name):
    names = [n for n, f in type(item).__dict__.items()
             if type(f) is FunctionType and not n.startswith("_")]
    for title, l_name in group_method_names(names):
        if name in l_name:
            return ["Methods"] if title is None else ["Methods", title]
    raise ValueError(name)


def test_method_from_submenu(qapp, editor_window, monkeypatch):
    """A method in a submenu runs from the context menu as before."""
    from test_add_item_menu import click_in_context_menu
    from test_method_dialog import run_on_thread
    l_run = run_on_thread(editor_window, monkeypatch)
    tree_item = editor_window.w_object_panel.topLevelItem(0)
    editor_window.item_clicked_on_w_object_panel(tree_item)
    crystal = editor_window.rcif_object.items[0]
    path = methods_menu_path(crystal, "report")
    click_in_context_menu(qapp, editor_window, tree_item, path + ["report()"])
    assert len(l_run) == 1
    assert l_run[0][0]() == crystal.report()

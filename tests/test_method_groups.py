"""Context menu Methods: methods with the same first word go to a submenu
(calc_ -> Calculate, report_ -> Report) when there are enough of them; the
groups come from CrysPy (cryspy.group_methods_for_menu)."""
from types import FunctionType

import cryspy

from cryspy_editor import method_groups
from cryspy_editor.method_groups import MIN_METHODS_IN_SUBMENU, group_methods


def make(name, doc="Do something."):
    def function(self):
        pass
    function.__name__ = name
    function.__doc__ = doc
    return function


def own_methods(cls):
    return {n: f for n, f in cls.__dict__.items()
            if type(f) is FunctionType and not n.startswith("_")}


def test_submenu_only_for_many_methods():
    names = ["calc_a", "calc_b", "calc_c", "calc_d", "report_a", "report_b",
             "get_x", "calc_e"]
    groups = group_methods({name: make(name) for name in names}, min_methods=4)
    assert groups == [
        ("Calculate", ["calc_a", "calc_b", "calc_c", "calc_d", "calc_e"]),
        (None, ["report_a", "report_b", "get_x"]),
    ]


def test_few_methods_stay_in_the_menu():
    names = ["calc_a", "report", "get_x"]
    assert group_methods({name: make(name) for name in names}) == [(None, names)]


def test_default_threshold():
    names = [f"calc_{i}" for i in range(MIN_METHODS_IN_SUBMENU)]
    d_method = {name: make(name) for name in names}
    assert group_methods(d_method) == [("Calculate", names)]
    del d_method[names[-1]]
    assert group_methods(d_method) == [(None, names[:-1])]


def test_fallback_without_cryspy_menus(monkeypatch):
    """CrysPy before group_methods_for_menu: groups by the first word."""
    monkeypatch.setattr(method_groups, "_group_methods_for_menu", None)
    test_submenu_only_for_many_methods()
    test_default_threshold()


def test_each_method_once():
    """No method is doubled for real CrysPy classes."""
    for cls in (cryspy.Crystal, cryspy.Cell, cryspy.AtomSiteL, cryspy.Pd,
                cryspy.Diffrn):
        d_method = own_methods(cls)
        l_name = [n for _, l_n in group_methods(d_method) for n in l_n]
        assert len(l_name) == len(set(l_name)) and set(l_name) <= set(d_method)


def methods_menu_path(item, name):
    for title, l_name in group_methods(own_methods(type(item))):
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

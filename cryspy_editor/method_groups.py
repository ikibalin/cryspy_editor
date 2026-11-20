"""Group the methods of a CrysPy object for the context menu Methods.

Some CrysPy objects have many methods. Methods with the same first word
(``calc_``, ``report_``, ``get_``, ...) go to a submenu (Calculate, Report,
Get, ...) when there are at least ``MIN_METHODS_IN_SUBMENU`` of them; the
others stay in the menu itself. The groups come from the method names only,
so a new method of CrysPy finds its place without changes here, as in the
menus of CrysPy procedures (first word of the name, Calc -> Calculate).
"""
from typing import List, Optional, Tuple

# a submenu appears when at least so many methods share the first word
MIN_METHODS_IN_SUBMENU = 4

# titles of the submenus for the usual first words; other words are
# capitalized ("refine" -> "Refine")
D_TITLE = {
    "calc": "Calculate",
    "plot": "Plot",
    "plots": "Plot",
    "del": "Delete",
    "rm": "Remove",
    "is": "Check",
}


def take_group_title(name: str) -> str:
    """Title of the submenu for a method name: its first word.

    >>> take_group_title("calc_sthovl")
    'Calculate'
    >>> take_group_title("report_html")
    'Report'
    >>> take_group_title("report")
    'Report'
    """
    word = name.split("_")[0].lower()
    return D_TITLE.get(word, word.capitalize())


def group_method_names(
        method_names: List[str],
        min_methods: int = MIN_METHODS_IN_SUBMENU,
) -> List[Tuple[Optional[str], List[str]]]:
    """Group method names for the menu.

    Returns a list of (title, names): first the submenus in alphabetical
    order of their titles, then (None, names) with the methods that stay in
    the menu itself. The order of the methods inside a group is the order of
    ``method_names``.
    """
    d_group = {}
    for name in method_names:
        d_group.setdefault(take_group_title(name), []).append(name)
    l_submenu = []
    l_alone = []
    for title in sorted(d_group.keys()):
        names = d_group[title]
        if len(names) >= min_methods:
            l_submenu.append((title, names))
    in_submenu = {name for _, names in l_submenu for name in names}
    l_alone = [name for name in method_names if name not in in_submenu]
    if len(l_alone) != 0:
        l_submenu.append((None, l_alone))
    return l_submenu

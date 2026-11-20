"""Group the methods of a CrysPy object for the context menu Methods.

The groups come from CrysPy (cryspy.group_methods_for_menu): methods with
the same first word (calc_, report_, ...) go to a submenu (Calculate,
Report, ...) when there are at least 4 of them, a line "Menu: <name>" in
the docstring sets the submenu, "Menu: -" hides the method from the menu.
The fallback below (first word only) is for CrysPy versions before that
function; remove it after the CrysPy release.
"""
from typing import Callable, Dict, List, Optional, Tuple

try:
    from cryspy import group_methods_for_menu as _group_methods_for_menu
except ImportError:
    _group_methods_for_menu = None

# a submenu appears when at least so many methods share the first word
MIN_METHODS_IN_SUBMENU = 4

D_TITLE = {"calc": "Calculate", "plot": "Plot", "plots": "Plot",
           "del": "Delete", "rm": "Remove", "is": "Check"}


def take_group_title(name: str) -> str:
    """Title of the submenu by the first word of a method name."""
    word = name.split("_")[0].lower()
    return D_TITLE.get(word, word.capitalize())


def group_methods(
        d_method: Dict[str, Callable],
        min_methods: int = MIN_METHODS_IN_SUBMENU,
) -> List[Tuple[Optional[str], List[str]]]:
    """[(submenu, names), ...] in alphabetical order of the submenus, then
    (None, names) of the methods directly in the menu."""
    if _group_methods_for_menu is not None:
        return _group_methods_for_menu(d_method, min_methods)
    d_group = {}
    for name in d_method:
        d_group.setdefault(take_group_title(name), []).append(name)
    l_out = [(title, d_group[title]) for title in sorted(d_group)
             if len(d_group[title]) >= min_methods]
    in_submenu = {name for _, names in l_out for name in names}
    l_alone = [name for name in d_method if name not in in_submenu]
    if l_alone:
        l_out.append((None, l_alone))
    return l_out

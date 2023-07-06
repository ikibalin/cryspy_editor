"""
Define actions and toolbars for procedures
"""
# import logging
from typing import List, Callable

from cryspy import GlobalN, DataN, LoopN, ItemN, file_to_globaln, load_packages, \
    L_FUNCTION, L_GLOBAL_CLASS, L_DATA_CLASS, L_LOOP_CLASS, L_ITEM_CLASS
load_packages()
from cryspy import L_FUNCTION_ADD



def cryspy_procedures_to_dictionary(l_func_external: list):
    d_procedures = {}
    l_func = [func for func in L_FUNCTION+L_FUNCTION_ADD if check_function_for_procedure(func)]
    l_func.extend(l_func_external)

    l_func_name = [
        func.__name__.replace("_", " ").title().replace("Mempy", "MEMPy")\
            .replace("Rhochi", "RhoChi").replace("Calc ", "Calculate ")
        for func in l_func]

    l_first_word = [func_name.split(" ")[0] for func_name in l_func_name]
    s_first_word = set(l_first_word)

    d_procedures["Unsorted procedures"] = []

    for first_word in s_first_word:
        if l_first_word.count(first_word) != 1:
            d_procedures[first_word] = []

    keys = d_procedures.keys()
    for func, first_word in zip(l_func, l_first_word):
        if first_word in keys:
            d_procedures[first_word].append(func)
        else:
            d_procedures["Unsorted procedures"].append(func)
    return d_procedures


def get_plot_functions_for_data_loop_item(l_func_external: list):
    l_plot_data, l_plot_loop, l_plot_item = [], [], []
    l_func_reserved = [func for func in L_FUNCTION+L_FUNCTION_ADD+l_func_external if check_function_reserved_for_cryspy_editor(func)]
    for func in l_func_reserved:
        if func.__name__.startswith("plot_data_"):
            l_plot_data.append(func)
        if func.__name__.startswith("plot_loop_"):
            l_plot_loop.append(func)
        if func.__name__.startswith("plot_item_"):
            l_plot_item.append(func)
    return l_plot_data, l_plot_loop, l_plot_item


def cryspy_classes_to_dictionary():
    d_classes = {"GlobalN": GlobalN, "DataN": DataN, "LoopN": LoopN, "ItemN": ItemN,
        "global": L_GLOBAL_CLASS, "data": L_DATA_CLASS, "loop": L_LOOP_CLASS, "item": L_ITEM_CLASS}
    return d_classes


def check_function_reserved_for_cryspy_editor(func: Callable):
    if not("__code__" in dir(func)):
        return False
    n_row_need = func.__code__.co_argcount
    if n_row_need != 1:
        return False
    if not(func.__name__.startswith(
            ("check_data_", "check_loop_", "check_item_",
            "plot_data_", "plot_loop_", "plot_item_",))):
        return False
    d_annotations = func.__annotations__
    if not("item" in d_annotations.keys()):
        return False
    item_type = d_annotations["item"]
    s_type = func.__name__.split("_")[1]
    if (s_type == "data") and (item_type is DataN):
        return True
    if (s_type == "loop") and (item_type is LoopN):
        return True
    if (s_type == "item") and (item_type is ItemN):
        return True
    return False


def check_function_for_procedure(func: Callable):
    if check_function_reserved_for_cryspy_editor(func):
        return False
    if not("__code__" in dir(func)):
        return False
    n_row_need = func.__code__.co_argcount

    d_annotations = func.__annotations__
    n_globaln = 0
    f_defined_types, f_items = True, False
    f_basic = False
    block_name = ""
    if "return" in d_annotations.keys():
        obj_return = d_annotations.pop("return")

    if len(d_annotations.items()) != n_row_need:
        f_defined_types = False
        return f_defined_types
    for item in d_annotations.items():

        if item[1].__class__.__name__ == '_UnionGenericAlias':
            item_types = set(item[1].__args__)
        else:
            item_types = set((item[1], ))
        type_item_types = [type(item_type) for item_type in item_types]

        if GlobalN in item_types:
            n_globaln += 1
        elif item == ("d_info", dict):
            pass
        elif len(item_types & set((int, float, complex, str, bool))) > 0:
            f_basic = True
        elif type in type_item_types:
            for item_type in item_types:
                if issubclass(item_type, (ItemN, LoopN, DataN)):
                    f_items = True
            if not(f_items):
                f_defined_types = False
        else:
            f_defined_types = False
    if (f_items | (n_globaln > 1) | (f_basic & (n_globaln == 1))):
        pass
    elif f_basic:
        f_defined_types = False

    if ((n_globaln ==0) and (f_items==False)):
        f_defined_types = False

    return f_defined_types

def check_function_to_auto_run(func: Callable):
    """
    Procedure or method is auto run if there is no
    external parameters except
    1. Self objetc
    2. GlobalN object (taken from GUI)
    3. d_info object
    """
    n_row_need = func.__code__.co_argcount

    d_annotations = func.__annotations__
    n_globaln = 0
    f_defined_types = True
    block_name = ""
    if "return" in d_annotations.keys():
        obj_return = d_annotations.pop("return")

    if len(d_annotations.items()) != n_row_need:
        f_defined_types = False
        return f_defined_types
    for item in d_annotations.items():
        if item[1].__class__.__name__ == '_UnionGenericAlias':
            item_types = set(item[1].__args__)
        else:
            item_types = set((item[1], ))

        if GlobalN in item_types:
            n_globaln += 1
        elif item == ("d_info", dict):
            pass
        else:
            f_defined_types = False
    if  (f_defined_types & (n_globaln == 1)):
        f_defined_types = True
    else:
        f_defined_types = False
    return f_defined_types


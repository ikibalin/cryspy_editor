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

def cryspy_classes_to_dictionary():
    d_classes = {"GlobalN": GlobalN, "DataN": DataN, "LoopN": LoopN, "ItemN": ItemN,
        "global": L_GLOBAL_CLASS, "data": L_DATA_CLASS, "loop": L_LOOP_CLASS, "item": L_ITEM_CLASS}
    return d_classes

# # TO DELITE
# def form_actions(cbuilder, parent_action, functions: List[Callable]):
#     "Form actions for list of functions"
#     toolbar = cbuilder.toolbar

#     l_func = [func for func in functions if check_function_for_procedure(func)]

#     l_func_name = [
#         func.__name__.replace("_", " ").title().replace("Mempy", "MEMPy")\
#             .replace("Rhochi", "RhoChi").replace("Calc ", "Calculate ")
#         for func in l_func]

#     l_first_word = [func_name.split(" ")[0] for func_name in l_func_name]
#     s_first_word = set(l_first_word)
#     l_numb = [l_first_word.count(first_word) for first_word in l_first_word]    

#     menu_gen = parent_action.addMenu("Unsorted")
#     for first_word in sorted(list(s_first_word)):
#         flag_add = False
#         if l_first_word.count(first_word) != 1:
#             menu_add = parent_action.addMenu(first_word)
#             flag_add = True

#         for func, func_name in zip(l_func, l_func_name):
#             if func_name.split(" ")[0] == first_word: 
#                 if flag_add:
#                     func_name_2 = func_name[(func_name.find(" ")+1):]
#                     f_action = QtWidgets.QAction(func_name_2, menu_add)
#                     menu_add.addAction(f_action)
#                 else:
#                     f_action = QtWidgets.QAction(func_name, menu_gen)
#                     menu_gen.addAction(f_action)

#                 f_action.object = func
#                 if func.__doc__ is not None:
#                     f_action.setStatusTip(func.__doc__.strip().split("\n")[0])
#                 f_action.triggered.connect(lambda: triggered_action(cbuilder))

#     return


# def form_toolbar(cbuilder, functions: List[Callable]):
#     toolbar = cbuilder.toolbar

#     for func in functions:
#         if check_function_for_toolbar(func):
#             func_name = "["+func.__name__.replace("_", " ").title().replace("Mempy", "MEMPy").replace("Rhochi", "RhoChi") + "]"
#             func_action = QtWidgets.QAction(func_name, toolbar)
#             func_action.object = func
#             func_action.triggered.connect(lambda: triggered_toolbar(cbuilder))
#             toolbar.addAction(func_action)


# def triggered_action(cbuilder):
#     sender = cbuilder.sender()
#     func = sender.object

#     flag = check_function_for_toolbar(func)
#     if flag:
#         obj_globaln = cbuilder.wpanel.object

#         cbuilder.mythread.function = func
#         cbuilder.mythread.arguments = (obj_globaln, )
#         cbuilder.mythread.start()
#     else:
#         w_function, thread = cbuilder.wfunction, cbuilder.mythread
#         # make a choise if only GlobalN that thread.start()
#         w_function.set_function(func, thread)


# def triggered_toolbar(cbuilder):
#     sender = cbuilder.sender()
#     func = sender.object
#     obj_globaln = cbuilder.wpanel.object
#     cbuilder.mythread.function = func
#     cbuilder.mythread.arguments = (obj_globaln, )
#     cbuilder.mythread.start()


def check_function_for_procedure(func: Callable):
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


# def check_function_for_toolbar(func: Callable):
#     n_row_need = func.__code__.co_argcount
#     if n_row_need > 2:
#         return False
#     d_annotations = func.__annotations__
#     f_globaln, f_info, f_only = False, True, True
#     for item in d_annotations.items():
#         if item[1] is GlobalN:
#             f_globaln = True
#         elif item == ("d_info", dict):
#             f_info = True
#         else:
#             f_only = False
#     return (f_globaln & f_info & f_only)

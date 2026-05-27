import numpy
from cryspy_editor.widgets.function_basis import remove_all_items
from cryspy_editor.widgets.procedures import (
    procedure_equiv_hkl,
    procedure_column_del,
    L_OPERATION,
    estimate_expression,
    procedure_column_sort,
    procedure_column_general,
    procedure_calc,
    procedure_group_hkl,
    procedure_aver_hkl,
    procedure_column_mark,
    procedure_generate_hkl,
    procedure_print,
    take_val,
    procedure_copy_to_clipboard,
    procedure_column,
    procedure_action_for_columns,
    procedure_columns_round,
    procedure_convert_to_int_format,
)

from cryspy_editor.widgets.cod import load_cif_from_cod_by_formula
from PyQt5 import QtWidgets
import cryspy_editor.widgets.ui_setting as ui_setting

L_ACTION_NAME = [
    "mean",
    "std",
    "sort",
    "del",
    "group_hkl",
    "equiv_hkl",
    "mean_hkl",
    "calc",
    "stat",
    "fit",
    "aver_hkl",
    "generate_hkl",
    "mark",
    "print",
    "sum",
    "min",
    "max",
    "copy_to_clipboard",
    "column",
    "load_cif",
    "int",
    "round",
    "convert_to_int_format",
    "abs",
]


def redefine_inline_parameters(d_np_table):
    # tables
    s_name = "Delete"
    if s_name in d_np_table[" table_names"]:
        remove_all_items(
            d_np_table[" table_names"], s_name, d_np_table[" table_commands"]
        )
        if s_name in d_np_table.keys():
            del d_np_table[s_name]

    for i_name, command_name in enumerate(d_np_table[" table_commands"]):
        if command_name == "":
            continue
        if (command_name[0] in L_OPERATION) and len(command_name) > 1:
            try:
                coeff = float(command_name[1:])
            except ValueError:
                continue
            if len(d_np_table[" table_names"]) <= i_name:
                continue
            name_var = d_np_table[" table_names"][i_name]
            val_name = d_np_table[name_var]
            ind_operation = L_OPERATION.index(command_name[0])
            try:
                if ind_operation == 0:
                    d_np_table[name_var] = val_name + coeff
                elif ind_operation == 1:
                    d_np_table[name_var] = val_name - coeff
                elif ind_operation == 2:
                    d_np_table[name_var] = val_name * coeff
                elif ind_operation == 3:
                    d_np_table[name_var] = val_name / coeff
                elif ind_operation == 4:
                    d_np_table[name_var] = val_name**coeff
                d_np_table[" table_commands"][i_name] = ""
            except:
                continue

    # inline_parameters
    l_inline_name = d_np_table[" inline_names"]
    s_name = "Unit Cell"
    if s_name in l_inline_name:
        val = d_np_table[s_name]
        del d_np_table[s_name]
        d_np_table[" inline_names"].pop(
            d_np_table[" inline_names"].index(s_name)
        )
        l_name = [
            "a",
            "b",
            "c",
            "alpha",
            "beta",
            "gamma",
        ]
        if len(val) == 3:
            val.extend([90.0, 90.0, 90.0])
        if len(val) >= 6:
            for i_name, name in enumerate(l_name):
                if not (name in d_np_table[" inline_names"]):
                    d_np_table[" inline_names"].append(name)
                d_np_table[name] = numpy.array(
                    [
                        float(val[i_name]),
                    ],
                    dtype=float,
                )

    s_name = "UB-matrix"
    if s_name in l_inline_name:
        val = d_np_table[s_name]
        del d_np_table[s_name]
        d_np_table[" inline_names"].pop(
            d_np_table[" inline_names"].index(s_name)
        )
        l_name = [
            "UB_11",
            "UB_12",
            "UB_13",
            "UB_21",
            "UB_22",
            "UB_23",
            "UB_31",
            "UB_32",
            "UB_33",
        ]
        if len(val) >= 9:
            for i_name, name in enumerate(l_name):
                if not (name in d_np_table[" inline_names"]):
                    d_np_table[" inline_names"].append(name)
                d_np_table[name] = numpy.array(
                    [
                        float(val[i_name]),
                    ],
                    dtype=float,
                )

    # operations with defined functions
    for expression_name in d_np_table[" expressions"]:
        s_hh = expression_name.strip().split()[0].lower()
        if s_hh in L_ACTION_NAME:
            s_param = " ".join(expression_name.strip().split()[1:])
            if L_ACTION_NAME.index(s_hh) == 0:  # mean
                procedure_column_general(expression_name, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 1:  # std
                procedure_column_general(expression_name, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 2:  # sort
                procedure_column_sort(s_param, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 3:  # del
                procedure_column_del(s_param, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 4:  # group_hkl
                procedure_group_hkl(s_param, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 5:  # equiv_hkl
                procedure_equiv_hkl(s_param, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 7:  # calc
                procedure_calc(s_param, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 10:  # aver_hkl
                procedure_aver_hkl(s_param, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 11:  # generate_hkl
                procedure_generate_hkl(s_param, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 12:  # mark
                procedure_column_mark(s_param, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 13:  # print
                procedure_print(s_param, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 14:  # sum
                procedure_column_general(expression_name, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 15:  # min
                procedure_column_general(expression_name, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 16:  # max
                procedure_column_general(expression_name, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 17:  # copy_to_clipboard
                procedure_copy_to_clipboard(s_param, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 18:  # column
                procedure_column(s_param, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 19:  # load_cif
                s_res = load_cif_from_cod_by_formula(s_param)
                clipboard = QtWidgets.QApplication.clipboard()
                clipboard.setText(s_res)
                S_COMMENT = ui_setting.get_comment_character()
                d_np_table[" comments"].append(
                    f"{S_COMMENT:} CIF file for '{s_param}' is copied to clipboard."
                )
            elif L_ACTION_NAME.index(s_hh) == 20:  # int columns
                procedure_action_for_columns(s_hh, s_param, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 21:  # round columns
                procedure_columns_round(s_param, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 22:  # convert_to_int_format
                procedure_convert_to_int_format(s_param, d_np_table)
            elif L_ACTION_NAME.index(s_hh) == 23:  # abs
                procedure_action_for_columns(s_hh, s_param, d_np_table)

            continue
        l_hh = expression_name.split("=")
        s_name_left = l_hh[0].strip()
        s_func_right = l_hh[1].strip()
        val, flag = estimate_expression(s_func_right, d_np_table)
        if not flag:
            continue
        l_name_table = d_np_table[" table_names"]
        l_name_table_lower = [_.lower() for _ in l_name_table]
        if s_name_left.lower() in l_name_table_lower:
            d_np_table[
                l_name_table[l_name_table_lower.index(s_name_left.lower())]
            ] = val
        else:
            d_np_table[s_name_left] = val
            d_np_table[" table_names"].append(s_name_left)
            d_np_table[" table_commands"].append("")

    # operations with defined functions
    n_row = 0
    for name in d_np_table[" table_names"]:
        try:
            n_row = d_np_table[name].size
            s_name = "Number of Rows in table"
            if not (s_name in d_np_table.keys()):
                d_np_table[" inline_names"].append(s_name)
            d_np_table[s_name] = [
                n_row,
            ]
        except:
            continue
    return


def xy_to_plot(D_NP_TABLE):
    l_name = D_NP_TABLE[" table_names"]

    l_commands = D_NP_TABLE[" table_commands"]
    np_y, flag_y, name_y = take_val("y", D_NP_TABLE)
    np_x, flag_x, name_x = take_val("x", D_NP_TABLE)
    D_OUT = {"x": [], "y": [], "name_x": "", "name_y": ""}
    if not flag_y:
        return D_OUT

    if not flag_x:
        np_x = numpy.linspace(1, np_y.size, num=np_y.size, endpoint=True)
    D_OUT = {"x": np_x, "y": np_y, "name_x": name_x, "name_y": name_y}
    return D_OUT

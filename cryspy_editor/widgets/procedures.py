import numpy
from cryspy_editor.widgets.from_cryspy import (
    calc_sthovl_by_unit_cell_parameters,
    calc_index_hkl_in_range,
    calc_unit_cell_parameters_and_u_by_ub,
)
from cryspy_editor.widgets.colors import (
    L_COLOR_TABLE,
    L_COLOR,
    transform_color,
)
from cryspy_editor.widgets.function_dictionary import (
    transform_name_to_table_name,
)
from PyQt5 import QtWidgets
import cryspy_editor.widgets.ui_setting as ui_setting

L_OPERATION_IN = [">", "<", "=="]

L_OPERATION = [
    "+",
    "-",
    "*",
    "/",
    "^",
    "%",
]


def procedure_column_general(s_line: str, d_np_table: dict):
    s_command = s_line.strip().split()[0].lower()
    l_name = s_line.strip().split()[1:]
    if len(l_name) < 1:
        raise ValueError(
            f"For command '{s_command.capitalize():}' the name of the column should be given"
        )

    for name in l_name:
        val, flag, name_in_d = take_val(name, d_np_table)
        if not flag:
            raise ValueError(
                f"The column '{name:}' should be defined in table to cald '{s_command.capitalize():}'"
            )

        if s_command == "sum":
            res = numpy.sum(val)
        elif s_command == "std":
            res = numpy.std(val)
        elif s_command == "mean":
            res = numpy.mean(val)
        elif s_command == "min":
            res = numpy.min(val)
        elif s_command == "max":
            res = numpy.max(val)
        else:
            raise ValueError(
                f"The command '{s_command.capitalize:}' is not defined in the program."
            )
        s_name = f"{s_command.capitalize():} of " + name_in_d
        if not (s_name in d_np_table.keys()):
            d_np_table[" inline_names"].append(s_name)
        d_np_table[s_name] = [
            float(res),
        ]
    return


def procedure_copy_to_clipboard(s_line: str, d_np_table: dict):
    l_name = s_line.strip().split()
    if len(l_name) < 1:
        l_name = d_np_table[" table_names"]
    l_val = []
    for i_name, name in enumerate(l_name):
        val, flag, name_in_d = take_val(name, d_np_table)
        if not flag:
            raise ValueError(
                f"The column '{name:}' should be defined in table to copy to clipboard"
            )
        l_val.append(val)
    ls_out = []
    ls_out.append("\t".join(l_name))
    for val in numpy.stack(l_val, axis=1):
        ls_out.append("\t".join([str(_) for _ in val]))
    s_out = "\n".join(ls_out)
    clipboard = QtWidgets.QApplication.clipboard()
    clipboard.setText(s_out)
    return


def procedure_column_sort(s_line: str, d_np_table: dict):
    if len(s_line.split()) < 1:
        raise ValueError(
            "For function 'sort' the sorting column should be defined"
        )

    name = s_line.split()[0]
    val, flag, name_in_d = take_val(name, d_np_table)
    if not flag:
        raise ValueError(
            f"The column '{name:}' should be defined in table to make sorting"
        )

    np_arg_sort = numpy.argsort(val)
    if "inv" in s_line.split()[1:]:
        np_arg_sort = np_arg_sort[::-1]

    for name in d_np_table[" table_names"]:
        d_np_table[name] = d_np_table[name][np_arg_sort]

    d_np_table[" table_colors"] = [
        transform_color(L_COLOR_TABLE[0]),
    ] * len(np_arg_sort)


def procedure_columns_int(s_line: str, d_np_table: dict):
    if len(s_line.split()) < 1:
        raise ValueError(
            "For function 'sort' the sorting column should be defined"
        )

    l_name = s_line.split()
    for name in l_name:
        val, flag, name_in_d = take_val(name, d_np_table)
        if not flag:
            raise ValueError(
                f"The column '{name:}' should be defined in table to make sorting"
            )
        d_np_table[name] = d_np_table[name].astype(int)


def procedure_columns_round(s_line: str, d_np_table: dict):
    if len(s_line.split()) < 1:
        raise ValueError(
            "For function 'sort' the sorting column should be defined"
        )

    l_name = s_line.split()
    for name in l_name:
        val, flag, name_in_d = take_val(name, d_np_table)
        if not flag:
            raise ValueError(
                f"The column '{name:}' should be defined in table to make sorting"
            )
        d_np_table[name] = numpy.round(d_np_table[name]).astype(int)


def procedure_column_del(s_line: str, d_np_table: dict):

    l_hh_more = s_line.split(L_OPERATION_IN[0])
    l_hh_less = s_line.split(L_OPERATION_IN[1])
    l_hh_equal = s_line.split(L_OPERATION_IN[2])
    flag_more = len(l_hh_more) == 2
    flag_less = len(l_hh_less) == 2
    flag_equal = len(l_hh_equal) == 2
    if len(l_hh_more) * len(l_hh_less) * len(l_hh_equal) != 2:
        raise ValueError(
            "Inequality function should be only one '>', '<' or '=='"
        )
    l_flag = [flag_more, flag_less, flag_equal]
    l_hh = [
        _
        for flag, _ in zip(l_flag, [l_hh_more, l_hh_less, l_hh_equal])
        if flag
    ][0]
    s_expr_right = l_hh[1].strip()
    s_expr_left = l_hh[0].strip()
    val_l, flag_l = estimate_expression(s_expr_left, d_np_table)
    val_r, flag_r = estimate_expression(s_expr_right, d_np_table)
    if not (flag_l and flag_r):
        raise ValueError("Given expression in 'del' function is not supported")

    if flag_more:
        np_flag = numpy.logical_not(val_l > val_r)
    elif flag_less:
        np_flag = numpy.logical_not(val_l < val_r)
    else:  # flag_equal
        np_flag = numpy.logical_not(val_l == val_r)
    for name in d_np_table[" table_names"]:
        d_np_table[name] = d_np_table[name][np_flag]
    if np_flag.size != len(d_np_table[" table_colors"]):
        d_np_table[" table_colors"] = [
            transform_color(L_COLOR[0]),
        ] * np_flag.size
    i_diff = 0
    for i_flag, flag in enumerate(np_flag):
        if not flag:
            del d_np_table[" table_colors"][i_flag - i_diff]
            i_diff += 1
    return


def procedure_print(s_line: str, d_np_table: dict):
    l_hh = s_line.split()
    l_name_d, l_val = [], []
    for name in l_hh:
        val, flag, name_d = take_val(name, d_np_table)
        if not flag:
            raise ValueError(
                f"The column '{name:}' should be defined in table to print"
            )
        l_name_d.append(name_d)
        l_val.append(val)
    l_command_d = [
        "",
    ] * len(l_name_d)
    for i_name_1, name in enumerate(d_np_table[" table_names"]):
        del d_np_table[name]
        if name in l_name_d:
            i_name = l_name_d.index(name)
            d_np_table[name] = l_val[i_name]
            l_command_d[i_name] = d_np_table[" table_commands"][i_name_1]
    d_np_table[" table_names"] = l_name_d
    d_np_table[" table_commands"] = l_command_d
    return


def procedure_column_mark(s_line: str, d_np_table: dict):

    l_hh_more = s_line.split(L_OPERATION_IN[0])
    l_hh_less = s_line.split(L_OPERATION_IN[1])
    l_hh_equal = s_line.split(L_OPERATION_IN[2])
    flag_more = len(l_hh_more) == 2
    flag_less = len(l_hh_less) == 2
    flag_equal = len(l_hh_equal) == 2
    if len(l_hh_more) * len(l_hh_less) * len(l_hh_equal) != 2:
        raise ValueError(
            "Inequality function should be only one '>', '<' or '=='"
        )
    l_flag = [flag_more, flag_less, flag_equal]
    l_hh = [
        _
        for flag, _ in zip(l_flag, [l_hh_more, l_hh_less, l_hh_equal])
        if flag
    ][0]
    s_expr_right = l_hh[1].strip()
    s_expr_left = l_hh[0].strip()
    val_l, flag_l = estimate_expression(s_expr_left, d_np_table)
    val_r, flag_r = estimate_expression(s_expr_right, d_np_table)
    if not (flag_l and flag_r):
        raise ValueError(
            "Given expression in 'mark' function is not supported"
        )

    if flag_more:
        np_flag = val_l > val_r
    elif flag_less:
        np_flag = val_l < val_r
    else:  # flag_equal
        np_flag = val_l == val_r

    if np_flag.size != len(d_np_table[" table_colors"]):
        d_np_table[" table_colors"] = [
            transform_color(L_COLOR[0]),
        ] * np_flag.size
    for i_flag, flag in enumerate(np_flag):
        if flag:
            d_np_table[" table_colors"][i_flag] = transform_color(L_COLOR[2])
    return


def procedure_equiv_hkl(s_line: str, d_np_table: dict):
    """Add to the table equivalent hkl indices.
    It removes all other columns from the table

    """
    l_necessary = ["H", "K", "L"]
    flag = all([name in d_np_table[" table_names"] for name in l_necessary])
    if not flag:
        raise ValueError("The table does not contain columns H, K, L")
    np_hkl = numpy.stack(
        [d_np_table["H"], d_np_table["K"], d_np_table["L"]], axis=1
    )

    s_command = s_line.strip().split()[0].lower()

    func_equiv = choose_func_equiv(s_command)

    l_hkl = []
    for hkl in np_hkl:
        l_hkl.extend(func_equiv(hkl))
    np_hkl_equiv = numpy.array(l_hkl, dtype=np_hkl.dtype)
    hkl_equiv = numpy.unique(np_hkl_equiv, axis=0)
    d_command = {"H": "", "K": "", "L": ""}
    for name, s_command in zip(
        d_np_table[" table_names"], d_np_table[" table_commands"]
    ):
        del d_np_table[name]
        if name in ["H", "K", "L"]:
            d_command[name] = s_command

    d_np_table[" table_names"] = ["H", "K", "L"]
    d_np_table[" table_commands"] = [
        d_command["H"],
        d_command["K"],
        d_command["L"],
    ]
    d_np_table["H"] = hkl_equiv[:, 0]
    d_np_table["K"] = hkl_equiv[:, 1]
    d_np_table["L"] = hkl_equiv[:, 2]
    procedure_group_hkl(s_line, d_np_table)
    return


def procedure_group_hkl(s_line: str, d_np_table: dict):
    l_necessary_table = ["H", "K", "L"]
    flag_table = all(
        [name in d_np_table[" table_names"] for name in l_necessary_table]
    )
    if not flag_table:
        raise ValueError(
            "The table does not contain columns "
            + ", ".join(l_necessary_table)
        )

    s_command = s_line.strip().split()[0].lower()
    func_equiv = choose_func_equiv(s_command)
    calc_flag = lambda hkl1, hkl2: chec_equiv_hkl(hkl1, hkl2, func_equiv)

    np_hkl = numpy.stack(
        [d_np_table["H"], d_np_table["K"], d_np_table["L"]], axis=1
    )

    ll_ind_equiv = group_by_hkl(np_hkl, calc_flag)
    l_arg = []
    l_table_colors = []
    for i_c, l_inx_equiv in enumerate(ll_ind_equiv):
        l_arg.extend(l_inx_equiv)
        colour = transform_color(L_COLOR_TABLE[i_c % 2])
        l_table_colors.extend(
            [
                colour,
            ]
            * len(l_inx_equiv)
        )

    np_arg = numpy.array(l_arg, dtype=int)
    for name in d_np_table[" table_names"]:
        d_np_table[name] = d_np_table[name][l_arg]
    d_np_table[" table_colors"] = l_table_colors


def procedure_aver_hkl(s_line: str, d_np_table: dict):
    l_necessary_table = ["H", "K", "L"]
    flag_table = all(
        [name in d_np_table[" table_names"] for name in l_necessary_table]
    )
    if not flag_table:
        raise ValueError(
            "The table does not contain columns "
            + ", ".join(l_necessary_table)
        )

    l_iint = ["Intensity", "sIntensity"]
    flag_iint = all([name in d_np_table[" table_names"] for name in l_iint])

    l_fsq = ["Fsq", "sFsq"]
    flag_fsq = all([name in d_np_table[" table_names"] for name in l_fsq])
    if not flag_iint and not flag_fsq:
        raise ValueError(
            "The table does not contain columns "
            + ", ".join(l_iint)
            + " or "
            + ", ".join(l_fsq)
        )

    s_command = s_line.strip().split()[0].lower()
    func_equiv = choose_func_equiv(s_command)
    calc_flag = lambda hkl1, hkl2: chec_equiv_hkl(hkl1, hkl2, func_equiv)

    np_hkl = numpy.stack(
        [d_np_table["H"], d_np_table["K"], d_np_table["L"]], axis=1
    )

    ll_ind_equiv = group_by_hkl(np_hkl, calc_flag)

    l_hkl_new, l_aver_iint, l_aver_fsq = [], [], []
    r_factor_iint_1, r_factor_fsq_1 = 0.0, 0.0
    r_factor_iint_2, r_factor_fsq_2 = 0.0, 0.0
    for l_inx_equiv in ll_ind_equiv:
        l_hkl_new.append(np_hkl[l_inx_equiv[0], :])
        np_arg = numpy.array(l_inx_equiv, dtype=int)
        if flag_iint:
            np_iint = d_np_table["Intensity"][np_arg]
            np_siint = d_np_table["sIntensity"][np_arg]
            aver_iint, saver_iint, af_aver_iint = calc_aver_saver(
                np_iint, np_siint
            )
            l_aver_iint.append((aver_iint, saver_iint, af_aver_iint))

            diff_abs = numpy.abs(np_iint - aver_iint)
            diff_abs[diff_abs < saver_iint] = saver_iint
            r_factor_iint_1 += numpy.sum(diff_abs)
            r_factor_iint_2 += numpy.sum(np_iint)
        if flag_fsq:
            np_fsq = d_np_table["Fsq"][np_arg]
            np_sfsq = d_np_table["sFsq"][np_arg]
            aver_fsq, saver_fsq, af_aver_fsq = calc_aver_saver(np_fsq, np_sfsq)
            l_aver_fsq.append((aver_fsq, saver_fsq, af_aver_fsq))

            diff_abs = numpy.abs(np_fsq - aver_fsq)
            diff_abs[diff_abs < saver_fsq] = saver_fsq
            r_factor_fsq_1 += numpy.sum(diff_abs)
            r_factor_fsq_2 += numpy.sum(np_fsq)

    for name in d_np_table[" table_names"]:
        del d_np_table[name]
    d_np_table[" table_names"] = [
        "H",
        "K",
        "L",
    ]
    d_np_table[" table_commands"] = ["", "", "", "", "", "", ""]
    color_norm = transform_color(L_COLOR[0])
    color_good = transform_color(L_COLOR[2])
    color_bad = transform_color(L_COLOR[3])
    d_np_table["H"] = numpy.array(
        [_[0] for _ in l_hkl_new], dtype=np_hkl.dtype
    )
    d_np_table["K"] = numpy.array(
        [_[1] for _ in l_hkl_new], dtype=np_hkl.dtype
    )
    d_np_table["L"] = numpy.array(
        [_[2] for _ in l_hkl_new], dtype=np_hkl.dtype
    )
    l_flag_good = [
        True,
    ] * len(l_hkl_new)
    l_flag_bad = [
        False,
    ] * len(l_hkl_new)
    d_np_table[" table_colors"] = []
    if flag_iint:
        d_np_table[" table_names"].extend(
            ["Intensity", "sIntensity", "AF_Intensity"]
        )
        d_np_table[" table_commands"].extend(["", "", ""])
        d_np_table["Intensity"] = numpy.array(
            [_[0] for _ in l_aver_iint], dtype=float
        )
        d_np_table["sIntensity"] = numpy.array(
            [_[1] for _ in l_aver_iint], dtype=float
        )
        d_np_table["AF_Intensity"] = numpy.array(
            [_[2] for _ in l_aver_iint], dtype=float
        )
        l_flag_bad = [
            _[2] > 20 or _2 for _, _2 in zip(l_aver_iint, l_flag_bad)
        ]
        l_flag_good = [
            _[2] < 5 and _2 for _, _2 in zip(l_aver_iint, l_flag_good)
        ]
        if r_factor_iint_2 > 0:
            r_factor_iint = 100 * r_factor_iint_1 / r_factor_iint_2
            s_name = "Agreement Factor for Intensity"
            if not (s_name in d_np_table[" inline_names"]):
                d_np_table[" inline_names"].append(s_name)
            d_np_table[s_name] = [
                r_factor_iint,
            ]
    if flag_fsq:
        d_np_table[" table_names"].extend(["Fsq", "sFsq", "AF_Fsq"])
        d_np_table[" table_commands"].extend(["", "", ""])
        d_np_table["Fsq"] = numpy.array(
            [_[0] for _ in l_aver_fsq], dtype=float
        )
        d_np_table["sFsq"] = numpy.array(
            [_[1] for _ in l_aver_fsq], dtype=float
        )
        d_np_table["AF_Fsq"] = numpy.array(
            [_[2] for _ in l_aver_fsq], dtype=float
        )
        l_flag_bad = [_[2] > 20 or _2 for _, _2 in zip(l_aver_fsq, l_flag_bad)]
        l_flag_good = [
            _[2] < 5 and _2 for _, _2 in zip(l_aver_fsq, l_flag_good)
        ]
        if r_factor_fsq_2 > 0:
            r_factor_fsq = 100 * r_factor_fsq_1 / r_factor_fsq_2
            s_name = "Agreement Factor for Fsq"
            if not (s_name in d_np_table[" inline_names"]):
                d_np_table[" inline_names"].append(s_name)
            d_np_table[s_name] = [
                r_factor_fsq,
            ]

    for flag_good, flag_bad in zip(l_flag_good, l_flag_bad):
        if flag_bad:
            d_np_table[" table_colors"].append(color_bad)
        elif flag_good:
            d_np_table[" table_colors"].append(color_good)
        else:
            d_np_table[" table_colors"].append(color_norm)


def calc_aver_saver(np_val, np_sval):
    np_sval2 = np_sval**2
    np_sval2_inv = 1 / np_sval2
    np_val_inv = np_val * np_sval2_inv
    aver_val = numpy.sum(np_val_inv) / numpy.sum(np_sval2_inv)
    saver_val1 = 1 / numpy.sqrt(numpy.sum(np_sval2_inv))
    saver_val2 = numpy.std(np_val)
    saver_val = max([saver_val1, saver_val2])
    abs_diff = numpy.abs(np_val - aver_val)
    abs_diff[abs_diff < saver_val] = saver_val
    r_factor = 100 * numpy.sum(abs_diff) / numpy.sum(numpy.abs(np_val))
    return aver_val, saver_val, r_factor


def chec_equiv_hkl(hkl1, hkl2, func_equiv):
    l_hkl2 = func_equiv(hkl2)
    return tuple(hkl1) in l_hkl2


def procedure_calc(s_line: str, d_np_table: dict):

    s_name = s_line.strip().split()[0].lower()
    l_necessary_table = ["H", "K", "L"]
    l_necessary_inline = ["a", "b", "c", "alpha", "beta", "gamma"]
    flag_hkl_ucp = True
    if s_name == "sthovl":
        pass
    elif s_name == "2theta":
        l_necessary_inline_3 = [
            "Wavelength",
        ]
    elif s_name.replace("_", "").startswith("chisq"):
        flag_hkl_ucp = False
        l_necessary_table = []
        l_necessary_inline = []
        l_name = s_line.strip().split()[1:]
        if len(l_name) < 2 or len(l_name) > 3:
            raise ValueError(
                "For '{s_name:}' the name of y_mod, y_exp, and y_sigma should be given"
            )
    else:
        return

    flag_table = all(
        [name in d_np_table[" table_names"] for name in l_necessary_table]
    )
    flag_inline = all(
        [name in d_np_table[" inline_names"] for name in l_necessary_inline]
    )

    if not flag_table:
        raise ValueError(
            "The table does not contain columns "
            + ", ".join(l_necessary_table)
        )

    if not flag_inline:
        calc_unit_cell_by_ub(d_np_table)
    if flag_hkl_ucp:
        np_hkl = numpy.stack(
            [d_np_table["H"], d_np_table["K"], d_np_table["L"]], axis=0
        )
        unit_cell_parameters = numpy.array(
            [d_np_table[name] for name in l_necessary_inline], dtype=float
        )
        unit_cell_parameters[3:] = numpy.radians(unit_cell_parameters[3:])
        np_sthovl = calc_sthovl_by_unit_cell_parameters(
            np_hkl, unit_cell_parameters
        )
    if s_name == "sthovl":
        if not ("sthovl" in d_np_table[" table_names"]):
            d_np_table[" table_names"].append("sthovl")
            d_np_table[" table_commands"].append("")
        d_np_table["sthovl"] = np_sthovl
    elif s_name == "2theta":
        flag_inline = all(
            [
                name in d_np_table[" inline_names"]
                for name in l_necessary_inline_3
            ]
        )
        if not flag_inline:
            raise ValueError("The 'Wavelength' should be defined")
        hh = np_sthovl * d_np_table["Wavelength"]
        hh[hh >= 1.0] = 0.0
        np_tth = 2 * numpy.degrees(numpy.arcsin(hh))
        if not ("2Theta" in d_np_table[" table_names"]):
            d_np_table[" table_names"].append("2Theta")
            d_np_table[" table_commands"].append("")
        d_np_table["2Theta"] = np_tth
    elif s_name.replace("_", "").startswith("chisq"):
        np_y_mod, flag_y_mod, name_y_mod = take_val(l_name[0], d_np_table)
        if not flag_y_mod:
            raise ValueError(f"The column {l_name[0]:} is not defined")
        np_y_exp, flag_y_exp, name_y_exp = take_val(l_name[1], d_np_table)
        if not flag_y_exp:
            raise ValueError(f"The column {l_name[1]:} is not defined")
        if len(l_name) == 3:
            np_y_sigma, flag_y_sigma, name_y_sigma = take_val(
                l_name[2], d_np_table
            )
            if not flag_y_exp:
                raise ValueError(f"The column {l_name[2]:} is not defined")
        else:
            np_y_sigma = numpy.ones_like(np_y_mod)

        np_chisq = numpy.sum(
            numpy.power((np_y_mod - np_y_exp) / np_y_sigma, 2)
        )
        if s_name.replace("_", "") == "chisq":
            s_name = f"ChiSq for {name_y_exp:}"
        else:  # chi_sq per n
            s_name = f"ChiSq per N for {name_y_exp:}"
            np_chisq = np_chisq / np_y_mod.size
        if not (s_name in d_np_table[" inline_names"]):
            d_np_table[" inline_names"].append(s_name)
        d_np_table[s_name] = [
            float(np_chisq),
        ]
    return


def procedure_generate_hkl(s_line: str, d_np_table: dict):
    s_name = s_line.strip().split()
    if s_name[0].lower() == "sthovl":
        sthovl_min, sthovl_max = float(s_name[1]), float(s_name[2])
    elif s_name[0].lower() == "theta":
        sthovl_min, sthovl_max = float(s_name[1]), float(s_name[2])
        if not "Wavelength" in d_np_table[" inline_names"]:
            raise ValueError("The parameter 'Wavelength' should be defined")
        sthovl_min = (
            numpy.sin(numpy.radians(sthovl_min)) / d_np_table["Wavelength"]
        )
        sthovl_max = (
            numpy.sin(numpy.radians(sthovl_max)) / d_np_table["Wavelength"]
        )
    elif s_name[0].lower() == "2theta":  # 2theta
        sthovl_min, sthovl_max = float(s_name[1]), float(s_name[2])
        if not "Wavelength" in d_np_table[" inline_names"]:
            raise ValueError("The parameter 'Wavelength' should be defined")
        sthovl_min = (
            numpy.sin(0.5 * numpy.radians(sthovl_min))
            / d_np_table["Wavelength"]
        )
        sthovl_max = (
            numpy.sin(0.5 * numpy.radians(sthovl_max))
            / d_np_table["Wavelength"]
        )
    else:  # 2theta
        sthovl_min, sthovl_max = (
            float(s_name[0]),
            float(s_name[1]),
        )
        if not "Wavelength" in d_np_table[" inline_names"]:
            raise ValueError("The parameter 'Wavelength' should be defined")
        sthovl_min = (
            numpy.sin(0.5 * numpy.radians(sthovl_min))
            / d_np_table["Wavelength"]
        )
        sthovl_max = (
            numpy.sin(0.5 * numpy.radians(sthovl_max))
            / d_np_table["Wavelength"]
        )

    l_necessary_inline = ["a", "b", "c", "alpha", "beta", "gamma"]
    flag_inline = all(
        [name in d_np_table[" inline_names"] for name in l_necessary_inline]
    )

    if not flag_inline:
        calc_unit_cell_by_ub(d_np_table)

    unit_cell_parameters = numpy.array(
        [d_np_table[name] for name in l_necessary_inline], dtype=float
    )
    unit_cell_parameters[3:] = numpy.radians(unit_cell_parameters[3:])

    np_hkl = calc_index_hkl_in_range(
        sthovl_min, sthovl_max, unit_cell_parameters
    )
    sthovl = calc_sthovl_by_unit_cell_parameters(np_hkl, unit_cell_parameters)
    for name in d_np_table[" table_names"]:
        del d_np_table[name]
    d_np_table[" table_names"] = ["H", "K", "L", "sthovl"]
    d_np_table[" table_commands"] = ["", "", "", ""]
    d_np_table["H"] = np_hkl[0, :]
    d_np_table["K"] = np_hkl[1, :]
    d_np_table["L"] = np_hkl[2, :]
    d_np_table["sthovl"] = sthovl
    d_np_table[" table_colors"] = [
        transform_color(L_COLOR_TABLE[0]),
    ] * sthovl.size
    if "Wavelength" in d_np_table[" inline_names"]:
        hh = sthovl * d_np_table["Wavelength"]
        hh[hh >= 1.0] = 0.0
        np_tth = 2 * numpy.degrees(numpy.arcsin(hh))
        d_np_table[" table_names"].append("2Theta")
        d_np_table[" table_commands"].append("")
        d_np_table["2Theta"] = np_tth
    return


def procedure_column(s_line: str, d_np_table: dict):
    s_name = s_line.strip().split()
    table_name = transform_name_to_table_name(s_name[0])
    l_param = [float(hh) for hh in (" ".join(s_name[1:])).split()]

    if (
        len(d_np_table[" table_names"]) == 1
        and table_name in d_np_table[" table_names"]
    ):
        d_np_table[" table_names"] = []
        d_np_table[" table_commands"] = []
        del d_np_table[table_name]

    if len(d_np_table[" table_names"]) > 0:
        start, end = l_param[0], l_param[1]
        num = d_np_table[d_np_table[" table_names"][0]].size
        pass
    else:
        start, step, end_hh = l_param[0], l_param[1], l_param[2]
        num = int(numpy.round((end_hh - start) / step, 0) + 1)
        end = start + (num - 1) * step

    np_val = numpy.linspace(start, end, num=num, endpoint=True)
    if not (table_name in d_np_table[" table_names"]):
        d_np_table[" table_names"].append(table_name)
        d_np_table[" table_commands"].append("")
    d_np_table[table_name] = np_val
    return


def procedure_convert_to_int_format(s_line: str, d_np_table: dict):
    l_necessary_table = [
        "H",
        "K",
        "L",
        "Intensity",
        "sIntensity",
        "Theta",
        "Phi",
        "Chi",
        "Omega",
    ]
    flag_table = all(
        [name in d_np_table[" table_names"] for name in l_necessary_table]
    )
    # flag_inline = all([name in d_np_table[" inline_names"] for name in l_necessary_inline])
    if not flag_table:
        raise ValueError(
            "The table does not contain columns "
            + ", ".join(l_necessary_table)
        )
    if "Wavelength" in d_np_table[" inline_names"]:
        wavelength = d_np_table["Wavelength"]
    else:
        wavelength = 0.90
    np_hkl = numpy.stack(
        [d_np_table["H"], d_np_table["K"], d_np_table["L"]], axis=0
    )
    np_q = numpy.mod(np_hkl, 1)
    np_hkl_int = numpy.round(np_hkl - np_q).astype(int)
    np_q_unique, np_inverse = numpy.unique(np_q, axis=1, return_inverse=True)
    flag_nucl = numpy.all(np_q_unique == 0.0)

    np_int = d_np_table["Intensity"]
    np_sint = d_np_table["sIntensity"]
    np_th = d_np_table["Theta"]
    np_ph = d_np_table["Phi"]
    np_ch = d_np_table["Chi"]
    np_om = d_np_table["Omega"]

    d_np_table.clear()
    d_np_table[" comments"] = []
    d_np_table[" expressions"] = []
    d_np_table[" inline_names"] = []
    d_np_table[" table_colors"] = []
    s_comment = ""  # ui_setting.get_comment_character()

    d_np_table[" table_names"] = []
    d_np_table[" table_commands"] = []
    d_np_table[" comments"].append(f"{s_comment:}TITLE CrysPy")
    if flag_nucl:
        d_np_table[" comments"].append(f"{s_comment:}(3i4,2F14.4,i5,4f8.2)")
    else:
        d_np_table[" comments"].append(f"{s_comment:}(3i4,i5,2F14.4,i5,4f8.2)")
    d_np_table[" comments"].append(f"{s_comment:}{wavelength:9.5f}   0   0")
    n_q = np_q_unique.shape[1]
    if not flag_nucl:
        d_np_table[" comments"].append(
            f"{s_comment:}{n_q:6}  ! Number of Propagation vectors (star_k)"
        )

    d_np_table["H"] = np_hkl_int[0, :]
    d_np_table["K"] = np_hkl_int[1, :]
    d_np_table["L"] = np_hkl_int[2, :]
    d_np_table["Q"] = np_inverse
    d_np_table["Intensity"] = np_int
    d_np_table["sIntensity"] = np_sint
    d_np_table["Theta"] = np_th
    d_np_table["Phi"] = np_ph
    d_np_table["Chi"] = np_ch
    d_np_table["Omega"] = np_om
    if not flag_nucl:
        for iq, q in enumerate(np_q_unique.T):
            d_np_table[" comments"].append(
                f"{s_comment:}{iq+1:4}{q[0]:10.4f}{q[1]:10.4f}{q[2]:10.4f}"
            )
    for hkl, qq, iint, siint, th, om, ch, ph in zip(
        np_hkl_int.T, np_inverse, np_int, np_sint, np_th, np_ph, np_ch, np_om
    ):
        s_hkl = f"{hkl[0]:4}{hkl[1]:4}{hkl[2]:4}"
        if flag_nucl:
            s_q = ""
        else:
            s_q = f"{qq + 1: 5}"
        s_int = f"{iint:14.4f}{siint:14.4f}{1:5}"
        s_angles = f"{th:8.2f}{om:8.2f}{ch:8.2f}{ph:8.2f}"
        d_np_table[" comments"].append(
            s_comment + s_hkl + s_q + s_int + s_angles
        )
    return


def calc_unit_cell_by_ub(d_np_table):
    l_necessary_inline = ["a", "b", "c", "alpha", "beta", "gamma"]
    l_necessary_inline_2 = [
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
    flag_inline_2 = all(
        [name in d_np_table[" inline_names"] for name in l_necessary_inline_2]
    )
    if not flag_inline_2:
        raise ValueError(
            "The following parameters should be defined: "
            + ", ".join(l_necessary_inline)
        )
    else:
        m_ub = numpy.array(
            [float(d_np_table[name]) for name in l_necessary_inline_2],
            dtype=float,
        )
        unit_cell_parameters, m_u = calc_unit_cell_parameters_and_u_by_ub(m_ub)
    d_np_table[" inline_names"].extend(l_necessary_inline)
    for i_name, name in enumerate(l_necessary_inline):
        d_np_table[name] = [
            float(unit_cell_parameters[i_name]),
        ]
        if i_name in [3, 4, 5]:
            d_np_table[name] = [
                float(numpy.degrees(d_np_table[name])),
            ]
    return


def choose_func_equiv(s_command: str):
    if s_command.startswith("f"):
        func_equiv = equiv_friedel
    elif s_command.startswith("o"):
        func_equiv = equiv_orto
    elif s_command.startswith("t"):
        func_equiv = equiv_tetra
    elif s_command.startswith("h"):
        func_equiv = equiv_hex
    elif s_command.startswith("c"):
        func_equiv = equiv_cubic
    else:
        func_equiv = lambda x: [
            x,
        ]
    return func_equiv


def check_same_hkl(np_hkl_1, np_hkl_2):
    return numpy.all(np_hkl_1 == np_hkl_2)


def equiv_friedel(hkl):
    l_hkl = [
        (hkl[0], hkl[1], hkl[2]),
        (-hkl[0], -hkl[1], -hkl[2]),
    ]
    return l_hkl


def check_friedel(np_hkl_1, np_hkl_2):
    l_hkl = equiv_friedel(np_hkl_2)
    return np_hkl_1 in l_hkl


def equiv_orto(hkl):
    l_hkl = [
        (hkl[0], hkl[1], hkl[2]),
        (-hkl[0], -hkl[1], -hkl[2]),
        (-hkl[0], hkl[1], hkl[2]),
        (hkl[0], -hkl[1], hkl[2]),
        (hkl[0], hkl[1], -hkl[2]),
        (-hkl[0], -hkl[1], hkl[2]),
        (hkl[0], -hkl[1], -hkl[2]),
        (-hkl[0], hkl[1], -hkl[2]),
    ]
    return l_hkl


def check_ortho(np_hkl_1, np_hkl_2):
    l_hkl = equiv_orto(np_hkl_2)
    return np_hkl_1 in l_hkl


def equiv_tetra(hkl):
    l_hkl = [
        (hkl[0], hkl[1], hkl[2]),
        (-hkl[0], -hkl[1], -hkl[2]),
        (-hkl[0], hkl[1], hkl[2]),
        (hkl[0], -hkl[1], hkl[2]),
        (hkl[0], hkl[1], -hkl[2]),
        (-hkl[0], -hkl[1], hkl[2]),
        (hkl[0], -hkl[1], -hkl[2]),
        (-hkl[0], hkl[1], -hkl[2]),
        (hkl[1], hkl[0], hkl[2]),
        (-hkl[1], -hkl[0], -hkl[2]),
        (-hkl[1], hkl[0], hkl[2]),
        (hkl[1], -hkl[0], hkl[2]),
        (hkl[1], hkl[0], -hkl[2]),
        (-hkl[1], -hkl[0], hkl[2]),
        (hkl[1], -hkl[0], -hkl[2]),
        (-hkl[1], hkl[0], -hkl[2]),
    ]
    return l_hkl


def check_tetra(np_hkl_1, np_hkl_2):
    l_hkl = equiv_orto(np_hkl_2)
    return np_hkl_1 in l_hkl


def equiv_hex(hkl):
    hh = -(hkl[0] + hkl[1])
    l_hkl = [
        (hkl[0], hkl[1], hkl[2]),
        (hkl[1], hh, hkl[2]),
        (hh, hkl[0], hkl[2]),
        (hkl[0], hkl[1], -hkl[2]),
        (hkl[1], hh, -hkl[2]),
        (hh, hkl[0], -hkl[2]),
        (-hkl[0], -hkl[1], -hkl[2]),
        (-hkl[1], -hh, -hkl[2]),
        (-hh, -hkl[0], -hkl[2]),
        (-hkl[0], -hkl[1], hkl[2]),
        (-hkl[1], -hh, hkl[2]),
        (-hh, -hkl[0], hkl[2]),
    ]
    return l_hkl


def check_hex(np_hkl_1, np_hkl_2):
    l_hkl = equiv_hex(np_hkl_2)
    return (np_hkl_1[0], np_hkl_1[1], np_hkl_1[2]) in l_hkl


def equiv_cubic(hkl):
    l_hkl = [
        (hkl[0], hkl[1], hkl[2]),
        (-hkl[0], -hkl[1], -hkl[2]),
        (-hkl[0], hkl[1], hkl[2]),
        (hkl[0], -hkl[1], hkl[2]),
        (hkl[0], hkl[1], -hkl[2]),
        (-hkl[0], -hkl[1], hkl[2]),
        (hkl[0], -hkl[1], -hkl[2]),
        (-hkl[0], hkl[1], -hkl[2]),
        (hkl[1], hkl[0], hkl[2]),
        (-hkl[1], -hkl[0], -hkl[2]),
        (-hkl[1], hkl[0], hkl[2]),
        (hkl[1], -hkl[0], hkl[2]),
        (hkl[1], hkl[0], -hkl[2]),
        (-hkl[1], -hkl[0], hkl[2]),
        (hkl[1], -hkl[0], -hkl[2]),
        (-hkl[1], hkl[0], -hkl[2]),
        (hkl[2], hkl[1], hkl[0]),
        (-hkl[2], -hkl[1], -hkl[0]),
        (-hkl[2], hkl[1], hkl[0]),
        (hkl[2], -hkl[1], hkl[0]),
        (hkl[2], hkl[1], -hkl[0]),
        (-hkl[2], -hkl[1], hkl[0]),
        (hkl[2], -hkl[1], -hkl[0]),
        (-hkl[2], hkl[1], -hkl[0]),
        (hkl[0], hkl[2], hkl[1]),
        (-hkl[0], -hkl[2], -hkl[1]),
        (-hkl[0], hkl[2], hkl[1]),
        (hkl[0], -hkl[2], hkl[1]),
        (hkl[0], hkl[2], -hkl[1]),
        (-hkl[0], -hkl[2], hkl[1]),
        (hkl[0], -hkl[2], -hkl[1]),
        (-hkl[0], hkl[2], -hkl[1]),
    ]
    return l_hkl


def check_cubic(np_hkl_1, np_hkl_2):
    l_hkl = equiv_cubic(np_hkl_2)
    return (np_hkl_1[0], np_hkl_1[1], np_hkl_1[2]) in l_hkl


def estimate_expression(s_expression: str, d_np_table: dict):
    flag = True
    l_val_sum = []
    for f_0 in s_expression.split(L_OPERATION[0]):
        l_val_diff = []
        for f_1 in f_0.split(L_OPERATION[1]):
            l_val_mult = []
            for f_2 in f_1.split(L_OPERATION[2]):
                l_val_dev = []
                for f_3 in f_2.split(L_OPERATION[3]):
                    l_val_power = []
                    for f_4 in f_3.split(L_OPERATION[4]):
                        l_val_mod = []
                        for f_5 in f_4.split(L_OPERATION[5]):
                            val_mod, flag, name_in_d = take_val(
                                f_5, d_np_table
                            )
                            if not flag:
                                return None, flag
                            l_val_mod.append(val_mod)
                        l_val_mod_inv = l_val_mod[::-1]
                        val_power = sequent_func(
                            *l_val_mod_inv, func=lambda x, y: y % x
                        )
                        # val_power, flag, name_in_d = take_val(f_4, d_np_table)
                        # if not flag:
                        #     return None, flag
                        l_val_power.append(val_power)
                    l_val_power_inv = l_val_power[::-1]
                    val_dev = sequent_func(
                        *l_val_power_inv, func=lambda x, y: x**y
                    )
                    l_val_dev.append(val_dev)
                val_mult = sequent_func(*l_val_dev, func=lambda x, y: x / y)
                l_val_mult.append(val_mult)
            val_diff = sequent_func(*l_val_mult, func=lambda x, y: x * y)
            l_val_diff.append(val_diff)
        val_sum = sequent_func(*l_val_diff, func=lambda x, y: x - y)
        l_val_sum.append(val_sum)
    val = sequent_func(*l_val_sum, func=lambda x, y: x + y)
    return val, flag


def sequent_func(val, *val2, func: callable = lambda x, y: x + y):
    if len(val2) == 0:
        return val
    return sequent_func(func(val, val2[0]), *val2[1:], func=func)


def take_val(s_input: str, d_np_table: dict):
    s_val = s_input.strip()
    if s_val == "":
        return 0, True, ""
    l_name_inline = d_np_table[" inline_names"]
    l_name_table = d_np_table[" table_names"]
    l_command_table = d_np_table[" table_commands"]

    s_val_lower = s_val.lower()
    l_name_all = l_name_table + l_name_inline
    l_name_all_lower = [_.lower() for _ in l_name_all]
    l_command_lower = [_.lower() for _ in l_command_table]

    if s_val_lower in l_name_all_lower:
        name_in_d = l_name_all[l_name_all_lower.index(s_val_lower)]
        res = d_np_table[name_in_d]
        return res, True, name_in_d
    elif s_val_lower in l_command_lower:
        name_in_d = l_name_table[l_command_lower.index(s_val_lower)]
        res = d_np_table[name_in_d]
        return res, True, name_in_d
    try:
        res = float(s_val_lower)
        return res, True, ""
    except ValueError:
        pass
    return 0, False, ""


def group_by_hkl(l_hkl, func_equivalent):
    l_group_hkl_ind = []
    l_ind = list(range(len(l_hkl)))
    flag_new_equiv = True
    num = len(l_hkl)
    for i_hkl, hkl_1 in enumerate(l_hkl):
        if i_hkl in l_ind:
            l_ind_equiv = []
            for i_hkl_2 in range(i_hkl, num):
                if i_hkl_2 in l_ind:
                    flag = func_equivalent(hkl_1, l_hkl[i_hkl_2])
                    if flag:
                        l_ind_equiv.append(i_hkl_2)
                        l_ind.remove(i_hkl_2)
            l_group_hkl_ind.append(l_ind_equiv)
    return l_group_hkl_ind

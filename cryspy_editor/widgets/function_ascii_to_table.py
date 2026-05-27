import numpy
import cryspy_editor.widgets.ui_setting as ui_setting

from cryspy_editor.widgets.function_basis import find_common_prefix, transform_string_to_vals, take_common_type
from cryspy_editor.widgets.function_dictionary import transform_name_to_table_name, transform_name_to_inline_name, get_d_known_formats
from cryspy_editor.widgets.function_table_operation import L_ACTION_NAME


D_CFL_NAMES = {
    "cell": (6, "Unit Cell"),
    "ubmat": (9, "UB-matrix"),
    "wave": (1, "Wavelength")
}


def take_table_names_cif_loop(l_line: list[str]):
    l_name_long = []
    for i_line, line in enumerate(l_line) :
        if line.startswith("_"):
            l_name_long.append(line.strip().lower())
        else:
            ind_miss = i_line +1
            break
    common_prefix = find_common_prefix(l_name_long)
    l_name = [name[len(common_prefix): ] for name in l_name_long]
    for i_name, name in enumerate(l_name):
        if name == "":
            l_name[i_name] = f"Column-{i_name+1:}"
    return l_name, ind_miss


def transform_cfl_to_inline(l_line: list[str]):
    S_COMMENT = ui_setting.get_comment_character()
    i_line = 0
    l_hh = l_line[i_line].split(S_COMMENT)[0].strip().split()
    cfl_name = l_hh[0].lower()
    l_cfl_name = D_CFL_NAMES.keys()
    if not (cfl_name in l_cfl_name):
        raise ValueError
    n_val, formal_name = D_CFL_NAMES[cfl_name]
    l_res = l_hh[1:]
    while len(l_res) <  n_val:
        i_line += 1
        l_hh=l_line[i_line].split(S_COMMENT)[0].strip().split()
        l_res.extend(l_hh)
    line_out = formal_name + " : " + " ".join(l_res[:n_val])
    return line_out, i_line

def take_comment_inline_table_lines(l_line: list[str]):
    l_comment = []
    l_inline = []
    l_expression = []
    l_table = []
    ind_miss_until = -1
    S_COMMENT = ui_setting.get_comment_character()
    for i_line, line in enumerate(l_line):
        if i_line <= ind_miss_until:
            continue
        h_line = line.strip()

        l_h_line = h_line.split(S_COMMENT)
        if len(l_h_line) > 1:
            l_comment.append(S_COMMENT + S_COMMENT.join(l_h_line[1:]))
        h_line = l_h_line[0]#.replace("==", "=") #.replace("=",":")

        if h_line == '':
            continue


        n_equal = h_line.count(':')
        flag_inline = n_equal != 0
        flag_table = n_equal == 0 
        flag_expression = ((h_line.count("=") == 1) or (h_line.strip().split()[0].lower() in L_ACTION_NAME)) and (n_equal == 0)
        
        l_cfl_word = D_CFL_NAMES.keys()

        flag_cfl = (h_line.split()[0].lower() in l_cfl_word) and (n_equal == 0) # and (len(h_line.split())>1)
        flag_cif_inline = h_line.startswith("_") and len(h_line.split()) == 2
        flag_cif_loop = h_line.lower().startswith("loop_")
        
        if flag_expression:
            line_out = h_line
            l_expression.append(line_out)
        elif flag_cif_loop:
            l_name_table, ind_line = take_table_names_cif_loop(l_line[i_line+1:])
            ind_miss_until = ind_line+i_line-1
            line_out = " ".join(l_name_table)
            l_table.append(line_out)
        elif flag_cif_inline:
            l_hh = h_line.split()
            if len(l_hh[0]) != 1:
                line_out = l_hh[0][1:] + " : " + l_hh[1]
                l_inline.append(line_out)
        elif flag_cfl:
            l_hh = h_line.split()
            line_out, ind_line = transform_cfl_to_inline(l_line[i_line:])
            ind_miss_until = ind_line + i_line
            l_inline.append(line_out)
        elif flag_inline:
            l_inline.append(h_line)
        elif flag_table:
            l_table.append(h_line)
        
    return l_comment, l_inline, l_expression, l_table

def upload_d_np_table_by_l_inline(d_np_table: dict, l_inline: list[str]):
    d_np_table[" inline_names"] = []
    for line in l_inline:
        name_inline = line.split(":")[0].strip()
        s_val_inline = line.split(":")[1]
        name_inline = transform_name_to_inline_name(name_inline)
        l_val =  transform_string_to_vals(s_val_inline)
        if not(name_inline in d_np_table[" inline_names"]):
            d_np_table[" inline_names"].append(name_inline)
        d_np_table[name_inline] = l_val 


def upload_d_np_table_by_l_expression(d_np_table: dict, l_expression: list[str]):
    d_np_table[" expressions"] = l_expression


def transform_table_head_to_names_commands(l_table_head: list[str]):
    l_table_name, l_table_commands = [], [] 
    for val_head in l_table_head:
        l_hh = val_head.split("(")
        l_table_name.append(l_hh[0].strip())
        if len(l_hh) == 1:
            l_table_commands.append("")
        else:
            l_table_commands.append(l_hh[1].split(")")[0].strip())
    return l_table_name, l_table_commands
        

def upload_d_np_table_by_l_table(d_np_table: dict, l_table: list[str]):
    d_np_table[" table_names"] = []
    d_np_table[" table_commands"] = []
    d_np_table[" table_colors"] = []

    if len(l_table) == 0:
        return
    # head of the table
    l_val = transform_string_to_vals(l_table[0])
    n_table = len(l_val)
    flag_head = all([isinstance(_, str) for _ in l_val])
    flag_default_head = False
    if flag_head:
        l_head_name = l_val
    else:
        flag_default_head = True
        l_head_name = [f"Column-{_+1:}" for _ in range(n_table)]

    l_table_name, l_table_commands= transform_table_head_to_names_commands(l_head_name)
    l_table_name = [transform_name_to_table_name(val) for val in l_table_name]
    d_np_table[" table_names"] = l_table_name
    d_np_table[" table_commands"] = l_table_commands

    for table_name in l_table_name:
        d_np_table[table_name] = numpy.array([], dtype=float)
    num_head = len(l_table_name)
    index_first_data = int(flag_head)

    # data of the table
    if len(l_table) <= index_first_data:
        return d_np_table
    ll_val = [[] for _ in range(num_head)]
    for i_line, line in enumerate(l_table[index_first_data:]):
        l_val = transform_string_to_vals(line)
        if len(l_val) >= num_head:
            for val, l_val_table in zip(l_val[:num_head], ll_val): 
                l_val_table.append(val)

    l_common_type = [take_common_type(l_val) for l_val  in ll_val]
    if flag_default_head:
        l_table_name_new = guess_l_table_name(l_common_type)
        if l_table_name_new is None:
            pass
        else:
            l_table_name_new= [transform_name_to_table_name(val) for val in l_table_name_new]
            for table_name in l_table_name:
                if table_name in d_np_table.keys():
                    del d_np_table[table_name]
            d_np_table[" table_names"] = l_table_name_new
            l_table_name = l_table_name_new

    for val_head, l_val, dtype  in zip(l_table_name, ll_val, l_common_type):
        d_np_table[val_head] = numpy.array(l_val, dtype=dtype)
    return

def guess_l_table_name(l_type, file:str=""):
    l_hh = file.strip().split(".")
    if len(l_hh) < 2:
        func_compare_formats = lambda x: x.startswith("types")
    else:
        func_compare_formats = lambda x: x == f"types.{l_hh[-1].strip():}"
    D_KNOWN_FORMATS = get_d_known_formats()
    l_names = None
    for key_name, val in D_KNOWN_FORMATS.items():
        if func_compare_formats(key_name):
            flag = all([_val in str(_type)  for _val, _type in zip(val, l_type)])
            flag = flag and (len(val) == len(l_type))
            if flag:
                l_names = D_KNOWN_FORMATS["names."+key_name.split(".")[1]]
                return l_names
    return l_names

def transform_lines_to_d_np_table(l_line: list[str]) -> dict:

    l_comment, l_inline, l_expression, l_table = take_comment_inline_table_lines(l_line)

    D_NP_TABLE = {" comments": l_comment}

    upload_d_np_table_by_l_inline(D_NP_TABLE, l_inline)

    upload_d_np_table_by_l_expression(D_NP_TABLE, l_expression)

    upload_d_np_table_by_l_table(D_NP_TABLE, l_table)
    
    return D_NP_TABLE
from .function_basis import transform_val_to_word
from .function_dictionary import get_d_digit_number

def transform_d_np_table_to_comments(D_NP_TABLE):
    ls_res = []
    ls_res.extend(D_NP_TABLE[" comments"])
    return ls_res


def transform_d_np_table_to_inline(D_NP_TABLE):
    ls_res = []
    s_fill = "  "

    for inline_name in D_NP_TABLE[" inline_names"]:
        ls_val = [transform_val_to_word(val, n_digits_float=5) for val in D_NP_TABLE[inline_name]]
        ls_res.append(f"{inline_name}: "+ s_fill.join(ls_val))
    return ls_res


def transform_d_np_table_to_expression(D_NP_TABLE):
    ls_res = []
    ls_res.extend(D_NP_TABLE[" expressions"])
    return ls_res


def transform_d_np_table_to_table(D_NP_TABLE):
    ls_res = []
    s_fill = "  "
    l_table_name = D_NP_TABLE[" table_names"]
    l_table_commands = D_NP_TABLE[" table_commands"]
    num_col = len(l_table_name)
    if num_col == 0:
        return ls_res
    n_row = D_NP_TABLE[l_table_name[0]].shape[0]
    lls_out = [[] for _ in range(n_row+1)]
    n_default = 0
    D_DIGIT_NUMBER = get_d_digit_number()
    l_key_name = D_DIGIT_NUMBER.keys()
    l_digit_float = [D_DIGIT_NUMBER[val_head] if val_head in l_key_name else 5 for val_head in l_table_name]
    for i_col, val_name in enumerate(l_table_name):
        np_val = D_NP_TABLE[val_name]
        ls_val = [transform_val_to_word(val, n_digits_float=l_digit_float[i_col]) for val in np_val]
        n_col_val = max([len(s_val) for s_val in ls_val]) if len(ls_val) else 0 
        val_command = l_table_commands[i_col]
        val_head = f"{val_name:}({val_command:})" if val_command != "" else val_name
        n_col = max([n_col_val, len(val_head)])

        lls_out[0].append(val_head.rjust(n_col))
        for i_row, s_val in enumerate(ls_val):
            lls_out[i_row+1].append(s_val.rjust(n_col))
    
    ls_res.extend([s_fill+s_fill.join(ls_out) for ls_out in lls_out])
    return ls_res


def transform_d_np_table_to_lines(D_NP_TABLE):
    ls_res = []
    ls_res.extend(transform_d_np_table_to_comments(D_NP_TABLE))
    ls_res.extend(transform_d_np_table_to_inline(D_NP_TABLE))
    ls_res.extend(transform_d_np_table_to_expression(D_NP_TABLE))
    ls_res.extend(transform_d_np_table_to_table(D_NP_TABLE))

    return ls_res
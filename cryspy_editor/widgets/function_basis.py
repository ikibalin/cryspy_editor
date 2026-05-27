from typing import Union

def find_common_prefix(l_line: list[str]):
    if len(l_line) == 0:
        return ""
    l_line_lower = [line.strip().lower() for line in l_line]    
    # Find the shortest string in the list
    shortest_str = min(l_line_lower, key=len)
    
    for i, char in enumerate(shortest_str):
        for line in l_line_lower:
            if line[i].lower() != char:
                return shortest_str[:i]
    return shortest_str.lower()


def remove_all_items(l_string: list[str], s_remove:str, *l_list):
    if s_remove in l_string:
        ind_to_remove = l_string.index(s_remove)
        l_string.pop(ind_to_remove)
        for h_list in l_list:
            h_list.pop(ind_to_remove)
        return remove_all_items(l_string, s_remove, *l_list)
    return


def take_common_type(l_val) -> type:
    flag_any_str = any([isinstance(val, str) for val in l_val])
    if flag_any_str:
        return str
    flag_any_float = any([isinstance(val, float) for val in l_val])
    if flag_any_float:
        return float
    flag_any_int = any([isinstance(val, int) for val in l_val])
    if flag_any_int:
        return int
    return str


def transform_val_to_word(val: Union[int, float, str], n_digits_float:int=5) -> str:
    s_type = str(type(val))
    if "int" in s_type:
        res = f"{int(val):}"
    elif "float" in s_type:
        res = '{:.{n}f}'.format(float(val), n=n_digits_float)
    else:
        res = f"{str(val):}"
    return res


def transform_string_to_vals(s_val:str) -> list:
    return [transform_word_to_val(_) for _ in s_val.replace("\t", " ").strip().split()]


def transform_word_to_val(s_val:str) -> Union[int, float,str]:
    """
    Converts a string to an integer, float, or returns the string itself.
    
    This function attempts to convert the input string to an integer. If that fails,
    it attempts to convert it to a float. If both conversions fail, it returns the
    original string.
    
    Args:
        s_val (str): The string value to be converted.
    Returns:
        Union[int, float, str]: The converted value, which can be an integer, float, or string.
    """
    try:
        res = int(s_val)
    except ValueError:
        try:
            res = float(s_val)
        except ValueError:
            res = str(s_val)
    return res

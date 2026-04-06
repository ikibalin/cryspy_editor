import os
from typing import Union


def upload_d_names_by_file(f_name:str, d_names: dict, func_to_values: callable = lambda x: x):
    if not os.path.isfile(f_name):
        return 
    with open(f_name, "r") as fid:
        l_content = fid.readlines()
    for line in l_content:
        l_h_line = line.strip().split(":")
        if len(l_h_line) != 2:
            continue 
        key_name = l_h_line[0].strip().strip("\"").strip()
        if key_name == "":
            continue
        l_val = [_.strip().strip("\"").strip() for _ in l_h_line[1].strip().split(",")]
        l_val = [_ for _ in l_val if _!=""]
        if len(l_val) == 0:
            continue
        try:
            l_val = func_to_values(l_val)
        except Exception as e:
            continue
        d_names[key_name] = l_val


F_INLINE = os.path.join(os.path.dirname(__file__), "names_in_line.dat")
F_TABLE = os.path.join(os.path.dirname(__file__), "names_in_table.dat")
F_DIGIT_NUMBER = os.path.join(os.path.dirname(__file__), "digit_number_table.dat")
F_KNOWN_FORMATS = os.path.join(os.path.dirname(__file__), "known_formats.dat")


def get_d_names_inline(file_name:str=F_INLINE):
    d_names_inline= {}
    upload_d_names_by_file(file_name, d_names_inline)
    return d_names_inline


def get_d_names_table(file_name:str=F_TABLE):
    d_names_table= {}
    upload_d_names_by_file(file_name, d_names_table)
    return d_names_table


def get_d_digit_number(file_name:str=F_DIGIT_NUMBER):
    d_digit_number = {}
    upload_d_names_by_file(file_name, d_digit_number, func_to_values=lambda x: int(x[0]))
    return d_digit_number

def get_d_known_formats(file_name:str=F_KNOWN_FORMATS):
    d_known_formats = {}
    upload_d_names_by_file(file_name, d_known_formats)
    return d_known_formats


def transform_name_to_table_name(s_val:str) -> str:
    s_1 = s_val.lower()
    s_2 = s_1.replace("-","").replace("_","").replace(".","").replace("^","").replace("**","")
    D_NAMES_IN_TABLE = get_d_names_table()
    for key_name, values in D_NAMES_IN_TABLE.items():
        if s_1 in values:
            return key_name
        elif s_2 in values:
            return key_name
    return s_val

def transform_name_to_inline_name(s_val: str) -> str:
    s_1 = s_val.lower()
    s_2 = s_1.replace("-","").replace("_","").replace(".","").replace("^","").replace("**","").replace(" ","")
    D_NAMES_IN_INLINE = get_d_names_inline()
    for key_name, values in D_NAMES_IN_INLINE.items():
        if s_1 in values:
            return key_name
        elif s_2 in values:
            return key_name
    return s_val
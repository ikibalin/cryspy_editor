import os

F_SETUP = os.path.join(
    os.path.dirname(__file__), "setup.internal")

L_SETUP_CONTENT = []

if os.path.isfile(F_SETUP):
    with open(F_SETUP, "r", encoding="utf-8") as fid:
        L_SETUP_CONTENT.extend([_.strip() for _ in fid.readlines()])


def write_to_setup_file():
    with open(F_SETUP, "w", encoding="utf-8") as fid:
        fid.write("\n".join(L_SETUP_CONTENT))
    return


def get_from_setup(name: str, value_type):
    
    s_hh = f"{name:}:"
    l_value = [hh for hh in L_SETUP_CONTENT if hh.startswith(s_hh)]
    value = None
    if len(l_value) > 0:
        s_value = ":".join(l_value[0].split(":")[1:]).strip()
        if value_type == bool:
            value = s_value.lower() == "true"
        else:
            value = value_type(s_value)
    return value


def replace_in_setup(name: str, value):
    l_i_line_del = []
    i_line_replace = None
    s_hh = f"{name:}:"
    s_line_replace = f"{s_hh:}{value:}"
    for i_line, line in enumerate(L_SETUP_CONTENT):
        if line.startswith(s_hh):
            if not i_line_replace is None:
                i_line_replace = i_line
            else:
                l_i_line_del.append(i_line)
        elif line.strip() == "":
            l_i_line_del.append(i_line)

    if i_line_replace is None:
        L_SETUP_CONTENT.append(s_line_replace)
    else:
        L_SETUP_CONTENT[i_line_replace] = s_line_replace

    l_i_line_del.sort(reverse=True)
    for i_line in l_i_line_del:
        del L_SETUP_CONTENT[i_line]
    return


def save_font_size(font_size:int):
    replace_in_setup("font_size", str(font_size))


def get_font_size() -> int:
    font_size = get_from_setup("font_size", int)
    if font_size is None:
        return 8
    return font_size

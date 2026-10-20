from PyQt5 import QtWidgets

from cryspy_editor.settings import take_settings, save_settings


def is_dark_mode(): 
    palette = QtWidgets.QApplication.palette() 
    bg = palette.window().color() 
    # Dark mode if background is darker than mid‑gray 
    return bg.lightness() < 128


def write_to_setup_file():
    save_settings()


def get_comment_character():
    s_comment = take_settings().get("comment_character", "# ")
    if not isinstance(s_comment, str) or s_comment == "":
        return "# "
    return s_comment


def save_font_size(font_size: int):
    take_settings()["font_size"] = int(font_size)


def get_font_size() -> int:
    try:
        return int(take_settings().get("font_size", 19))
    except (TypeError, ValueError):
        return 19

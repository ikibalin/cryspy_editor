"""Settings of CrysPy Editor in a JSON file in the user's folder.

Windows: %APPDATA%\\CrysPyEditor\\settings.json
macOS:   ~/Library/Application Support/CrysPyEditor/settings.json
Linux:   ~/.config/cryspy_editor/settings.json ($XDG_CONFIG_HOME is respected)

The folder can be changed by the environment variable
CRYSPY_EDITOR_CONFIG_DIR (used by tests). Settings of older versions
(setup.npy and widgets/setup.internal inside the package folder) are read
once and moved here.
"""
import json
import os
import sys

DIR_PACKAGE = os.path.dirname(__file__)
F_OLD_SETUP_NPY = os.path.join(DIR_PACKAGE, "setup.npy")
F_OLD_SETUP_INTERNAL = os.path.join(DIR_PACKAGE, "widgets", "setup.internal")

N_RECENT_FILES = 10

D_DEFAULT = {
    "data_file_name": "",
    "data_dir_name": os.path.expanduser("~"),
    "file_names_for_external_functions": "",
    "recent_files": [],
    "font_size": 19,  # as in widgets/setup.internal of older versions
    "comment_character": "# ",
    "check_for_updates": True,  # look for a new release at startup
    "skipped_update_version": "",  # "Skip this version" in the dialog
}

# one dictionary for the whole program, loaded at first use
_D_SETTINGS = {}


def take_config_dir() -> str:
    dir_env = os.environ.get("CRYSPY_EDITOR_CONFIG_DIR", "")
    if dir_env != "":
        return dir_env
    if sys.platform == "win32":
        dir_base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(dir_base, "CrysPyEditor")
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library",
                            "Application Support", "CrysPyEditor")
    dir_base = os.environ.get("XDG_CONFIG_HOME", "")
    if dir_base == "":
        dir_base = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(dir_base, "cryspy_editor")


def take_settings_file() -> str:
    return os.path.join(take_config_dir(), "settings.json")


def to_plain(value):
    """numpy scalars and tuples from old pickled settings -> JSON types."""
    if isinstance(value, (list, tuple)):
        return [to_plain(hh) for hh in value]
    if isinstance(value, dict):
        return {str(key): to_plain(hh) for key, hh in value.items()}
    if hasattr(value, "item") and not isinstance(value, str):
        return value.item()
    return value


def read_old_settings() -> dict:
    """Settings of CrysPy Editor <= 1.9 stored in the package folder."""
    d_old = {}
    if os.path.isfile(F_OLD_SETUP_NPY):
        try:
            import numpy
            d_npy = numpy.load(F_OLD_SETUP_NPY, allow_pickle=True).item()
            if isinstance(d_npy, dict):
                d_old.update(to_plain(d_npy))
        except Exception as error:
            print(f"Old settings '{F_OLD_SETUP_NPY}' are not read: {error}")
    if os.path.isfile(F_OLD_SETUP_INTERNAL):
        try:
            with open(F_OLD_SETUP_INTERNAL, "r", encoding="utf-8") as fid:
                for line in fid:
                    key, _, value = line.partition(":")
                    if key.strip() == "font_size" and value.strip().isdigit():
                        d_old["font_size"] = int(value)
                    elif key.strip() == "comment_character" and value != "":
                        d_old["comment_character"] = value.rstrip("\n")
        except OSError:
            pass
    if d_old.get("data_file_name", "") != "":
        d_old.setdefault("recent_files", [d_old["data_file_name"]])
    return d_old


def load_settings() -> dict:
    d_settings = dict(D_DEFAULT)
    d_settings["recent_files"] = []
    f_settings = take_settings_file()
    d_file = {}
    if os.path.isfile(f_settings):
        try:
            with open(f_settings, "r", encoding="utf-8") as fid:
                d_file = json.load(fid)
        except (OSError, ValueError) as error:
            print(f"Settings '{f_settings}' are not read: {error}")
    else:
        d_file = read_old_settings()
    if isinstance(d_file, dict):
        d_settings.update(d_file)
    if not isinstance(d_settings.get("recent_files"), list):
        d_settings["recent_files"] = []
    return d_settings


def take_settings() -> dict:
    """The settings dictionary shared by all windows and widgets."""
    if len(_D_SETTINGS) == 0:
        _D_SETTINGS.update(load_settings())
    return _D_SETTINGS


def reload_settings() -> dict:
    _D_SETTINGS.clear()
    return take_settings()


def save_settings() -> bool:
    """Write the settings; False if the folder is not writable."""
    f_settings = take_settings_file()
    try:
        os.makedirs(os.path.dirname(f_settings), exist_ok=True)
        f_tmp = f_settings + ".tmp"
        with open(f_tmp, "w", encoding="utf-8") as fid:
            json.dump(to_plain(take_settings()), fid, indent=2,
                      ensure_ascii=False)
        os.replace(f_tmp, f_settings)
    except (OSError, TypeError, ValueError) as error:
        print(f"Settings are not saved to '{f_settings}': {error}")
        return False
    return True


def add_recent_file(file_name: str):
    """Put the file first in the list of recent files."""
    d_settings = take_settings()
    file_name = os.path.abspath(file_name)
    l_recent = [hh for hh in d_settings.get("recent_files", [])
                if os.path.abspath(hh) != file_name]
    d_settings["recent_files"] = [file_name] + l_recent[:N_RECENT_FILES - 1]

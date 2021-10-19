import os
import os.path

import json

def text_from_d_info(d_info: dict = None):
    """Take text from print key of d_info."""
    s_out = ""
    if d_info is not None:
        s_out = d_info["print"]
        if "d_info" in d_info.keys():
            s_out_2 = text_from_d_info(d_info["d_info"])
            s_out += "\n\n" + s_out_2
    return s_out

def load_d_setup(f_setup: str):
    """Get CrysPy editor parameters from files.
    """
    if os.path.isfile(f_setup):
        d_setup = json.load(open(f_setup, 'r'))
    else:
        d_setup = {}
    return d_setup

def save_d_setup(dsetup: dict, f_setup: str):
    """Save CrysPy editor parameters to file.
    """
    s_cont = json.dumps(dsetup, sort_keys=True, indent=4)
    with open(f_setup, "w") as fid:
        fid.write(s_cont)
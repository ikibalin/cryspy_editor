"""Refinement of the example, for profiling with 1_profile.py:

    python 1_profile.py 1_profile_for.py
"""
import os

import cryspy

f_dir = os.path.dirname(os.path.abspath(__file__))
rcif_object = cryspy.load_file(os.path.join(f_dir, "main.rcif"))
d_res = cryspy.rhochi_rietveld_refinement(rcif_object)

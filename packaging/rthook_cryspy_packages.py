# PyInstaller runtime hook: CrysPy keeps its list of user packages
# (packages.dat) in its own package folder, which is read-only inside the
# built program (macOS .app on a dmg, Program Files). Keep it in the
# settings folder of CrysPy Editor instead. Not needed once CrysPy stores
# packages.dat in the user's folder itself.
import os

from cryspy.H_functions_global import function_1_cryspy_objects
from cryspy_editor.settings import take_config_dir

if function_1_cryspy_objects.F_PACKAGES.startswith(
        os.path.dirname(os.path.dirname(function_1_cryspy_objects.__file__))):
    try:
        os.makedirs(take_config_dir(), exist_ok=True)
    except OSError:
        pass
    function_1_cryspy_objects.F_PACKAGES = os.path.join(
        take_config_dir(), "cryspy_packages.dat")

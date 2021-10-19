import os
from PyQt5 import QtWidgets

app = QtWidgets.QApplication([])
wobj = QtWidgets.QMainWindow()
f_dir = os.path.curdir
f_dir = QtWidgets.QFileDialog.getExistingDirectory(
    wobj, "Select directory to create '.bat' file", f_dir)

s_cont = "python -m cryspy_editor"
f_name = os.path.join(f_dir, "CrysPy_Editor.bat")
with open(f_name, "w") as fid:
    fid.write(s_cont)

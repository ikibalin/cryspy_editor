from PyQt5 import QtCore, QtGui, QtWidgets, Qt

from cryspy import __version__ as cryspy_version
from cryspy_editor import __version__ as cryspy_editor_version

def w_about(main_window: QtWidgets.QMainWindow):
    s_address = r"https://github.com/ikibalin/cryspy"
    QtWidgets.QMessageBox.information(
        main_window, "About CrysPy",
        f"Versions:\n\
    CrysPy Editor - {cryspy_editor_version:} \n\
    CrysPy library - {cryspy_version:}\n\n\
To upgrade see the site: \n\
(address is copied to the clipboard) \n\n\
{s_address:}")

    cb = QtWidgets.QApplication.clipboard()
    cb.clear(mode=cb.Clipboard)
    cb.setText(s_address, mode=cb.Clipboard)
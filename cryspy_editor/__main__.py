"""Doc string."""
import os
import os.path
import sys

from PyQt5 import QtWidgets

from cryspy_editor.ceditor import CMainWindow


def main():
    """Make main window."""
    
    l_arg = sys.argv
    app = QtWidgets.QApplication(l_arg)
    app.setStartDragDistance(100)
    main_window = CMainWindow()
    sys.exit(app.exec_())

main()

"""Doc string."""
import os
import os.path
import sys

from PyQt5 import QtWidgets

from cryspy_editor.cl_main_window import CMainWindow
import logging

def main():
    """Make main window."""
    
    l_arg = sys.argv
    # f_logging = os.path.join(os.path.dirname(__file__), 'cryspy_editor.log')
    # logging.basicConfig(filename=f_logging, level=logging.INFO)
    # logging.info("Cryspy-Editor is runned")
    app = QtWidgets.QApplication(l_arg)
    # app.setStyle(QtWidgets.QStyleFactory.create('Fusion'))
    app.setStartDragDistance(100)
    main_window = CMainWindow()
    sys.exit(app.exec_())
    # logging.info("Cryspy-Editor is finished")

main()

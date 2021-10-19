"""WMethods class."""
from typing import Callable, Any, NoReturn
import os
from PyQt5 import QtWidgets, QtGui, QtCore

from cryspy import load_packages, add_package, packages, delete_package

class WPackages(QtWidgets.QMainWindow):
    """WPackages class."""

    def __init__(self, parent=None):
        super(WPackages, self).__init__(parent)
        self.init_widget()
        self.setWindowTitle(
            'Additional packages of the CrysPy library')
        
    def init_widget(self):
        """Init widget."""
        cw = QtWidgets.QWidget(self)
        grid_layout = QtWidgets.QGridLayout()

        self.list_widget = QtWidgets.QListWidget(cw)
        l_package = [hh.strip() for hh in packages()]
        self.list_widget.addItems(l_package)
        self.pb_add = QtWidgets.QPushButton("Add package", cw)
        self.pb_add.clicked.connect(self.add_package)
        self.pb_del = QtWidgets.QPushButton("Delete secelcted package", cw)
        self.pb_del.clicked.connect(self.del_package)
        self.list_widget.itemDoubleClicked.connect(self.copy_path)
        # self.pb_load = QtWidgets.QPushButton("Load packages", cw)
        # self.pb_load.clicked.connect(self.load_package)

        grid_layout.addWidget(self.list_widget, 0, 0, 3, 1)
        grid_layout.addWidget(self.pb_add, 0, 1, 1, 1)
        grid_layout.addWidget(self.pb_del, 1, 1, 1, 1)
        # grid_layout.addWidget(self.pb_load, 2, 1, 1, 1)

        cw.setLayout(grid_layout)
        self.setCentralWidget(cw)

    def copy_path(self, w_item):
        f_dir = w_item.text()
        try:
            os.startfile(f_dir)
        except:
            cb = QtWidgets.QApplication.clipboard()
            cb.clear(mode=cb.Clipboard)
            cb.setText(f_dir, mode=cb.Clipboard)


    def add_package(self):
        f_dir = os.getcwd()
        f_name = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Directory of package', f_dir)
        if f_name=="":
            return None
        print("f_name: ", f_name)
        add_package(f_name)
        self.refresh()

    def del_package(self):
        s_package = self.list_widget.currentItem().text()
        delete_package(s_package)
        self.refresh()

    # def load_packages(self):
    #     load_packages()
    #     self.refresh()

    def refresh(self):
        load_packages()
        self.list_widget.clear()
        l_package = [hh.strip() for hh in packages()]
        self.list_widget.addItems(l_package)

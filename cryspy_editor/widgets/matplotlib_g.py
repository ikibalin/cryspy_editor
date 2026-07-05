import os

from PyQt5 import QtWidgets


import matplotlib
import matplotlib.backends.backend_qt5agg
import matplotlib.figure 
import matplotlib.pyplot


class Graph(matplotlib.backends.backend_qt5agg.FigureCanvasQTAgg):
    def __init__(self, fig: matplotlib.figure.Figure, parent=None):
        super(Graph, self).__init__(fig)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, 
                           QtWidgets.QSizePolicy.Expanding)
        # fig.canvas.mpl_connect("button_press_event", self.onclick)
    
        # self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)        
        # self.customContextMenuRequested.connect(self.open_menu)

    def get_toolbar(self, parent=None):
        toolbar = matplotlib.backends.backend_qt5agg.NavigationToolbar2QT(
            self, parent)

        # qtb_1 = toolbar.addAction("Save to png (for notes)")
        # qtb_1.triggered.connect(self.save_fig_as)

        toolbar.update()
        self.flag_toolbar = True
        return toolbar

    # def open_menu(self, position):
    #     menu = QtWidgets.QMenu(self)
    #     save_fig_as = QtWidgets.QAction('Save figure as...', menu)
    #     save_fig_as.triggered.connect(self.save_fig_as)
    #     menu.addAction(save_fig_as)
        
    #     menu.exec_(self.viewport().mapToGlobal(position))

    def save_fig_as(self):
        f_name, okPressed = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Select a file:', os.getcwd(), "Png files (*.png)")
        if not (okPressed):
            return None
        self.figure.savefig(f_name)
        
        s_markdown = f"![Image]({f_name:})"
        cb = QtWidgets.QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText(s_markdown, mode=cb.Clipboard)


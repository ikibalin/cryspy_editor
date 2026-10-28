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

        toolbar.update()
        return toolbar

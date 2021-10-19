__author__ = 'ikibalin'
__version__ = "2020_09_10"

import os
import sys
 
from PyQt5 import QtWidgets, QtGui, QtCore

import numpy
import matplotlib
import matplotlib.backends.backend_qt5agg
import matplotlib.figure 
import matplotlib.pyplot

class cwind_central(QtWidgets.QMainWindow):
    def __init__(self):
        super(cwind_central, self).__init__()
        self.title = "program 'Graph'"
        self.setWindowTitle(self.title)
        widg_central = cwidg_central()
        self.setCentralWidget(widg_central)

         
        np_x = numpy.linspace(1, 2, 10)
        np_y = numpy.square(np_x)
        np_s = numpy.square(np_x)*0.2
        np_xm = numpy.vstack((np_x, np_y)).transpose()
        np_xes = numpy.vstack((np_x, np_y+1, np_s)).transpose()
        np_xesm = numpy.vstack((np_x, np_y+2, np_s, np_y+2.1)).transpose()
        widg_central.plot_numpy_arrays(np_x, np_xm, np_xes, np_xesm)
         
        self.show()

class cwidg_central(QtWidgets.QWidget):
    def __init__(self):
        super(cwidg_central, self).__init__()
        self.init_layout_central()
        self.setLayout(self.layout_central)
 
    def init_layout_central(self):
        lay_main = QtWidgets.QHBoxLayout()

        self.graph = Graph(self, width=5, height=4)
        """
        lay_1 = QtWidgets.QVBoxLayout()
        _b_gm = QtWidgets.QPushButton("values to clipboard")
        _b_gm.clicked.connect(self.give_values)
        lay_1.addStretch(1)
        lay_1.addWidget(_b_gm)
        """
        lay_main.addWidget(self.graph)
        #lay_main.addLayout(lay_1)

        self.layout_central = lay_main
        
    def plot_numpy_arrays(self, *argv):
        """
Keyword arguments:

    np_x: 2D array (:, 1) with columns: position of x points
    np_xm: 2D array (:, 2) with columns: x, model points
    np_xes: 2D array (:, 3) with columns: x, experimental points, sigma
    np_xesm: 2D array (:, 4) with columns: x, experimental points, sigma, model points

Example:

>>> self.plot_file(np_xes, np_xesm, np_xm)
>>> self.plot_file(np_xm)
>>> self.plot_file(np_xm, np_x)
        """
        self.graph.numpy_arrays = argv
        self.graph.set_data_to_graph()

    def give_values(self):
        """
Save information in clipboard
        """
        ls_out = ["Not realized."]
        cb = QtWidgets.QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText("\n".join(ls_out), mode=cb.Clipboard)


class Graph(matplotlib.backends.backend_qt5agg.FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = matplotlib.figure.Figure(figsize=(width, height), dpi = dpi)
        fig.subplots_adjust(left = 0.07,
                            right = 0.97,
                            top = 0.97,
                            bottom = 0.07,
                            wspace = 0.0,
                            hspace = 0.0)
        
        super(Graph, self).__init__(fig)
        self.info_press = (False, False)
        self.xlim_orig = (0., 1.)
        self.ylim_orig_1 = (0., 1.)
        self.ylim_orig_2 = (-0.5, 0.5)
        self.numpy_arrays = []

        self.control = parent
        self.figure = fig
        
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.grid = matplotlib.figure.GridSpec(4, 4)
        self.ax_pri_1, self.ax_pri_2 = None, None

        fig.canvas.mpl_connect("button_press_event", self.onclick)
        
    def set_data_to_graph(self):


        flag_ax_1, flag_ax_2 = False, False
        for np_array in self.numpy_arrays:
            n12 = np_array.shape
            if len(n12) == 1:
                flag_ax_2 = True
            else:
                if (n12[1] in (2, 3)):
                    flag_ax_1 = True
                elif (n12[1] == 4):
                    flag_ax_1 = True
                    flag_ax_2 = True

        if (flag_ax_1 & flag_ax_2): 
            self.ax_pri_1 = self.figure.add_subplot(self.grid[:-1, :], xticklabels=[])
            self.ax_pri_1.cla()
            self.ax_pri_2 = self.figure.add_subplot(self.grid[-1, :], xticklabels=[])
            self.ax_pri_2.cla()
        elif flag_ax_1: 
            self.ax_pri_1 = self.figure.add_subplot(self.grid[:, :], xticklabels=[])
            self.ax_pri_1.cla()
        elif flag_ax_2: 
            self.ax_pri_2 = self.figure.add_subplot(self.grid[:, :], xticklabels=[])
            self.ax_pri_2.cla()

        col_0 = "#000000"
        col_1 = "#FF0000"
        col_2 = "#0000FF"
        col_3 = "#006400"
        x_lim_min, x_lim_max = None, None
        y_lim_min, y_lim_max = None, None
        y_lim_min_2, y_lim_max_2 = -0.5, 0.5

        if flag_ax_2: self.ax_pri_2.axhline(y=0., linewidth=0.5, color="k", linestyle="--")

        for np_array in self.numpy_arrays:
            flag_do = True
            n12 = np_array.shape
            if len(n12) == 2:
                n1, n2 = n12
                x = np_array[:, 0]
                flag_do = not(any([numpy.all(numpy.isnan(np_array[:, _i])) for _i in range(n12[1])]))
            elif len(n12) == 1:
                n1, n2 = n12[0], 1
                x = np_array[:]
                flag_do = not(numpy.all(numpy.isnan(x)))
            else:
                flag_do = False

            if n12[0] == 0:
                flag_do = False

                

            if flag_do: 
                if x_lim_min is not None:
                    x_lim_min = min((numpy.nanmin(x), x_lim_min))
                    x_lim_max = max((numpy.nanmax(x), x_lim_max))
                else:
                    x_lim_min = numpy.nanmin(x)
                    x_lim_max = numpy.nanmax(x)

                if n2 == 1:
                    #np_x
                    for _x in x:
                        self.ax_pri_2.axvline(x=_x, linewidth=0.5, color="k", linestyle=":")
                    #self.ax_pri_2.plot(x, 0*x, "k|", linewidth=1.0)
                elif n2 == 2:
                    #np_xm
                    y_mod = np_array[:, 1]
                    if y_lim_min is not None:
                        y_lim_min = min((numpy.nanmin(y_mod), y_lim_min))
                        y_lim_max = max((numpy.nanmax(y_mod), y_lim_max))
                    else:
                        y_lim_min = numpy.nanmin(y_mod)
                        y_lim_max = numpy.nanmax(y_mod)

                    self.ax_pri_1.plot(x, y_mod, "k-", linewidth=1.0)
                elif n2 == 3:
                    #np_xes
                    y_exp = np_array[:, 1]
                    y_sig = np_array[:, 2]
                    if y_lim_min is not None:
                        y_lim_min = min((numpy.nanmin(y_exp-y_sig), y_lim_min))
                        y_lim_max = max((numpy.nanmax(y_exp+y_sig), y_lim_max))
                    else:
                        y_lim_min = numpy.nanmin(y_exp)
                        y_lim_max = numpy.nanmax(y_exp)
                    self.ax_pri_1.errorbar(x, y_exp, yerr = y_sig, ecolor = col_1,  fmt='.', color=col_1, linewidth = 0.5)
                elif n2 == 4:
                    #np_xesm
                    y_exp = np_array[:, 1]
                    y_sig = np_array[:, 2]
                    y_mod = np_array[:, 3]
                    if y_lim_min is not None:
                        y_lim_min = min((numpy.nanmin(y_mod), numpy.nanmin(y_exp-y_sig), y_lim_min))
                        y_lim_max = max((numpy.nanmax(y_mod), numpy.nanmax(y_exp+y_sig), y_lim_max))
                    else:
                        y_lim_min = min(numpy.nanmin(y_mod), numpy.nanmin(y_exp-y_sig))
                        y_lim_max = max(numpy.nanmax(y_mod), numpy.nanmax(y_exp+y_sig))

                    y_lim_min_2 = min((numpy.nanmin(y_exp-y_mod), y_lim_min_2))
                    y_lim_max_2 = max((numpy.nanmax(y_exp-y_mod), y_lim_max_2))


                    self.ax_pri_1.errorbar(x, y_exp, yerr = y_sig, ecolor = col_1,  fmt='.', color=col_1, linewidth = 0.5)
                    self.ax_pri_1.plot(x, y_mod, "k-", linewidth=1.0)
                    self.ax_pri_2.plot(x, y_exp-y_mod, "k-", linewidth=1.0)

        if x_lim_min is None:
            return
        if y_lim_max is None:
            return
        x_diff = x_lim_max - x_lim_min
        y_diff = y_lim_max - y_lim_min
        y_diff_2 = y_lim_max_2 - y_lim_min_2
        self.xlim_orig = (x_lim_min-0.05*x_diff, x_lim_max+0.05*x_diff)
        self.ylim_orig_1 = (y_lim_min-0.05*y_diff, y_lim_max+0.05*y_diff)
        self.ylim_orig_2 = (y_lim_min_2-0.05*y_diff_2, y_lim_max_2+0.05*y_diff_2)
        
        if self.ax_pri_1 is not None: self.ax_pri_1.set_xlim(self.xlim_orig)
        if self.ax_pri_2 is not None: self.ax_pri_2.set_xlim(self.xlim_orig)
        if self.ax_pri_1 is not None: self.ax_pri_1.set_ylim(self.ylim_orig_1)
        if self.ax_pri_2 is not None: self.ax_pri_2.set_ylim(self.ylim_orig_2)


    def onclick(self, event):
        if event.button == 3:
            if self.info_press == (False, False):
                self.info_press = (True, False)
                self.xlim = [event.xdata]
                self.ylim = [event.ydata]
            elif self.info_press == (True, False):
                self.info_press = (True, True)
                self.xlim.append(event.xdata)
                self.ylim.append(event.ydata)
            if self.info_press == (True, True):
                self.info_press = (False, False)
                xlim = (min(self.xlim), max(self.xlim))
                ylim = (min(self.ylim), max(self.ylim))
                if self.ax_pri_1 is not None: self.ax_pri_1.set_xlim(xlim)
                if self.ax_pri_2 is not None: self.ax_pri_2.set_xlim(xlim)
                if self.ax_pri_1 is not None: self.ax_pri_1.set_ylim(ylim)
                self.xlim = []
                self.ylim = []
                self.draw()
        elif event.button == 1:
                self.info_press == (False, False)
                if self.ax_pri_1 is not None:  self.ax_pri_1.set_xlim(self.xlim_orig)
                if self.ax_pri_2 is not None: self.ax_pri_2.set_xlim(self.xlim_orig)
                if self.ax_pri_1 is not None: self.ax_pri_1.set_ylim(self.ylim_orig_1)
                if self.ax_pri_2 is not None: self.ax_pri_2.set_ylim(self.ylim_orig_2)
                self.xlim = []
                self.ylim = []
                self.draw()
        else:
            self.info_press == (False, False)
            self.xlim = []
            self.ylim = []
            
 
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    fname = "NaCaAlF_exp.out"
    ex = cwind_central()
    
    sys.exit(app.exec_())

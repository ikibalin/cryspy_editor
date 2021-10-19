import os
import sys

import pycifstar

from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5 import QtCore
 
import matplotlib
import matplotlib.backends.backend_qt5agg
import matplotlib.figure 
import matplotlib.pyplot

import numpy
import math
import scipy
import scipy.optimize


class ccomunicate(QtCore.QObject):
    sig_m = QtCore.pyqtSignal()
    sig_l_tth = QtCore.pyqtSignal()
    sig_l_phi = QtCore.pyqtSignal()
    sig_l_redraw = QtCore.pyqtSignal()





class cmodel(QtCore.QObject):
    """
    class to control changings in the widget and to interact with data
    """
    def __init__(self, x, y, z):
        super(cmodel, self).__init__()
        self.data_matrix = z
        self.data_range_x = x
        self.data_range_y = y
        
        self.min_x = numpy.nan
        self.max_x = numpy.nan
        self.min_y = numpy.nan
        self.max_y = numpy.nan
        self.min_z_u = numpy.nan
        self.max_z_u = numpy.nan
        self.reset_limit()
        
    def reset_limit(self):
        self.min_x = numpy.nanmin(self.data_range_x)
        self.max_x = numpy.nanmax(self.data_range_x)
        self.min_y = numpy.nanmin(self.data_range_y)
        self.max_y = numpy.nanmax(self.data_range_y)        
        
        
        self.min_z_u = numpy.nanmin(self.data_matrix)
        self.max_z_u = numpy.nanmax(self.data_matrix)

        
    def index_to_value(self, ind_x, ind_y):
        iint_x = int(round(ind_x))
        iint_y = int(round(ind_y))
        val_x = self.data_range_x[iint_x]
        val_y = self.data_range_y[iint_y]
        return val_x, val_y
        
    def value_to_index(self, val_x, val_y):
        min_x = numpy.nanmin(self.data_range_x)
        max_x = numpy.nanmax(self.data_range_x)
        min_y = numpy.nanmin(self.data_range_y)
        max_y = numpy.nanmax(self.data_range_y)
        ind_x = int(round((self.data_range_x.size-1)*(val_x-min_x)*1./(max_x-min_x)))
        ind_y = int(round((self.data_range_y.size-1)*(val_y-min_y)*1./(max_y-min_y)))
        return ind_x, ind_y



class cwidg_central(QtWidgets.QWidget):
    def __init__(self):
        super(cwidg_central, self).__init__()
        self.init_layout_central()
        self.setLayout(self.layout_central)
        
 
    def init_layout_central(self):
        
        lay_main = QtWidgets.QHBoxLayout()
        
        self.graph_m = cgraph_matrix(self)
        self.graph_m.figure.canvas.mpl_connect("button_press_event", self.onclick_matrix)

        def _temp_func(_graph_m, label, val):
            if label == "min":
                _graph_m.image.set_clim(vmin=val)
            elif label == "max":
                _graph_m.image.set_clim(vmax=val)
            _graph_m.draw()
            return

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        lay_right = QtWidgets.QVBoxLayout()
        _l_1 = QtWidgets.QLabel("z_min:")
        self._l_e_z_min = QtWidgets.QLineEdit()
        self._l_e_z_min.editingFinished.connect(lambda : _temp_func(self.graph_m, "min", float(str(self._l_e_z_min.text()))))

        _l_2 = QtWidgets.QLabel("z_max:")
        self._l_e_z_max = QtWidgets.QLineEdit()
        self._l_e_z_max.editingFinished.connect(lambda : _temp_func(self.graph_m, "max", float(str(self._l_e_z_max.text()))))
        
        self._l_coord = QtWidgets.QLabel()

        _b_gm = QtWidgets.QPushButton("matrix to clipboard")
        _b_gm.clicked.connect(self.give_matrix)

        lay_right.addWidget(_l_1)
        lay_right.addWidget(self._l_e_z_min)
        lay_right.addWidget(_l_2)
        lay_right.addWidget(self._l_e_z_max)
        lay_right.addWidget(self._l_coord)
        lay_right.addStretch(1)
        lay_right.addWidget(_b_gm)

        _l_1.setSizePolicy(sizePolicy)
        self._l_e_z_min.setSizePolicy(sizePolicy)
        _l_2.setSizePolicy(sizePolicy)
        self._l_e_z_max.setSizePolicy(sizePolicy)
        _b_gm.setSizePolicy(sizePolicy)


        """
        splitter_h = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter_v = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter_v.addWidget(self.graph_l_tth)
        splitter_v.addWidget(self.graph_l_phi)
        splitter_h.addWidget(self.graph_m)
        splitter_h.addWidget(splitter_v)
        lay_cp = self.control_panel()
        lay_1 = QtWidgets.QVBoxLayout()
        lay_1.addWidget(splitter_h)
        lay_1.addLayout(lay_cp)
        """
        lay_main.addWidget(self.graph_m)
        lay_main.addLayout(lay_right)
        self.layout_central = lay_main

    def give_matrix(self):
        val_x = self.graph_m.val_x
        val_y = self.graph_m.val_y
        val_z = self.graph_m.val_z

        ls_out = []
        ls_out.append(f"{val_y.size:15} " + " ".join([f"{_:15.2f}" for _ in val_x]))
        for _y, _l_z in zip(val_y, val_z):
            sline = f"{_y:15.2f} "+" ".join(["           None" if numpy.isnan(_) else f"{_:15.1f}" for _ in _l_z])
            ls_out.append(sline)
        
        cb = QtWidgets.QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText("\n".join(ls_out), mode=cb.Clipboard)

    def onclick_matrix(self, event):
        ind_x = int(round(event.xdata))
        ind_y = int(round(event.ydata))
        val_x, val_y = self.model.index_to_value(ind_x, ind_y)
        str_x = "{:.3f}".format(val_x)
        str_y = "{:.3f}".format(val_y)
    
        val_z = None
        val_z = self.model.data_matrix[ind_y, ind_x]

        str_z = "{:.3f}".format(val_z)
        
        if event.button == 1:
            self._l_coord.setText(f"x: {val_x:.2f}\ny: {val_y:.2f}\nz: {val_z:.2f}")
        elif event.button == 2:
            self.graph_m.set_lim(0, len(self.graph_m.val_x)-1, "x")
            self.graph_m.set_lim(0, len(self.graph_m.val_y)-1, "y")
            self.graph_m.lim_flag = True
            
        elif event.button == 3:
            if self.graph_m.lim_flag:
                self.graph_m.lim_flag = False
                self.graph_m.xlim_1 = ind_x
                self.graph_m.ylim_1 = ind_y
            else:
                self.graph_m.lim_flag = True
                self.graph_m.set_lim(None, ind_x, "x")
                self.graph_m.set_lim(None, ind_y, "y")
    
    def plot_matrix(self, x, y, z):
        self.model = cmodel(x, y, z)
        self.graph_m.set_x(x)
        self.graph_m.set_y(y)
        self.graph_m.set_z(z)
        
        try:
            flag = numpy.logical_not(numpy.isnan(z))
            self._l_e_z_min.setText(f"{min(z[flag]):.0f}")
            self._l_e_z_max.setText(f"{max(z[flag]):.0f}")
        except:
            pass
        
        self.graph_m.set_data_to_graph()

    def change_value(self, value):        
        return


       
class cgraph(matplotlib.backends.backend_qt5agg.FigureCanvasQTAgg):
 
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = matplotlib.figure.Figure(figsize=(width, height), dpi = dpi)
        self.fig.subplots_adjust(left = 0.12,
                            right = 0.90,
                            top = 0.90,
                            bottom = 0.12,
                            wspace = 0.0,
                            hspace = 0.0)
        super(cgraph, self).__init__(self.fig)
        self.xlim_1 = None
        self.xlim_2 = None
        self.ylim_1 = None
        self.ylim_2 = None
        self.zlim_1 = None
        self.zlim_2 = None
        self.lim_flag = True
        
        self.val_x = None
        self.val_y = None
        self.val_z = None
        
        self.info_press = (False, False)
        self.control = parent
        self.figure = self.fig
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.ax_pri = self.fig.add_subplot(111)
        #fig.canvas.mpl_connect("button_press_event", self.onclick)
        
        
    def onclick(self, event):
        print("x position: ", event.xdata)
        print("y position: ", event.ydata)
        
    def set_x(self, np_x):
        self.val_x = np_x
        
    def set_y(self, np_y):
        self.val_y = np_y
        
    def set_z(self, np_z):
        self.val_z = np_z
    
    def set_lim(self, xlim_1, xlim_2, ax):
        
        if xlim_1 != None:
            if ax == "x":
                self.xlim_1 = xlim_1
            elif ax == "y":
                self.ylim_1 = xlim_1
            elif ax == "z":
                self.zlim_1 = xlim_1
        if xlim_2 != None:
            if ax == "x":
                self.xlim_2 = xlim_2
            elif ax == "y":
                self.ylim_2 = xlim_2
            elif ax == "z":
                self.zlim_2 = xlim_2
        if ax == "x":
            if (self.xlim_1 != None) & (self.xlim_2 != None):
                x_min = min([self.xlim_1, self.xlim_2])
                x_max = max([self.xlim_1, self.xlim_2])
                self.ax_pri.set_xlim([x_min, x_max])
                self.draw()        
        elif ax == "y":
            if (self.ylim_1 != None) & (self.ylim_2 != None):
                x_min = min([self.ylim_1, self.ylim_2])
                x_max = max([self.ylim_1, self.ylim_2])
                self.ax_pri.set_ylim([x_min, x_max])
                self.draw()        
        elif ax == "z":
            if (self.zlim_1 != None) & (self.zlim_2 != None):
                x_min = min([self.zlim_1, self.zlim_2])
                x_max = max([self.zlim_1, self.zlim_2])
                self.image.set_clim(vmin = x_min, vmax = x_max)
                self.draw()        

     

class cgraph_matrix(cgraph):
    def __init__(self, parent=None):
        super(cgraph_matrix, self).__init__(cgraph)
        self.zlim_1 = None
        self.zlim_2 = None
        self.fig.subplots_adjust(left = 0.02,
                            right = 0.95,
                            top = 0.95,
                            bottom = 0.02,
                            wspace = 0.0,
                            hspace = 0.0)
        
        
        
    def onclick(self, event):
        ind_tth = int(event.xdata)
        ind_phi = int(event.ydata)
        if event.button == 1:
            self.val_x_inline = self.val_z[ind_phi, :]
            self.val_y_inline = self.val_z[:, ind_tth]
            
            self.sig.sig_m.emit()
        elif event.button == 2:
            self.set_lim(0, len(self.val_x)-1, "x")
            self.set_lim(0, len(self.val_y)-1, "y")
            self.lim_flag = True
            self.sig.sig_l_redraw.emit()
            
        elif event.button == 3:
            ind_tth = int(event.xdata)
            ind_phi = int(event.ydata)
            if self.lim_flag:
                
                self.lim_flag = False
                self.xlim_1 = ind_tth
                self.ylim_1 = ind_phi
            else:
                
                self.lim_flag = True
                self.set_lim(None, ind_tth, "x")
                self.set_lim(None, ind_phi, "y")
                self.sig.sig_l_redraw.emit()

        
    def set_data_to_graph(self):
        self.ax_pri.cla()
        if (self.zlim_1 != None) and (self.zlim_2 != None):
            image = self.ax_pri.imshow(self.val_z, aspect = 'auto', origin = 'lower', vmin = self.zlim_1, vmax = self.zlim_2)
        else:
            image = self.ax_pri.imshow(self.val_z, aspect = 'auto', origin = 'lower')
        #self.ax_pri.set_axis_off()
        #numpy.arange(len(self.val_x)),self.val_x
        self.ax_pri.set_xticks([])
        
        self.ax_pri.set_yticks([])
        if ((self.xlim_1 != None)&(self.xlim_2 != None)):
            x_min = min([self.xlim_1 , self.xlim_2])
            x_max = max([self.xlim_1 , self.xlim_2])
            self.ax_pri.set_xlim([x_min, x_max])
        if ((self.ylim_1 != None)&(self.ylim_2 != None)):
            y_min = min([self.ylim_1 , self.ylim_2])
            y_max = max([self.ylim_1 , self.ylim_2])
            self.ax_pri.set_ylim([y_min, y_max])
        #self.ax_pri.plot(self.data_x, self.data_y, "-")
        #self.ax_pri.matshow(self.np_int)
        #self.ax_pri.set_xticks(self.np_tth)
        #self.ax_pri.set_yticks(self.np_phi)
        #print self.np_phi.size
        #print self.np_tth.size
        #print self.np_int.shape
        #self.ax_pri.plot(self.data_x, self.data_x, "k-", linewidth=1.0)    
        #self.ax_pri.errorbar(self.data_x, self.data_y, yerr = self.data_sy, ecolor = col_1, fmt='o', color=col_1, linewidth = 0.5)
        self.image = image
        self.draw()

        

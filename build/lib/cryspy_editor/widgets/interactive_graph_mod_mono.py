__author__ = 'ikibalin'
__version__ = "2019_09_10"

import os
import sys

import numpy

from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5 import QtCore
 
import matplotlib
import matplotlib.backends.backend_qt5agg
import matplotlib.figure 
import matplotlib.pyplot
 

class cwind_central(QtWidgets.QMainWindow):
    def __init__(self, fname):
        super(cwind_central, self).__init__()
        self.title = "program 'Graph'"
        self.setWindowTitle(self.title)
        widg_central = cwidg_central(fname)
        self.setCentralWidget(widg_central)
        self.show()
        
class cwidg_central(QtWidgets.QWidget):
    def __init__(self, ffig_full = None):
        super(cwidg_central, self).__init__()
        self.init_layout_central(ffig_full)
        self.setLayout(self.layout_central)
        self.ffig_full = ffig_full
 
    def init_layout_central(self, ffig_full):
        
        lay_main = QtWidgets.QHBoxLayout()
        self.graph = Graph(self, width=5, height=4)
        

        lay_1 = QtWidgets.QVBoxLayout()
        _b_gm = QtWidgets.QPushButton("values to clipboard")
        _b_gm.clicked.connect(self.give_values)
        
        lay_1.addStretch(1)
        lay_1.addWidget(_b_gm)

        lay_main.addWidget(self.graph)
        lay_main.addLayout(lay_1)

        
        self.layout_central = lay_main
        
    def plot_file(self, x, y_exp, y_sig=None): 
        """
Temporary file. It will be deleted
        """
        self.graph.ax_pri.cla()       

        self.graph.data_x = x
        self.graph.data_y = y_exp
        self.graph.data_sy = y_sig
        
        self.graph.set_data_to_graph()

    def plot_lines(self, x, l_y=None, l_y_sig=None): 
        self.graph.ax_pri.cla()       

        self.graph.data_x = x
        if l_y is not None:
            self.graph.data_l_y = l_y
        if ((l_y_sig is not None) & (self.graph.data_l_y is not None)):
            if (len(l_y_sig) == len(self.graph.data_l_y)):
                self.graph.data_l_y_sig = l_y_sig
        
        self.graph.set_data_to_graph()


    def give_values(self):
        
        val_x = self.graph.data_x
        val_y = self.graph.data_y
        val_sy = self.graph.data_sy

        sval_x = [f"{_:.3f}" for _ in val_x] 
        sval_y = [" None" if (numpy.isnan(_) | (_ is None)) else f"{_:.3f}" for _ in val_y] 

        if val_sy is None:
            sval_sy = ["" for _ in val_y]
        else:
            sval_sy = [" None" if (numpy.isnan(_) | (_ is None)) else f"{_:.3f}" for _ in val_sy] 
        ls_out = [f"{_1:} {_2:} {_3:}"  for _1, _2, _3 in zip(sval_x, sval_y, sval_sy)]

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

        self.data_x = []
        self.data_y = []
        self.data_sy = []

        self.data_l_y = []
        self.data_l_y_sig = []

        self.control = parent
        self.figure = fig
        
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.ax_pri = fig.add_subplot(111)
        
        fig.canvas.mpl_connect("button_press_event", self.onclick)
        
    def set_data_to_graph(self):
        col_1 = "#000000"
        #self.ax_pri.plot(self.data_x, self.data_y, "-")
        _x = self.data_x
        _y = self.data_y
        _y_sig = self.data_sy

        l_y = self.data_l_y
        l_y_sig = self.data_l_y_sig
        if (len(l_y) != 0):
            if (len(l_y)==len(l_y_sig)):
                for _y, _y_sig in zip(l_y, l_y_sig):
                    if _y_sig is None:
                        self.ax_pri.plot(_x, _y, "k-", linewidth=1.0)
                    else:
                        self.ax_pri.errorbar(_x, _y, yerr = _y_sig, ecolor = col_1, fmt='o', color=col_1, linewidth = 0.5)
            else:
                for _y in l_y:
                    self.ax_pri.plot(_x, _y, "k-", linewidth=1.0)
        else:
            if _y_sig is None:
                self.ax_pri.plot(_x, _y, "k-", linewidth=1.0)
            else:
                self.ax_pri.plot(_x, _y_sig, "b-", linewidth=1.0)  
            #self.ax_pri.errorbar(self.data_x, self.data_y, yerr = self.data_sy, ecolor = col_1, fmt='o', color=col_1, linewidth = 0.5)
        self.draw()
        
    def onclick(self, event):
        if event.button == 3:
            #print(event.xdata, event.ydata)
            #self.data_x.append(event.xdata)
            #self.data_y.append(event.ydata)
            #self.set_data_to_graph()
            
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
                self.ax_pri.set_xlim(xlim)
                self.ax_pri.set_ylim(ylim)
                self.xlim = []
                self.ylim = []
                self.draw()
        elif event.button == 2:
                self.info_press == (False, False)
                x_min = min(self.data_x)
                x_max = max(self.data_x)
                if len(self.data_l_y) != 0:
                    l_y_min, l_y_max = [], []
                    for _y in self.data_l_y:
                        if isinstance(_y, numpy.ndarray):
                            _y_min = min(_y[numpy.logical_not(numpy.isnan(_y))])
                            _y_max = max(_y[numpy.logical_not(numpy.isnan(_y))])
                        else:
                            _y_min = min([_1 for _1 in _y if _1 is not None])
                            _y_max = max([_1 for _1 in _y if _1 is not None])
                        l_y_min.append(_y_min)
                        l_y_max.append(_y_max)
                    y_min = min(l_y_min)
                    y_max = max(l_y_max)
                else:
                    y_min = min(self.data_y)
                    y_max = max(self.data_y)
                x_diff = x_max - x_min
                y_diff = y_max - y_min
                xy_min = min([x_min, y_min])
                xy_max = max([x_max, y_max])
                xy_diff = xy_max - xy_min
                xlim = (xy_min - 0.05*xy_diff, xy_max + 0.05*xy_diff)
                x_lim = (x_min - 0.05*x_diff, x_max + 0.05*x_diff)
                y_lim = (y_min - 0.05*y_diff, y_max + 0.05*y_diff)
                self.ax_pri.set_xlim(x_lim)
                self.ax_pri.set_ylim(y_lim)
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
    fname = "oHoTi_p.dat"
    ex = cwind_central(fname)
    
    sys.exit(app.exec_())
    
    
    
"""
    def clean_fig(self):
        self.ldata = []
        self.ldata_simple = []
        self.pcanvas.figure.clf()
        self.pcanvas.make_plot()
        self.pcanvas.draw()
        
    def replot_fig(self):
        lhelp=['#005555','#BB5555','#550055','#55BB55','#555500','#5555BB']
        for iddata, ddata in enumerate(self.ldata_simple):
            lflags = [ (isinstance(hh1,(float, int))&isinstance(hh2,(float, int))&isinstance(hh3,(float, int))&isinstance(hh4,(float, int))) for hh1,hh2,hh3,hh4 in zip(ddata["IntUP"],ddata["sIntUP"],ddata["IntDOWN"],ddata["sIntDOWN"])]
            lx = [hh for hh, flag in zip(ddata["ttheta"], lflags) if flag]
            li_u_exp = [hh for hh, flag in zip(ddata["IntUP"], lflags) if flag]
            lsi_u_exp = [hh for hh, flag in zip(ddata["sIntUP"], lflags) if flag]
            li_d_exp = [hh for hh, flag in zip(ddata["IntDOWN"], lflags) if flag]
            lsi_d_exp = [hh for hh, flag in zip(ddata["sIntDOWN"], lflags) if flag]
            
            #li_u_exp = ddata["IntUP"]
            #lsi_u_exp = ddata["sIntUP"]
            #li_d_exp = ddata["IntDOWN"]
            #lsi_d_exp = ddata["sIntDOWN"]
            ldiff_exp = [hh1-hh2 for hh1, hh2 in zip(li_u_exp, li_d_exp)]
            lsdiff_exp = [(hh1**2+hh2**2)**0.5  for hh1, hh2 in zip(lsi_u_exp, lsi_d_exp)]
            lcolors=[lhelp[iddata] for hh in range(3)]
            self.pcanvas.plot(lx,[li_u_exp,lsi_u_exp,None],[li_d_exp,lsi_d_exp,None],[ldiff_exp,lsdiff_exp,None],None,lcolors)
        xmin = float(self.le_xmin.text())
        xmax = float(self.le_xmax.text())
        ymin = float(self.le_ymin.text())
        ymax = float(self.le_ymax.text())
        self.pcanvas.set_limits(xmin,xmax,ymin,ymax)          
        self.pcanvas.draw()
"""    
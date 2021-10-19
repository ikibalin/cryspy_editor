import numpy
from PyQt5 import QtWidgets, QtGui, QtCore
from .interactive_graph_mod_mono import cwidg_central

from .FUNCTIONS import make_qtablewidget_for_loop_constr, show_info


def widget_for_meas_inelasticl(obj, label_out):
    lay_to_fill = QtWidgets.QHBoxLayout()

    lay_left = QtWidgets.QVBoxLayout()

    
    w_t = make_qtablewidget_for_loop_constr(obj)
        
    lay_left.addWidget(w_t)

    if obj.count_calc is not None:
        widg_graph_1d = cwidg_central()
        widg_graph_1d.plot_lines(obj.energy, l_y=[obj.count, obj.count_calc], l_y_sig=[obj.count_sigma, None])
        lay_left.addWidget(widg_graph_1d)

    _b_info = QtWidgets.QPushButton("info")
    _b_info.clicked.connect(lambda : show_info(obj, label_out))
    lay_left.addWidget(_b_info)


    lay_to_fill.addLayout(lay_left)
    widg_out = QtWidgets.QWidget()
    widg_out.setLayout(lay_to_fill)
    
    return widg_out

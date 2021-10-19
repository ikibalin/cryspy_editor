import numpy
from PyQt5 import QtWidgets, QtGui, QtCore
from .interactive_graph_mod_mono import cwidg_central

from .FUNCTIONS import make_qtablewidget_for_loop_constr, show_info, del_layout
from .w_loop_constr import w_for_loop_constr

def w_for_meas_inelasticl(obj, layout_11, layout_12, layout_13, layout_2, layout_3, w_output, thread):
    w_for_loop_constr(obj, layout_11, layout_12, layout_13, layout_2, layout_3, w_output, thread)

    if obj.count_calc is not None:
        del_layout(layout_3)
        widg_graph_1d = cwidg_central()
        widg_graph_1d.plot_lines(obj.energy, l_y=[obj.count, obj.count_calc], l_y_sig=[obj.count_sigma, None])
        layout_3.addWidget(widg_graph_1d)
    
    return 

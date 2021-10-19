import numpy
from PyQt5 import QtWidgets

from .i_graph_mod_1d import cwidg_central as cwidg_pwd
from .FUNCTIONS import get_layout_rciftab_obj, del_layout
from .w_loop_constr import w_for_loop_constr

def w_for_pd_peak(obj, layout_11, layout_12, layout_13, layout_2, layout_3, w_output, thread):
    w_for_loop_constr(obj, layout_11, layout_12, layout_13, layout_2, layout_3, w_output, thread)
    del_layout(layout_3)

    np_x_1 = numpy.array(obj.ttheta, dtype = float)
    np_y_1 = numpy.array(obj.width_ttheta, dtype = float)

    np_xy_1 = numpy.vstack((np_x_1, np_y_1)).transpose()
    w_s_1 = cwidg_pwd()
    w_s_1.plot_numpy_arrays(np_xy_1, np_x_1)

    layout_3.addWidget(w_s_1)
    return 
    
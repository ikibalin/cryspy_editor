import numpy
from PyQt5 import QtWidgets, QtGui, QtCore
from .i_graph_mod_1d import cwidg_central as cwidg_pwd
from .FUNCTIONS import get_layout_rciftab_obj, del_layout
from .w_loop_constr import w_for_loop_constr


def w_for_diffrn_refln(obj, layout_11, layout_12, layout_13, layout_2, layout_3, w_output, thread):
    w_for_loop_constr(obj, layout_11, layout_12, layout_13, layout_2, layout_3, w_output, thread)
    del_layout(layout_3)

    np_x_1 = numpy.array(obj.fr_calc, dtype = float)
    np_y_1 = numpy.array(obj.fr, dtype = float)
    np_s_1 = numpy.array(obj.fr_sigma, dtype = float)
    if (numpy.all(numpy.isnan(np_x_1)) | numpy.all(numpy.isnan(np_y_1)) | numpy.all(numpy.isnan(np_s_1))):
        return
    np_xys_1 = numpy.vstack((np_x_1, np_y_1, np_s_1)).transpose()
    np_xm_1 = numpy.vstack((np_x_1, np_x_1)).transpose()

    w_s_1 = cwidg_pwd()
    w_s_1.plot_numpy_arrays(np_xys_1, np_xm_1)

    layout_3.addWidget(w_s_1)
    return

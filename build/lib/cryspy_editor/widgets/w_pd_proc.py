import numpy
from PyQt5 import QtWidgets

from .i_graph_mod_1d import cwidg_central as cwidg_pwd
from .FUNCTIONS import get_layout_rciftab_obj, del_layout
from .w_loop_constr import w_for_loop_constr

def w_for_pd_proc(obj, layout_11, layout_12, layout_13, layout_2, layout_3, w_output, thread):
    w_for_loop_constr(obj, layout_11, layout_12, layout_13, layout_2, layout_3, w_output, thread)
    del_layout(layout_3)

    np_x_1 = numpy.array(obj.ttheta, dtype = float)
    np_y_u_1 = numpy.array(obj.intensity_up, dtype = float)
    np_y_su_1 = numpy.array(obj.intensity_up_sigma, dtype = float)
    np_y_d_1 = numpy.array(obj.intensity_down, dtype = float)
    np_y_sd_1 = numpy.array(obj.intensity_down_sigma, dtype = float)
    np_y_b_1 = numpy.array(obj.intensity_bkg_calc, dtype = float)
    np_y_u_2 = numpy.array(obj.intensity_up_total, dtype = float)
    np_y_d_2 = numpy.array(obj.intensity_down_total, dtype = float)
    np_y_s_1 = numpy.array(obj.intensity, dtype = float)
    np_y_ss_1 = numpy.array(obj.intensity_sigma, dtype = float)
    np_y_m_1 = np_y_u_1 - np_y_d_1
    np_y_sm_1 = np_y_ss_1
    np_y_s_2 = numpy.array(obj.intensity_total, dtype = float)
    np_y_m_2 = numpy.array(obj.intensity_diff_total, dtype = float)

    np_xysm_1 = numpy.vstack((np_x_1, np_y_s_1, np_y_ss_1, np_y_s_2)).transpose()
    np_xb_1 = numpy.vstack((np_x_1, 2*np_y_b_1)).transpose()
    w_s_1 = cwidg_pwd()
    w_s_1.plot_numpy_arrays(np_xysm_1, np_xb_1)

    np_xysm_1 = numpy.vstack((np_x_1, np_y_m_1, np_y_sm_1, np_y_m_2)).transpose()
    w_s_2 = cwidg_pwd()
    w_s_2.plot_numpy_arrays(np_xysm_1)

    np_xysm_1 = numpy.vstack((np_x_1, np_y_u_1, np_y_su_1, np_y_u_2)).transpose()
    np_xb_1 = numpy.vstack((np_x_1, np_y_b_1)).transpose()
    w_s_3 = cwidg_pwd()
    w_s_3.plot_numpy_arrays(np_xysm_1, np_xb_1)

    np_xysm_1 = numpy.vstack((np_x_1, np_y_d_1, np_y_sd_1, np_y_d_2)).transpose()
    w_s_4 = cwidg_pwd()
    w_s_4.plot_numpy_arrays(np_xysm_1, np_xb_1)

    stack_widg = QtWidgets.QStackedWidget()
    stack_widg.addWidget(w_s_1)
    stack_widg.addWidget(w_s_2)
    stack_widg.addWidget(w_s_3)
    stack_widg.addWidget(w_s_4)
        
    lay_h = QtWidgets.QHBoxLayout()
    _rb_1 = QtWidgets.QRadioButton("sum")
    _rb_1.toggled.connect(lambda: stack_widg.setCurrentIndex(0))
    lay_h.addWidget(_rb_1)
    _rb_1.setChecked(True)
    _rb_2 = QtWidgets.QRadioButton("diff")
    _rb_2.toggled.connect(lambda: stack_widg.setCurrentIndex(1))
    lay_h.addWidget(_rb_2)
    _rb_3 = QtWidgets.QRadioButton("up")
    _rb_3.toggled.connect(lambda: stack_widg.setCurrentIndex(2))
    lay_h.addWidget(_rb_3)
    _rb_4 = QtWidgets.QRadioButton("down")
    _rb_4.toggled.connect(lambda: stack_widg.setCurrentIndex(3))
    lay_h.addWidget(_rb_4)
    lay_h.addStretch(1)

    layout_3.addLayout(lay_h)
    layout_3.addWidget(stack_widg)
    return 


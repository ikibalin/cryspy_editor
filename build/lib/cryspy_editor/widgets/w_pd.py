import numpy
from PyQt5 import QtWidgets

from .FUNCTIONS import get_layout_rciftab_obj, del_layout
from .w_pd_proc import w_for_pd_proc
from .w_pd_meas import w_for_pd_meas
from .w_data_constr import w_for_data_constr
from .i_graph_mod_1d import cwidg_central as cwidg_pwd
from cryspy import PdMeasL, PdProcL, PdBackgroundL, PdPeakL

def w_for_pd(obj, layout_11, layout_12, layout_13, layout_2, layout_3, w_output, thread):
    w_for_data_constr(obj, layout_11, layout_12, layout_13, layout_2, layout_3, w_output, thread)
    del_layout(layout_3)

    f_proc, f_meas, f_bkgr, f_peak = False, False, False, False
    proc, meas, bkgr, peak = None, None, None, None
    meas = obj.meas
    f_meas = meas is not None
    bkgr = obj.background
    f_bkgr = bkgr is not None
    for int_obj in obj.internal_objs:
        if isinstance(int_obj, PdProcL):
            proc, f_proc = int_obj, True
        elif isinstance(int_obj, PdPeakL):
            peak, f_peak = int_obj, True
    if (f_proc & f_peak):
        np_x_1 = numpy.array(proc.ttheta, dtype = float)
        np_y_u_1 = numpy.array(proc.intensity_up, dtype = float)
        np_y_su_1 = numpy.array(proc.intensity_up_sigma, dtype = float)
        np_y_d_1 = numpy.array(proc.intensity_down, dtype = float)
        np_y_sd_1 = numpy.array(proc.intensity_down_sigma, dtype = float)
        np_y_b_1 = numpy.array(proc.intensity_bkg_calc, dtype = float)
        np_y_u_2 = numpy.array(proc.intensity_up_total, dtype = float)
        np_y_d_2 = numpy.array(proc.intensity_down_total, dtype = float)
        np_y_s_1 = numpy.array(proc.intensity, dtype = float)
        np_y_ss_1 = numpy.array(proc.intensity_sigma, dtype = float)
        np_y_m_1 = np_y_u_1 - np_y_d_1
        np_y_sm_1 = np_y_ss_1
        np_y_s_2 = numpy.array(proc.intensity_total, dtype = float)
        np_y_m_2 = numpy.array(proc.intensity_diff_total, dtype = float)

        np_x_2 = numpy.array(peak.ttheta, dtype = float)
        np_xysm_1 = numpy.vstack((np_x_1, np_y_s_1, np_y_ss_1, np_y_s_2)).transpose()
        np_xb_1 = numpy.vstack((np_x_1, 2*np_y_b_1)).transpose()
        w_s_1 = cwidg_pwd()
        w_s_1.plot_numpy_arrays(np_x_2, np_xysm_1, np_xb_1)

        np_xysm_1 = numpy.vstack((np_x_1, np_y_m_1, np_y_sm_1, np_y_m_2)).transpose()
        w_s_2 = cwidg_pwd()
        w_s_2.plot_numpy_arrays(np_x_2, np_xysm_1)

        np_xysm_1 = numpy.vstack((np_x_1, np_y_u_1, np_y_su_1, np_y_u_2)).transpose()
        np_xb_1 = numpy.vstack((np_x_1, np_y_b_1)).transpose()
        w_s_3 = cwidg_pwd()
        w_s_3.plot_numpy_arrays(np_x_2, np_xysm_1, np_xb_1)

        np_xysm_1 = numpy.vstack((np_x_1, np_y_d_1, np_y_sd_1, np_y_d_2)).transpose()
        w_s_4 = cwidg_pwd()
        w_s_4.plot_numpy_arrays(np_x_2, np_xysm_1, np_xb_1)

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
    elif (f_meas & f_bkgr):
        np_x_1 = numpy.array(meas.ttheta, dtype = float)
        np_y_u_1 = numpy.array(meas.intensity_up, dtype = float)
        np_y_su_1 = numpy.array(meas.intensity_up_sigma, dtype = float)
        np_y_d_1 = numpy.array(meas.intensity_down, dtype = float)
        np_y_sd_1 = numpy.array(meas.intensity_down_sigma, dtype = float)

        if numpy.all(numpy.isnan(np_y_u_1)):
            np_y_s_1 = numpy.array(meas.intensity, dtype = float)
            np_y_ss_1 = numpy.array(meas.intensity_sigma, dtype = float)
            np_y_m_1 = 0*np_y_s_1
            np_y_sm_1 = np_y_ss_1
        else:
            np_y_s_1 = np_y_u_1 + np_y_d_1
            np_y_ss_1 = numpy.sqrt(numpy.square(np_y_su_1) + numpy.square(np_y_sd_1))
            np_y_m_1 = np_y_u_1 - np_y_d_1
            np_y_sm_1 = np_y_ss_1

        np_x_2 = numpy.array(bkgr.ttheta, dtype = float)
        np_y_b_2 = numpy.array(bkgr.intensity, dtype = float)
        np_xys_1 = numpy.vstack((np_x_1, np_y_s_1, np_y_ss_1)).transpose()
        np_xy_1 = numpy.vstack((np_x_1, np_y_s_1)).transpose()
        np_xb_2 = numpy.vstack((np_x_2, 2*np_y_b_2)).transpose()
        w_s_1 = cwidg_pwd()
        w_s_1.plot_numpy_arrays(np_xy_1, np_xys_1, np_xb_2)

        np_xys_1 = numpy.vstack((np_x_1, np_y_m_1, np_y_sm_1)).transpose()
        np_xy_1 = numpy.vstack((np_x_1, np_y_m_1)).transpose()
        w_s_2 = cwidg_pwd()
        w_s_2.plot_numpy_arrays(np_xy_1, np_xys_1)

        np_xys_1 = numpy.vstack((np_x_1, np_y_u_1, np_y_su_1)).transpose()
        np_xy_1 = numpy.vstack((np_x_1, np_y_u_1)).transpose()
        np_xb_2 = numpy.vstack((np_x_2, np_y_b_2)).transpose()
        w_s_3 = cwidg_pwd()
        w_s_3.plot_numpy_arrays(np_xy_1, np_xys_1, np_xb_2)

        np_xys_1 = numpy.vstack((np_x_1, np_y_d_1, np_y_sd_1)).transpose()
        np_xy_1 = numpy.vstack((np_x_1, np_y_d_1)).transpose()
        w_s_4 = cwidg_pwd()
        w_s_4.plot_numpy_arrays(np_xy_1, np_xys_1, np_xb_2)

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
    elif f_meas:
        pass

    return 


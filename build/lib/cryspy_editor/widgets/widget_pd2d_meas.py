import numpy
from PyQt5 import QtWidgets

from .interactive_graph_mod_mono import cwidg_central as cwidg_mono
from .interactive_matrix import cwidg_central as cwidg_matrix

def widget_for_pd2d_meas(obj):
    stack_widg = QtWidgets.QStackedWidget()
    
    lay_to_fill = QtWidgets.QVBoxLayout()
    lay_grid = QtWidgets.QGridLayout()
    lay_grid.addWidget(QtWidgets.QLabel("sum"), 0, 1)
    lay_grid.addWidget(QtWidgets.QLabel("diff."), 0, 2)
    lay_grid.addWidget(QtWidgets.QLabel("up"), 0, 3)
    lay_grid.addWidget(QtWidgets.QLabel("down"), 0, 4)
    lay_grid.addWidget(QtWidgets.QLabel("projection"), 1, 0)
    lay_grid.addWidget(QtWidgets.QLabel("maxtix exp"), 2, 0)
    lay_grid.addWidget(QtWidgets.QLabel("in gamma nu"), 3, 0)


    _rb_1 = QtWidgets.QRadioButton()
    _rb_1.toggled.connect(lambda: stack_widg.setCurrentIndex(0))
    lay_grid.addWidget(_rb_1, 1, 1)
    _rb_1.setChecked(True)
    _rb_2 = QtWidgets.QRadioButton()
    _rb_2.toggled.connect(lambda: stack_widg.setCurrentIndex(1))
    lay_grid.addWidget(_rb_2, 2, 1)

    _rb_3 = QtWidgets.QRadioButton()
    _rb_3.toggled.connect(lambda: stack_widg.setCurrentIndex(2))
    lay_grid.addWidget(_rb_3, 1, 2)
    _rb_4 = QtWidgets.QRadioButton()
    _rb_4.toggled.connect(lambda: stack_widg.setCurrentIndex(3))
    lay_grid.addWidget(_rb_4, 2, 2)

    _rb_5 = QtWidgets.QRadioButton()
    _rb_5.toggled.connect(lambda: stack_widg.setCurrentIndex(4))
    lay_grid.addWidget(_rb_5, 1, 3)
    _rb_6 = QtWidgets.QRadioButton()
    _rb_6.toggled.connect(lambda: stack_widg.setCurrentIndex(5))
    lay_grid.addWidget(_rb_6, 2, 3)

    _rb_7 = QtWidgets.QRadioButton()
    _rb_7.toggled.connect(lambda: stack_widg.setCurrentIndex(6))
    lay_grid.addWidget(_rb_7, 1, 4)
    _rb_8 = QtWidgets.QRadioButton()
    _rb_8.toggled.connect(lambda: stack_widg.setCurrentIndex(7))
    lay_grid.addWidget(_rb_8, 2, 4)

    _rb_9 = QtWidgets.QRadioButton()
    _rb_9.toggled.connect(lambda: stack_widg.setCurrentIndex(8))
    lay_grid.addWidget(_rb_9, 3, 1)

    _rb_10 = QtWidgets.QRadioButton()
    _rb_10.toggled.connect(lambda: stack_widg.setCurrentIndex(9))
    lay_grid.addWidget(_rb_10, 3, 2)

    _rb_11 = QtWidgets.QRadioButton()
    _rb_11.toggled.connect(lambda: stack_widg.setCurrentIndex(10))
    lay_grid.addWidget(_rb_11, 3, 3)

    _rb_12 = QtWidgets.QRadioButton()
    _rb_12.toggled.connect(lambda: stack_widg.setCurrentIndex(11))
    lay_grid.addWidget(_rb_12, 3, 4)




    _lay_1 = QtWidgets.QHBoxLayout()
    _lay_1.addLayout(lay_grid)
    _lay_1.addStretch(1)

    lay_to_fill.addLayout(_lay_1)

    ttheta = obj.ttheta
    phi = obj.phi
    intensity_up = obj.intensity_up
    intensity_up_sigma = obj.intensity_up_sigma
    intensity_down = obj.intensity_down
    intensity_down_sigma = obj.intensity_down_sigma

    x = ttheta
    y = phi

    z_u_e = intensity_up.transpose()
    z_u_s_sq = (intensity_up_sigma.transpose())**2
    _z_1_e = numpy.where(numpy.isnan(z_u_e), 0., z_u_e).sum(axis=0)
    _z_1_s = numpy.sqrt(numpy.where(numpy.isnan(z_u_e), 0., z_u_s_sq).sum(axis=0))
    _n_1 = numpy.where(numpy.isnan(z_u_e), 0., 1.).sum(axis=0)
    z_1_u_e = _z_1_e/_n_1
    z_1_u_s = _z_1_s/_n_1


    z_d_e = intensity_down.transpose()
    z_d_s_sq = (intensity_down_sigma.transpose())**2
    _z_1_e = numpy.where(numpy.isnan(z_d_e), 0., z_d_e).sum(axis=0)
    _z_1_s = numpy.sqrt(numpy.where(numpy.isnan(z_d_e), 0., z_d_s_sq).sum(axis=0))
    _n_1 = numpy.where(numpy.isnan(z_d_e), 0., 1.).sum(axis=0)
    z_1_d_e = _z_1_e/_n_1
    z_1_d_s = _z_1_s/_n_1

    z_sum_e = intensity_up.transpose()+intensity_down.transpose()
    z_sum_s_sq = (intensity_up_sigma.transpose())**2+(intensity_down_sigma.transpose())**2
    _z_1_e = numpy.where(numpy.isnan(z_sum_e), 0., z_sum_e).sum(axis=0)
    _z_1_s = numpy.sqrt(numpy.where(numpy.isnan(z_sum_e), 0., z_sum_s_sq).sum(axis=0))
    _n_1 = numpy.where(numpy.isnan(z_sum_e), 0., 1.).sum(axis=0)
    z_1_sum_e = _z_1_e/_n_1
    z_1_sum_s = _z_1_s/_n_1

    z_diff_e = intensity_up.transpose()-intensity_down.transpose()
    _z_1_e = numpy.where(numpy.isnan(z_diff_e), 0., z_diff_e).sum(axis=0)
    _n_1 = numpy.where(numpy.isnan(z_diff_e), 0., 1.).sum(axis=0)
    z_1_diff_e = _z_1_e/_n_1
    z_1_diff_s = _z_1_s/_n_1

    widg_matrix_u_e = cwidg_matrix()
    widg_matrix_u_e.plot_matrix(x, y, z_u_e)
    widg_proj_u = cwidg_mono()
    widg_proj_u.plot_lines(x, l_y=[z_1_u_e], l_y_sig=[z_1_u_s])

    widg_matrix_d_e = cwidg_matrix()
    widg_matrix_d_e.plot_matrix(x, y, z_d_e)
    widg_proj_d = cwidg_mono()
    widg_proj_d.plot_lines(x, l_y=[z_1_d_e], l_y_sig=[z_1_d_s])

    widg_matrix_sum_e = cwidg_matrix()
    widg_matrix_sum_e.plot_matrix(x, y, z_sum_e)
    widg_proj_sum = cwidg_mono()
    widg_proj_sum.plot_lines(x, l_y=[z_1_sum_e], l_y_sig=[z_1_sum_s])

    widg_matrix_diff_e = cwidg_matrix()
    widg_matrix_diff_e.plot_matrix(x, y, z_diff_e)
    widg_proj_diff = cwidg_mono()
    widg_proj_diff.plot_lines(x, l_y=[z_1_diff_e], l_y_sig=[z_1_diff_s])

    stack_widg.addWidget(widg_proj_sum)
    stack_widg.addWidget(widg_matrix_sum_e)
    stack_widg.addWidget(widg_proj_diff)
    stack_widg.addWidget(widg_matrix_diff_e)
    stack_widg.addWidget(widg_proj_u)
    stack_widg.addWidget(widg_matrix_u_e)
    stack_widg.addWidget(widg_proj_d)
    stack_widg.addWidget(widg_matrix_d_e)


    np_gamma, np_nu, l_int = obj.recalc_to_gamma_nu_grid()
    x_gn, y_gn = np_gamma, np_nu
    z_u_e_gn, z_d_e_gn, z_sum_e_gn, z_diff_e_gn = l_int

    widg_matrix_u_e_gn = cwidg_matrix()
    widg_matrix_u_e_gn.plot_matrix(x_gn, y_gn, z_u_e_gn)
    widg_matrix_d_e_gn = cwidg_matrix()
    widg_matrix_d_e_gn.plot_matrix(x_gn, y_gn, z_d_e_gn)
    widg_matrix_sum_e_gn = cwidg_matrix()
    widg_matrix_sum_e_gn.plot_matrix(x_gn, y_gn, z_sum_e_gn)
    widg_matrix_diff_e_gn = cwidg_matrix()
    widg_matrix_diff_e_gn.plot_matrix(x_gn, y_gn, z_diff_e_gn)

    stack_widg.addWidget(widg_matrix_sum_e_gn)
    stack_widg.addWidget(widg_matrix_diff_e_gn)
    stack_widg.addWidget(widg_matrix_u_e_gn)
    stack_widg.addWidget(widg_matrix_d_e_gn)

    stack_widg.setCurrentIndex(0)

    lay_to_fill.addWidget(stack_widg)

    widg_out = QtWidgets.QWidget()
    widg_out.setLayout(lay_to_fill)

    

    return widg_out


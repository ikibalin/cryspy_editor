import numpy
from PyQt5 import QtWidgets, QtGui, QtCore

def widget_for_diffrn_refln(diffrn_refln):
    lay_to_fill = QtWidgets.QHBoxLayout()

    lay_right = QtWidgets.QVBoxLayout()
    size_pol_2 =  QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
    label_out = QtWidgets.QLabel()
    label_out.setSizePolicy(size_pol_2)
    label_out.setFont(QtGui.QFont("Courier", 8, QtGui.QFont.Normal))
    label_out.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
    area = QtWidgets.QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(label_out)
    lay_right.addWidget(area)

    lay_left = QtWidgets.QVBoxLayout()

    n_row, n_col = len(diffrn_refln.h), 5
    l_name = ["h", "k", "l", "fr", "fr_sigma"]
    _i_row = 0
    l_add = n_row*[None]
    if diffrn_refln.fr_calc is not None:
        if len(diffrn_refln.fr_calc) == n_row:
            l_add  = diffrn_refln.fr_calc
            n_col = 6
            l_name = ["h", "k", "l", "fr", "fr_sigma", "fr_calc"]
    w_t = QtWidgets.QTableWidget(n_row, n_col)
    w_t.setHorizontalHeaderLabels(l_name)
        
    for _h, _k, _l, _fr, _fr_sigma, _fr_calc in zip(diffrn_refln.h, diffrn_refln.k, 
                                               diffrn_refln.l, diffrn_refln.fr, diffrn_refln.fr_sigma, l_add): 
        _w_ti_0 = QtWidgets.QTableWidgetItem()
        _w_ti_0.setText(str(_h))
        _w_ti_1 = QtWidgets.QTableWidgetItem()
        _w_ti_1.setText(str(_k))
        _w_ti_2 = QtWidgets.QTableWidgetItem()
        _w_ti_2.setText(str(_l))
        _w_ti_3 = QtWidgets.QTableWidgetItem()
        _w_ti_3.setText(f"{_fr:.5f}")
        _w_ti_4 = QtWidgets.QTableWidgetItem()
        _w_ti_4.setText(f"{_fr_sigma:.5f}")
        w_t.setItem(_i_row, 0, _w_ti_0)
        w_t.setItem(_i_row, 1, _w_ti_1)
        w_t.setItem(_i_row, 2, _w_ti_2)
        w_t.setItem(_i_row, 3, _w_ti_3)
        w_t.setItem(_i_row, 4, _w_ti_4)
        if _fr_calc is not None:
            _w_ti_5 = QtWidgets.QTableWidgetItem()
            _w_ti_5.setText(f"{_fr_calc:.5f}")
            w_t.setItem(_i_row, 5, _w_ti_5)
        _i_row += 1
    lay_left.addWidget(w_t)


    _b_chi_sq = QtWidgets.QPushButton("calc_chi_sq")
    _b_chi_sq.clicked.connect(lambda : calc_chi_sq(diffrn_refln, label_out))
    lay_left.addWidget(_b_chi_sq)


    _b_info = QtWidgets.QPushButton("info")
    _b_info.clicked.connect(lambda : show_info(diffrn_refln, label_out))
    lay_left.addWidget(_b_info)


    lay_to_fill.addLayout(lay_left)
    lay_to_fill.addLayout(lay_right)
    widg_out = QtWidgets.QWidget()
    widg_out.setLayout(lay_to_fill)
    
    return widg_out

def show_info(diffrn_refln, label):
    label.setText(str(diffrn_refln))

def calc_chi_sq(diffrn_refln, label):
    ls_out = []
    if diffrn_refln.fr_calc is not None:
        _e = numpy.array(diffrn_refln.fr, dtype=float)
        _s = numpy.array(diffrn_refln.fr_sigma, dtype=float)
        _m = numpy.array(diffrn_refln.fr_calc, dtype=float)
        _t = ((_e-_m)/_s)**2
        _n = int((numpy.logical_not(numpy.isnan(_t))).sum())
        chi_sq =  numpy.nansum(_t)
        chi_sq_n = chi_sq/float(_n)
        ls_out.append(f"Number of reflections is {_n:}.")
        ls_out.append(f"Chi_sq per n is {chi_sq_n:.2f}.")
    else:
        ls_out.append(f"Number of reflections is {len(diffrn_refln.fr):}")
        ls_out.append("fr_calc is not defined")
    label.setText("\n".join(ls_out))

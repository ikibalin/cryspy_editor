import numpy
from PyQt5 import QtWidgets, QtGui, QtCore
from .FUNCTIONS import show_info

def widget_for_meas_elasticl(obj):
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

    n_row, n_col = len(obj.moment_11), 1
    l_name = ["moment_11"]
    _i_row = 0
    l_add = n_row*[None]
    if obj.moment_11_calc is not None:
        if len(obj.moment_11_calc) == n_row:
            l_add  = obj.moment_11_calc
            n_col = 2
            l_name = ["moment_11", "moment_11_calc"]
    w_t = QtWidgets.QTableWidget(n_row, n_col)
    w_t.setHorizontalHeaderLabels(l_name)
        
    for _0, _1 in zip(obj.moment_11, l_add): 
        _w_ti_0 = QtWidgets.QTableWidgetItem()
        _w_ti_0.setText(str(_0))
        w_t.setItem(_i_row, 0, _w_ti_0)
        if _1 is not None:
            _w_ti_1 = QtWidgets.QTableWidgetItem()
            _w_ti_1.setText(f"{_1:.5f}")
            w_t.setItem(_i_row, 1, _w_ti_1)
        _i_row += 1
    lay_left.addWidget(w_t)



    _b_info = QtWidgets.QPushButton("info")
    _b_info.clicked.connect(lambda : show_info(obj, label_out))
    lay_left.addWidget(_b_info)


    lay_to_fill.addLayout(lay_left)
    lay_to_fill.addLayout(lay_right)
    widg_out = QtWidgets.QWidget()
    widg_out.setLayout(lay_to_fill)
    
    return widg_out

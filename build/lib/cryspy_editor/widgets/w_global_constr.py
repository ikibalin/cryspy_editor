import os
import numpy
from PyQt5 import QtWidgets, QtGui, QtCore

from cryspy_editor.b_rcif_to_cryspy import L_ITEM_CLASS, L_LOOP_CLASS, L_DATA_CLASS
from .FUNCTIONS import show_info, get_layout_method_help, add_mandatory_optional_obj, make_qtablewidget_for_data_constr, show_widget

def w_for_global_constr(obj, layout_11, layout_12, layout_13, layout_2, layout_3, w_output, thread):

    layout_11.addWidget(QtWidgets.QLabel("Global name:"))
    _l_e_dist = QtWidgets.QLineEdit()
    _l_e_dist.setText(obj.global_name)
    _l_e_dist.editingFinished.connect(lambda : setattr(obj, "global_name", _l_e_dist.text()))
    layout_11.addWidget(_l_e_dist)

    
    layout_11.addWidget(QtWidgets.QLabel("Defined attributes:"))
    _widg_table = make_qtablewidget_for_data_constr(obj, w_output, thread)
    layout_11.addWidget(_widg_table)


    _b_info = QtWidgets.QPushButton("info")
    _b_info.clicked.connect(lambda : show_info(obj, w_output))
    layout_11.addWidget(_b_info)

    layout_12.addLayout(add_mandatory_optional_obj(obj, w_output, thread))

    layout_13.addLayout(get_layout_method_help(obj, w_output, thread))

    _text_edit = QtWidgets.QTextEdit()
    _text_edit.setText(obj.to_cif())
    layout_2.addWidget(_text_edit)

    return


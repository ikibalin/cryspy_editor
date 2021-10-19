from .FUNCTIONS import make_qtablewidget_for_item_constr, show_info, get_layout_method_help, \
    get_layout_internal_attribute, get_layout_rciftab_obj

from PyQt5 import QtWidgets, QtGui, QtCore


def w_for_item_constr(obj, layout_11, layout_12, layout_13, layout_2, layout_3, w_output, thread):
    layout_11.addWidget(QtWidgets.QLabel("Mandatory and optional attributes"))
    w_t = make_qtablewidget_for_item_constr(obj, label=w_output)
    layout_11.addWidget(w_t)

    _b_info = QtWidgets.QPushButton("info")
    _b_info.clicked.connect(lambda: show_info(obj, w_output))
    layout_11.addWidget(_b_info)

    lay_left_2 = get_layout_internal_attribute(obj, w_output)
    layout_12.addLayout(lay_left_2)

    lay_left_3 = get_layout_method_help(obj, w_output, thread)
    layout_13.addLayout(lay_left_3)


    _lay_3 = get_layout_rciftab_obj(obj, thread)
    layout_2.addLayout(_lay_3)
    return

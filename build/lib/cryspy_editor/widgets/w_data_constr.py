import os
import numpy
from PyQt5 import QtWidgets, QtGui, QtCore
from cryspy_editor.b_rcif_to_cryspy import L_ITEM_CLASS, L_LOOP_CLASS, L_DATA_CLASS
from .FUNCTIONS import show_info, get_layout_method_help,  make_qtablewidget_for_data_constr, show_widget, add_mandatory_optional_obj

from cryspy.common.cl_item_constr import ItemConstr
from cryspy.common.cl_loop_constr import LoopConstr


def w_for_data_constr(obj, layout_11, layout_12, layout_13, layout_2, layout_3, w_output, thread):


    layout_11.addWidget(QtWidgets.QLabel("Data name:"))
    _l_e_dist = QtWidgets.QLineEdit()
    _l_e_dist.setText(obj.data_name)
    _l_e_dist.editingFinished.connect(lambda : setattr(obj, "data_name", _l_e_dist.text()))
    layout_11.addWidget(_l_e_dist)

    layout_11.addWidget(QtWidgets.QLabel("Defined attributes:"))
    _widg_table = make_qtablewidget_for_data_constr(obj, w_output, thread)
    layout_11.addWidget(_widg_table)

    _b_info = QtWidgets.QPushButton("info")
    _b_info.clicked.connect(lambda : show_info(obj, w_output))
    layout_11.addWidget(_b_info)

    lay_left_2 = add_mandatory_optional_obj(obj, w_output, thread)
    layout_12.addLayout(lay_left_2)

    lay_left_3 = get_layout_method_help(obj, w_output, thread)
    layout_13.addLayout(lay_left_3)


    _text_edit = QtWidgets.QTextEdit()
    _text_edit.setText(obj.to_cif())
    layout_2.addWidget(_text_edit)

    return


def create_obj(widg, obj):
    ls_out = ["Enter the item:"]
    l_class = obj.mandatory_classes+obj.optional_classes
    
    n_mandatory = len(obj.mandatory_classes)

    l_h = []
    for _class in l_class:
        if isinstance(_class, ItemConstr):
            l_h.append(_class.PREFIX, _class)
        elif isinstance(_class, LoopConstr):
            l_h.append(_class.ITEM_CLASS.PREFIX, _class)

    ls_out.extend([f"{_i+1}: {_h[0]:}" for _i, _h in enumerate(l_h)])

    text, ok = QtWidgets.QInputDialog.getText(widg, 'Input Dialog',
                            "\n".join(ls_out))
    if not(ok):
        return None

    _ind = int(text)-1
    item_class = l_h[_ind][1]
    item = item_class()
    if _ind >= n_mandatory:
        obj.optional_objs.append(item)
    else:
        obj.mandatory_objs.append(item)

def create_items(widg, obj):
    ls_out = ["Enter the item:"]
    ls_out.extend([f"{_i+1}: {_item.PREFIX:}" for _i, _item in enumerate(L_ITEM_CLASS)])

    text, ok = QtWidgets.QInputDialog.getText(widg, 'Input Dialog',
                            "\n".join(ls_out))
    if not(ok):
        return None

    _ind = int(text)-1
    item_class = L_ITEM_CLASS[_ind]
    item = item_class()
    if not(item_class in obj.mandatory_classes+obj.optional_classes):
        obj.optional_classes.append(item_class)
    obj.optional_objs.append(item)
    

def create_loop(widg, obj):
    ls_out = ["Enter the loop:"]
    ls_out.extend([f"{_i+1}: {_item.ITEM_CLASS.PREFIX:}" for _i, _item in enumerate(L_LOOP_CLASS)])

    text, ok = QtWidgets.QInputDialog.getText(widg, 'Input Dialog',
                            "\n".join(ls_out))
    if not(ok):
        return None

    _ind = int(text)-1
    loop_class = L_LOOP_CLASS[_ind]
    loop = loop_class()
    if not(loop_class in obj.mandatory_classes+obj.optional_classes):
        obj.optional_classes.append(loop_class)
    obj.optional_objs.append(loop)

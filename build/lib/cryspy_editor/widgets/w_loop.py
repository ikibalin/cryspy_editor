from .FUNCTIONS import make_qtablewidget_for_loop, show_info, show_variables, show_help, \
    get_layout_method_help, del_layout, show_widget, get_layout_rciftab_obj, \
    get_layout_internal_attribute

from PyQt5 import QtWidgets, QtGui, QtCore


def w_for_loop(obj, layout_11, layout_12, layout_13, layout_2, layout_3, w_output, thread):
    layout_11.addWidget(QtWidgets.QLabel("Loop name:"))

    _l_e_dist = QtWidgets.QLineEdit()
    _l_e_dist.setText(obj.name)
    _l_e_dist.editingFinished.connect(lambda: setattr(obj, "loop_name", _l_e_dist.text()))
    layout_11.addWidget(_l_e_dist)

    w_t = make_qtablewidget_for_loop(obj, label=w_output)
    layout_11.addWidget(w_t, 2)

    lay_left_11 = QtWidgets.QHBoxLayout()
    #_b_add = QtWidgets.QPushButton("add/delete item")
    #lay_left_11.addWidget(_b_add)

    #_b_show_item = QtWidgets.QPushButton("show item")
    #lay_left_11.addWidget(_b_show_item)

    _b_info = QtWidgets.QPushButton("info")
    _b_info.clicked.connect(lambda:  w_output.setText(str(obj)))
    lay_left_11.addWidget(_b_info)
    layout_11.addLayout(lay_left_11)


    _lay_3 = get_layout_rciftab_obj(obj, thread)
    layout_2.addLayout(_lay_3)

    #_b_show_item.clicked.connect(lambda: show_item_in_loop(obj, w_t.selectedRanges(), layout_3, w_output, thread))
    return


"""
def plot_graph(qtablewidget, widg_graph_1d):
    selected_items = qtablewidget.selectedItems()
    print("selected_items")
    l_col = [_h.column() for _h in selected_items]
    if len(l_col) == 0:
        return
    columns = set(l_col)
    column_min = min(columns)
    columns_y = sorted(columns-set([column_min]))

    try:
        x = [float(_h.text()) for _h in selected_items if _h.column()==column_min]
    except:
        return None
    l_y = []
    for _column in columns_y:
        try:
            y = [float(_h.text()) for _h in selected_items if _h.column()==_column]
            l_y.append(y)
        except:
            pass
    xy_s =  sorted(zip(x, *l_y), key=lambda _: _[0])
    
    x = list(zip(*xy_s))[0]
    if len(l_y) >= 1:
        l_y = list(zip(*xy_s))[1:]
        widg_graph_1d.plot_lines(x, l_y=l_y)
    else:
        widg_graph_1d.plot_lines(range(len(x)), l_y==[x])
"""


def add_del_item_in_loop(widg, obj):
    ls_out = ["Enter the number of items:"]

    text, ok = QtWidgets.QInputDialog.getText(widg, 'Input Dialog',
                                              "\n".join(ls_out))
    if not (ok):
        return None

    _ind = int(text)
    l_item = obj.item
    if len(l_item) <= _ind:
        _item_class = obj.ITEM_CLASS
        for _i in range(_ind - len(l_item)):
            l_item.append(_item_class())
    elif len(l_item) > _ind:
        l_item_new = l_item[:(_ind + 1)]
        obj.item = l_item_new


def show_item_in_loop(obj, selected_ranges, layout, w_output, thread):
    del_layout(layout)
    row = None
    item = None
    if len(selected_ranges) >= 1:
        row = selected_ranges[0].topRow()
    if row is not None:
        if len(obj.item) > row:
            item = obj.item[row]
    if item is not None:

        l_11 = QtWidgets.QVBoxLayout()
        l_12 = QtWidgets.QVBoxLayout()
        l_13 = QtWidgets.QVBoxLayout()
        l_2 = QtWidgets.QVBoxLayout()
        l_3 = QtWidgets.QVBoxLayout()
        w_for_item_constr(item, l_11, l_12, l_13, l_2, l_3, w_output, thread)
        lay_main = QtWidgets.QHBoxLayout()
        lay_main.addLayout(l_11)
        lay_main.addLayout(l_12)
        lay_main.addLayout(l_13)

        layout.addLayout(lay_main)

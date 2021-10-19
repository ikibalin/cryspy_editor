import numpy
from PyQt5 import QtWidgets, QtGui, QtCore
from types import FunctionType
from cryspy import Fitable
from cryspy import GlobalConstr
from cryspy import DataConstr, LoopConstr, ItemConstr
from pycifstar import Global, Data, Loop, Item


from cryspy_editor.b_rcif_to_cryspy import L_ITEM_CLASS, L_LOOP_CLASS, L_DATA_CLASS

def temp_func_loop(qt_table, i_row, i_col, obj, l_ii):
    table_item = qt_table.item(i_row, i_col)
    val = str(table_item.text())
    l_attr = obj.ITEM_CLASS.MANDATORY_ATTRIBUTE + obj.ITEM_CLASS.OPTIONAL_ATTRIBUTE
    setattr(obj.item[i_row], l_attr[l_ii[i_col]], val)
    return

def temp_func_loop_help(qt_table, i_row, i_col, obj, l_ii, label):
    table_item = qt_table.item(i_row, i_col)
    val = str(table_item.text())
    l_attr = obj.ITEM_CLASS.MANDATORY_ATTRIBUTE + obj.ITEM_CLASS.OPTIONAL_ATTRIBUTE
    if (label is not None):
        label.setText(get_help_for_attribute(obj.item[i_row], l_attr[l_ii[i_col]]))
    return

def temp_func_item_constr(qt_table, i_row, i_col, obj, l_ii):
    table_item = qt_table.item(i_row, i_col)
    val = str(table_item.text())
    l_attr = obj.MANDATORY_ATTRIBUTE + obj.OPTIONAL_ATTRIBUTE
    if i_col == 1:
        setattr(obj, l_attr[l_ii[i_row]], val)
    return

def temp_func_item(qt_table, i_row, i_col, obj, l_ii):
    table_item = qt_table.item(i_row, i_col)
    val = str(table_item.text())
    if i_col == 1:
        setattr(obj, "value", val)
    return

def temp_func_item_help(qt_table, i_row, i_col, obj, l_ii, label):
    table_item = qt_table.item(i_row, i_col)
    val = str(table_item.text())
    l_attr = obj.MANDATORY_ATTRIBUTE + obj.OPTIONAL_ATTRIBUTE
    if (label is not None):
        label.setText(get_help_for_attribute(obj, l_attr[l_ii[i_row]]))
    return


def make_qtablewidget_for_loop(obj, label=None):

    l_ii, l_attr_sh = [], obj.names
    if l_attr_sh is None:
        return  QtWidgets.QTableWidget(0, 0)

    n_row, n_col = len(obj.values), len(l_attr_sh)
    w_t = QtWidgets.QTableWidget(n_row, n_col)
    l_name = l_attr_sh

    for _i_attr, _attr in enumerate(l_attr_sh):
        _item_header = QtWidgets.QTableWidgetItem(_attr)
        w_t.setHorizontalHeaderItem(_i_attr, _item_header)

    _i_row = 0
    for _i_row, _item in enumerate(obj.values):
        for _i, _attr in enumerate(l_attr_sh):
            _1 = _item[_i]
            _w_ti_0 = QtWidgets.QTableWidgetItem()
            _w_ti_0.setText(str(_1))
            w_t.setItem(_i_row, _i, _w_ti_0)

    #w_t.cellChanged.connect(lambda _1, _2: temp_func_loop(w_t, _1, _2, obj, l_ii))
    return w_t


def make_qtablewidget_for_loop_constr(obj, label=None):
    l_attr = obj.ITEM_CLASS.MANDATORY_ATTRIBUTE + obj.ITEM_CLASS.OPTIONAL_ATTRIBUTE
    l_flag_mandatory = len(obj.ITEM_CLASS.MANDATORY_ATTRIBUTE)*[True]+len(obj.ITEM_CLASS.OPTIONAL_ATTRIBUTE)*[False]
    if len(obj.item)==0:
        n_row, n_col = 0, len(l_attr)
        w_t = QtWidgets.QTableWidget(n_row, n_col)
        for _i_attr, _attr in enumerate(l_attr):
            _item_header = QtWidgets.QTableWidgetItem(_attr)
            if l_flag_mandatory[_i_attr]:
                _item_header.setBackground(QtGui.QColor(255, 255, 240))#Ivory
            else:
                _item_header.setBackground(QtGui.QColor(255, 255, 255))#White
            w_t.setHorizontalHeaderItem(_i_attr, _item_header)
        return w_t

    _item = obj.item[0]
    l_ii, l_attr_sh = [], []
    l_flag_m_sh = []
    for _i, _attr in enumerate(l_attr):
        if getattr(_item, _attr) is not None:
            l_ii.append(_i) 
            l_attr_sh.append(_attr)
            l_flag_m_sh.append(l_flag_mandatory[_i])

    if len(l_attr_sh) == 0:
        l_attr_sh = l_attr
        l_ii = [_i for _i in range(len(l_attr))]

    n_row, n_col = len(obj.item), len(l_attr_sh)
    w_t = QtWidgets.QTableWidget(n_row, n_col)
    l_name = l_attr_sh


    for _i_attr, _attr in enumerate(l_attr_sh):
        _item_header = QtWidgets.QTableWidgetItem(_attr)
        if l_flag_m_sh[_i_attr]:
            _item_header.setBackground(QtGui.QColor(255, 255, 240))#Ivory
        else:
            _item_header.setBackground(QtGui.QColor(255, 255, 255))#White
        w_t.setHorizontalHeaderItem(_i_attr, _item_header)


    _i_row = 0
    for _i_row, _item in enumerate(obj.item):
        for _i, _attr in enumerate(l_attr_sh):
            _1 = getattr(_item, _attr)
            _w_ti_0 = QtWidgets.QTableWidgetItem()
            _w_ti_0.setToolTip(get_help_for_attribute(_item, _attr))
            if isinstance(_1, float):
                _w_ti_0.setText(str(round(_1, 5)))
            elif isinstance(_1, Fitable):
                if _1.refinement:
                    _w_ti_0.setText(str(_1))
                else:
                    _w_ti_0.setText(str(round(float(_1), 5)))
            else:
                _w_ti_0.setText(str(_1))
            w_t.setItem(_i_row, _i, _w_ti_0)

    w_t.cellChanged.connect(lambda _1, _2: temp_func_loop(w_t, _1, _2, obj, l_ii))
    return w_t

def make_qtablewidget_for_item(obj, label=None):
    l_attr_sh = [obj.name]
    l_flag_m_sh = [True]
    n_row, n_col = len(l_attr_sh), 2
    w_t = QtWidgets.QTableWidget(n_row, n_col)

    l_ii = [0]
    l_name = l_attr_sh
    w_t.setHorizontalHeaderLabels(["name", "value"])
    w_t.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
    _i_row = 0
    for _i_row, _attr in enumerate(l_attr_sh):
        _w_ti_0 = QtWidgets.QTableWidgetItem()
        _w_ti_0.setText(str(_attr))
        w_t.setItem(_i_row, 0, _w_ti_0)
        _1 = obj.value
        _w_ti_1 = QtWidgets.QTableWidgetItem()
        _w_ti_1.setText(str(_1))
        if l_flag_m_sh[_i_row]:
            _w_ti_0.setBackground(QtGui.QColor(255, 255, 240))#Ivory
            _w_ti_1.setBackground(QtGui.QColor(255, 255, 240))
        else:
            _w_ti_0.setBackground(QtGui.QColor(255, 255, 255))#White
            _w_ti_1.setBackground(QtGui.QColor(255, 255, 255))

        w_t.setItem(_i_row, 1, _w_ti_1)
    w_t.cellChanged.connect(lambda _1, _2: temp_func_item(w_t, _1, _2, obj, l_ii))
    w_t.setVerticalHeaderLabels(n_row*[""])
    return w_t


def make_qtablewidget_for_item_constr(obj, label=None):
    l_attr = obj.MANDATORY_ATTRIBUTE + obj.OPTIONAL_ATTRIBUTE
    l_flag_mandatory = len(obj.MANDATORY_ATTRIBUTE)*[True]+len(obj.OPTIONAL_ATTRIBUTE)*[False]
    l_ii, l_attr_sh = [], []
    l_flag_m_sh = []
    l_ii_end, l_attr_sh_end = [], []
    l_flag_m_sh_end = []
    for _i, _attr in enumerate(l_attr):
        if getattr(obj, _attr) is not None:
            l_ii.append(_i) 
            l_attr_sh.append(_attr)
            l_flag_m_sh.append(l_flag_mandatory[_i])
        else:
            l_ii_end.append(_i)
            l_attr_sh_end.append(_attr)
            l_flag_m_sh_end.append(l_flag_mandatory[_i])

    l_ii.extend(l_ii_end)
    l_attr_sh.extend(l_attr_sh_end)
    l_flag_m_sh.extend(l_flag_m_sh_end)

    n_row, n_col = len(l_attr_sh), 2
    w_t = QtWidgets.QTableWidget(n_row, n_col)
    l_name = l_attr_sh
    w_t.setHorizontalHeaderLabels(["name", "value"])
    w_t.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
    _i_row = 0
    for _i_row, _attr in enumerate(l_attr_sh):
        _w_ti_0 = QtWidgets.QTableWidgetItem()
        _w_ti_0.setText(str(_attr))
        w_t.setItem(_i_row, 0, _w_ti_0)
        _1 = getattr(obj, _attr)
        _w_ti_0.setToolTip(get_help_for_attribute(obj, _attr))
        _w_ti_1 = QtWidgets.QTableWidgetItem()
        _w_ti_1.setToolTip(_1.__doc__)
        _w_ti_1.setText(str(_1))
        _w_ti_1.setToolTip(get_help_for_attribute(obj, _attr))
        if l_flag_m_sh[_i_row]:
            _w_ti_0.setBackground(QtGui.QColor(255, 255, 240))#Ivory
            _w_ti_1.setBackground(QtGui.QColor(255, 255, 240))
        else:
            _w_ti_0.setBackground(QtGui.QColor(255, 255, 255))#White
            _w_ti_1.setBackground(QtGui.QColor(255, 255, 255))

        w_t.setItem(_i_row, 1, _w_ti_1)
    w_t.cellChanged.connect(lambda _1, _2: temp_func_item_constr(w_t, _1, _2, obj, l_ii))
    w_t.setVerticalHeaderLabels(n_row*[""])
    return w_t


def make_qtablewidget_for_data_constr(obj, label, thread):
    l_data_obj = obj.mandatory_objs + obj.optional_objs
    l_ii, l_obj_sh = [], []

    l_obj_sh = l_data_obj
    l_ii = [_i for _i in range(len(l_data_obj))]

    n_row, n_col = len(l_obj_sh)+1, 1
    w_t = QtWidgets.QTableWidget(n_row, n_col)
    
    w_t.setHorizontalHeaderLabels(["name"])
    w_t.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
    for _i_row, _obj in enumerate(l_obj_sh):
        _w_ti_0 = QtWidgets.QTableWidgetItem()
        s_val = str(type(_obj).__name__)
        if isinstance(_obj, GlobalConstr): 
            s_val += f": {_obj.global_name:}"
        elif isinstance(_obj, DataConstr): 
            s_val += f": {_obj.data_name:}"
        elif isinstance(_obj, LoopConstr): 
            s_val += f": {_obj.loop_name:}"
        _w_ti_0.setText(s_val)
        _w_ti_0.setToolTip(_obj.__doc__)
        _w_ti_0.setCheckState(0)
        w_t.setItem(_i_row, 0, _w_ti_0)
    pb_del = QtWidgets.QPushButton("Delete")
    w_t.setCellWidget(n_row-1, 0, pb_del)
    
    w_t.setVerticalHeaderLabels(n_row*[""])
    pb_del.clicked.connect(lambda : del_obj_by_table(w_t, obj, thread))
    return w_t

def del_obj_by_table(table_widget, obj, thread):
    n_mandatory = len(obj.mandatory_objs)
    n_optional = len(obj.optional_objs)
    n_row = table_widget.rowCount()
    l_del = []
    l_ind = []
    for i_row in range(n_row-1):
        val = 0
        flag=False
        _table_item =  table_widget.item(i_row, 0)
        if _table_item is not None:
            l_ind.append(i_row)
            val = _table_item.checkState()
        if val == 2: flag = True
        l_del.append(flag)
    for _1, _2 in zip(range((n_row-2), -1, -1), reversed(l_del)):
        if _2:
            table_widget.takeItem(_1, 0)
            _ind = l_ind.index(_1)
            if _ind < n_mandatory:
                n_mandatory -= 1
                obj.mandatory_objs.pop(_ind)
            else:
                n_optional -= 1
                obj.optional_objs.pop(_ind-n_mandatory)
    thread.signal_refresh.emit()   

def show_info(obj, label):
    if obj.is_defined:
        obj.form_object
    label.setText(str(obj))

def show_variables(obj, label):
    if obj.is_defined:
        obj.form_object
    ls_str= [f"Variables:\n"]
    l_variable = obj.get_variables()
    for _ind, _variable in enumerate(l_variable):
        ls_str.append(f"({_ind+1:}) {str(_variable):}")
    label.setText("\n".join(ls_str))

def show_help(obj, label):
    ls_out = []
    ls_out.append(str(obj.__doc__))
    label.setText("\n".join(ls_out))

def get_help_for_attribute(obj, attribute):
    ls_out = []
    obj_class = type(obj)
    try:
        func = getattr(obj_class, attribute)
        if isinstance(func, FunctionType):
            l_param = [ _ for _ in func.__code__.co_varnames[:func.__code__.co_argcount] if _ != "self"]
            if len(l_param) > 0:
                ls_out.append("INPUT PARAMETERS: \n"+ "\n".join(l_param))
            else:
                ls_out.append("NO INPUT PARAMETERS.")
            if func.__defaults__ is not None:
                ls_out.append("\nDEFAULT PARAMETERS: \n" + "\n".join([str(_) for _ in func.__defaults__]))
            #print("func.__kwdefaults__: ", func.__kwdefaults__)
            #print("func.__code__.co_kwonlyargcount: ", func.__code__.co_kwonlyargcount)
        ls_out.append(70*"*")
        val = func.__doc__
        if val is not None:
            ls_out.append(val)
        else:
            ls_out.append("Documentation is not written")
    except:
        ls_out.append("It's not found.")
    return "\n".join(ls_out)

def get_method_list(obj):
    _cls = type(obj)
    l_method = [_1 for _1, _2 in _cls.__dict__.items() if ((type(_2) == FunctionType) & (not(_1.startswith("_"))))]
    l_method.sort()
    return l_method

def get_layout_method_help(obj, label_out, thread):
    _lay = QtWidgets.QVBoxLayout()
    
    l_method = get_method_list(obj)

    if len(l_method) != 0:
        obj_class = type(obj)
        _label = QtWidgets.QLabel("Methods (double click to do): ")
        _lay.addWidget(_label)

        _list_widget = QtWidgets.QListWidget()
        qfont = QtGui.QFont()
        qfont.setBold(True)
        for _method in l_method:
            func = getattr(obj_class, _method)
            l_param = [_ for _ in func.__code__.co_varnames[:func.__code__.co_argcount] if _ != "self"]
            s_par = ""
            if len(l_param) > 0:
                s_par = ", ".join(l_param)
            s_val = f"{_method:}({s_par:})"

            _list_widget_item = QtWidgets.QListWidgetItem(s_val)
            _list_widget_item.setFont(qfont)
            _list_widget_item.setToolTip(get_help_for_attribute(obj, _method))
            _list_widget.addItem(_list_widget_item)
        _list_widget.setSortingEnabled(True)
        _lay.addWidget(_list_widget)
        table_widget_1 = QtWidgets.QTableWidget()
        table_widget_1.setHorizontalHeaderLabels(["name", "value"])
        table_widget_1.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        table_widget_1.hide()
        _lay.addWidget(table_widget_1)

        _list_widget.doubleClicked.connect(lambda : do_obj_func(obj, _list_widget.currentItem().text().split("(")[0], table_widget_1, label_out, thread))
    return _lay

def do_obj_func(obj, func_name, table_widget, label, thread):
    ls_out = []
    func = getattr(obj, func_name)
    if (func.__code__.co_argcount == 1):
        #res = func()
        ls_out.append("Calculations are started")
        thread.function = func
        thread.arguments = ()
        thread.start()
        table_widget.hide()
    else: 
        flag = False
        if flag:
            ls_out.append("Function is performed with default parameters:\n")
            ls_out.append(str(res))
            table_widget.hide()
        else:
            table_widget.show()
            n_row_need = (func.__code__.co_argcount-1) 
            n_row = table_widget.rowCount()
            flag_read = n_row_need==n_row

            l_var_names = func.__code__.co_varnames[1:(n_row_need+1)]

            if flag_read:
                flag_read = all([str(table_widget.item(_i_row, 0).text()) == _2 for _i_row, _2 in zip(range(n_row), l_var_names)])
                flag_read_2 = all([str(table_widget.item(_i_row, 1).text()) != "" for _i_row in range(n_row)])
                flag_read = flag_read & flag_read_2

            if func.__defaults__ is None:
                n_defaults = 0
            else:
                n_defaults = len(func.__defaults__)
            n_var_names = len(l_var_names)
            
            if not(flag_read):
                table_widget.setColumnCount(2)
                table_widget.setRowCount(n_row_need)
                for _i, _name in enumerate(l_var_names):
                    t_w_i_1 = table_widget.item(_i, 0)
                    if t_w_i_1 is None:
                        t_w_i_1 = QtWidgets.QTableWidgetItem()
                        table_widget.setItem(_i, 0, t_w_i_1)
                    t_w_i_1.setText(_name)
                    t_w_i_2 = table_widget.item(_i, 1)
                    if t_w_i_2 is None:
                        t_w_i_2 = QtWidgets.QTableWidgetItem()
                        table_widget.setItem(_i, 1, t_w_i_2)
                    i_default = _i-(n_var_names-n_defaults)
                    if i_default >= 0:
                        t_w_i_2.setText(str(func.__defaults__[i_default]))

                ls_out.append("Introduce the input parameters in the table.")
            else:
                l_var_in = []
                for _i, _name in enumerate(l_var_names):
                    s_val = table_widget.item(_i, 1).text()
                    try:
                        e_val = eval(s_val)
                        if isinstance(e_val, (str, list, tuple, float, int)):
                            val_in = numpy.array(e_val, dtype=float)
                        else:
                            val_in = e_val
                    except:
                        val_in = s_val.strip()
                    if s_val == "None":
                        val_in = None
                    l_var_in.append(val_in)
                t_var_in = tuple(l_var_in)

                ls_out.append("Calculations are started")
                thread.function = func
                thread.arguments = t_var_in
                thread.start()

    label.setText("\n".join(ls_out))

def get_layout_internal_attribute(obj, label_out):
    _lay = QtWidgets.QVBoxLayout()
    
    l_attr_name = obj.INTERNAL_ATTRIBUTE
    if l_attr_name is None:
        return _lay
    l_attr_name = list(l_attr_name)
    l_attr_name.sort()
    if len(l_attr_name) != 0:
        _label = QtWidgets.QLabel("Internal attributes: ")
        _lay.addWidget(_label)

        _list_widget = QtWidgets.QListWidget()
        for _attr_name in l_attr_name:
            val = str(getattr(obj, _attr_name))
            if isinstance(val, float):
                s_val = f"{_attr_name:}: {round(val, 5):}"
            elif isinstance(val, Fitable):
                if val.refinement:
                    s_val = f"{_attr_name:}: {str(val):}"
                else:
                    s_val = f"{_attr_name:}: {round(float(val), 5):}"
            elif len(str(val).split("\n")) > 1:
                s_val = f"{_attr_name:}: ..."
            elif len(str(val)) > 10:
                try:
                    s_val = f"{_attr_name:}: {round(float(val), 5):}"
                except:
                    s_val = f"{_attr_name:}: {str(val)[:7]:}..."
            else:
                s_val = f"{_attr_name:}: {str(val):}"

            _list_widget_item = QtWidgets.QListWidgetItem(s_val)
            _list_widget_item.setToolTip(get_attribute_with_help(obj, _attr_name))
            _list_widget.addItem(_list_widget_item)
        _list_widget.itemDoubleClicked.connect(lambda _1: label_out.setText(get_attribute_with_help(obj, _1.text().split(":")[0])))
        _lay.addWidget(_list_widget)
    
    return _lay

def get_attribute_with_help(obj, attribute):
    ls_out = []
    ls_out.append(f"{attribute:}:\n")
    ls_out.append(str(getattr(obj, attribute)))
    ls_out.append("\n"+50*"*"+"\n")
    ls_out.append(get_help_for_attribute(obj, attribute))
    return "\n".join(ls_out)


def del_layout(layout):
    """
delete all elements from layouts
    """
    for i in reversed(range(layout.count())):
        if layout.itemAt(i).widget() != None:
           layout.itemAt(i).widget().setParent(None)
        elif layout.itemAt(i).layout() != None:
            del_layout(layout.itemAt(i).layout())
            layout.itemAt(i).layout().setParent(None)
        else:
            layout.removeItem(layout.itemAt(i))
    return


def show_widget(widget, state):
    if int(state) == 0:
        widget.hide()
    else:
        widget.show()


def add_mandatory_optional_obj(obj, label, thread):
    """
layout to add new attributes for DataConstr or GlobalConstr
    """
    layout = QtWidgets.QVBoxLayout()
    layout.addWidget(QtWidgets.QLabel("Add attribute:"))


    if type(obj) == GlobalConstr:
        l_cls = L_ITEM_CLASS + L_LOOP_CLASS + L_DATA_CLASS
        l_flag_mandatory = len(l_cls)*[False]
    elif type(obj) == DataConstr:
        l_cls = L_ITEM_CLASS + L_LOOP_CLASS
        l_flag_mandatory = len(l_cls) * [False]
    else:
        l_cls = obj.mandatory_classes+obj.optional_classes
        l_flag_mandatory = len(obj.mandatory_classes) * [True] + len(obj.optional_classes) * [False]

    l_cls_name_module_bases = [(_, _.__name__, _.__module__, _.__bases__[0].__name__, str(int(not(_f)))) for _, _f in zip(l_cls, l_flag_mandatory)]
    l_cls_name_module_bases.sort(key=lambda x: x[4]+x[3]+x[2]+x[1])
    l_cls = [_[0] for _ in l_cls_name_module_bases]
    n_row, n_col = len(l_cls)+1, 3
    table_widget_1 = QtWidgets.QTableWidget(n_row, n_col)
    table_widget_1.setHorizontalHeaderLabels(["class_name", "type", "module"])


    header = table_widget_1.horizontalHeader()
    header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
    header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
    header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)


    for i_row, _cls_name_module_bases in enumerate(l_cls_name_module_bases):
        
        s_name = _cls_name_module_bases[1]
        s_module = ".".join(_cls_name_module_bases[2].split(".")[:-1])
        s_bases = _cls_name_module_bases[3]
        s_flag_m = _cls_name_module_bases[4]

        if s_bases == "GlobalConstr":
            s_bases = "global block "
        elif s_bases == "DataConstr":
            s_bases = "data block "
        elif s_bases == "LoopConstr":
            s_bases = "loop "
        elif s_bases == "ItemConstr":
            s_bases = "items "
        s_doc = _cls_name_module_bases[0].__doc__

        table_widget_1_item = QtWidgets.QTableWidgetItem(s_name)
        table_widget_1_item.setCheckState(0)
        table_widget_1_item.setToolTip(s_doc)
        table_widget_1.setItem(i_row, 0, table_widget_1_item)

        table_widget_2_item = QtWidgets.QTableWidgetItem(s_bases)
        table_widget_2_item.setToolTip(s_doc)
        table_widget_1.setItem(i_row, 1, table_widget_2_item)

        table_widget_3_item = QtWidgets.QTableWidgetItem(s_module)
        table_widget_3_item.setToolTip(s_doc)
        table_widget_1.setItem(i_row, 2, table_widget_3_item)

        if s_flag_m=="0":
            table_widget_1_item.setBackground(QtGui.QColor(255, 255, 240))#Ivory
            table_widget_2_item.setBackground(QtGui.QColor(255, 255, 240))
            table_widget_3_item.setBackground(QtGui.QColor(255, 255, 240))
        else:
            table_widget_1_item.setBackground(QtGui.QColor(255, 255, 255))#White
            table_widget_2_item.setBackground(QtGui.QColor(255, 255, 255))
            table_widget_3_item.setBackground(QtGui.QColor(255, 255, 255))


    pb_add = QtWidgets.QPushButton("Add objects")
    table_widget_1.setCellWidget(n_row-1, 0, pb_add)
    table_widget_1.setVerticalHeaderLabels(n_row*[""])
    pb_add.clicked.connect(lambda : add_obj_by_table(table_widget_1, l_cls, obj, thread))

    layout.addWidget(table_widget_1)

    return layout


def add_obj_by_table(table_widget, l_cls, obj, thread):
    if type(obj) == GlobalConstr:
        flag_constrained = True
    elif type(obj) == DataConstr:
        flag_constrained = True
    else:
        flag_constrained = False
    
    n_mandatory = len(obj.mandatory_classes)
    n_optional = len(obj.optional_classes)
    n_row = table_widget.rowCount()
    l_del = []
    l_ind = []
    l_name = []
    for i_row in range(n_row-1):
        val = 0
        flag=False
        _table_item =  table_widget.item(i_row, 0)
        if _table_item is not None:
            l_ind.append(i_row)
            val = _table_item.checkState()
        
        _table_item_2 =  table_widget.item(i_row, 1)
        if val == 2: flag = True
        l_del.append(flag)
        s_name = ""
        l_name.append(s_name)
    for _1, _2, _name in zip(range((n_row-2), -1, -1), reversed(l_del), reversed(l_name)):
        if _2:
            _ind = l_ind.index(_1)
            _cls = l_cls[_ind]
            _item = _cls()
            if isinstance(_item, GlobalConstr):
                _item.global_name=_name
            elif isinstance(_item, DataConstr):
                _item.data_name=_name
            elif isinstance(_item, LoopConstr):
                _item.loop_name=_name

            if _item is not None:
                l_add_mandatory_obj = []
                l_add_optional_obj = []
                flag = False
                if _ind < n_mandatory:
                    for _item_in in obj.mandatory_objs:
                        if type(_item_in) == type(_item):
                            if isinstance(_item_in, GlobalConstr):
                                if _item_in.global_name == _name:
                                    obj.mandatory_objs.remove(_item_in)
                            elif isinstance(_item_in, DataConstr):
                                if _item_in.data_name == _name:
                                    obj.mandatory_objs.remove(_item_in)
                            elif isinstance(_item_in, LoopConstr):
                                if _item_in.loop_name == _name:
                                    obj.mandatory_objs.remove(_item_in)
                            elif isinstance(_item_in, ItemConstr):
                                obj.mandatory_objs.remove(_item_in)
                    l_add_mandatory_obj.append(_item)
                else:
                    for _item_in in obj.optional_objs:
                        if type(_item_in) == type(_item):
                            if isinstance(_item_in, GlobalConstr):
                                if _item_in.global_name == _name:
                                    obj.optional_objs.remove(_item_in)
                            elif isinstance(_item_in, DataConstr):
                                if _item_in.data_name == _name:
                                    obj.optional_objs.remove(_item_in)
                            elif isinstance(_item_in, LoopConstr):
                                if _item_in.loop_name == _name:
                                    obj.optional_objs.remove(_item_in)
                            elif isinstance(_item_in, ItemConstr):
                                obj.optional_objs.remove(_item_in)
                    l_add_optional_obj.append(_item)

                obj.mandatory_objs.extend(l_add_mandatory_obj)
                obj.optional_objs.extend(l_add_optional_obj)

                if flag_constrained:
                    for _obj in l_add_optional_obj:
                        if not(isinstance(_obj, tuple(obj.optional_classes))):
                            obj.optional_classes.append(type(_obj))
    thread.signal_refresh.emit()

def get_layout_rciftab_obj(obj, thread):
    layout = QtWidgets.QVBoxLayout()

    _text_edit = QtWidgets.QTextEdit()
    if (isinstance(obj, Global) | isinstance(obj, Data) | isinstance(obj, Loop) | isinstance(obj, Item)):
        _text_edit.setText(str(obj))
    else:
        _text_edit.setText(obj.to_cif(flag=True))
    layout.addWidget(_text_edit)

    lay_button = QtWidgets.QHBoxLayout()
    lay_button.addStretch(1)
    button_to_obj = QtWidgets.QPushButton("add to object")
    lay_button.addWidget(button_to_obj)
    layout.addLayout(lay_button)
    button_to_obj.clicked.connect(lambda : add_rcif_to_obj(obj, _text_edit.toPlainText(), thread))
    return layout

def add_rcif_to_obj(obj, text, thread):
    obj_cls = type(obj)
    obj_new = None
    if (isinstance(obj, Global) | isinstance(obj, Data) | isinstance(obj, Loop) | isinstance(obj, Item)):
        l_obj_new = obj_cls() 
        l_obj_new.take_from_string(text)
    else:
        l_obj_new = obj_cls.from_cif(text)
    if l_obj_new is not None:
        if isinstance(l_obj_new, list):
            if len(l_obj_new) != 0:
                obj_new = l_obj_new[0]
        else:
            obj_new = l_obj_new 

    if obj_new is None:
        return
    if isinstance(obj, LoopConstr):
        obj.item = obj_new.item
        obj.form_object
    elif isinstance(obj, DataConstr):
        pass
    elif isinstance(obj, GlobalConstr):
        pass
    elif isinstance(obj, ItemConstr):
        obj.clean_attribute
        l_attr = obj_new.mandatory_attribute + obj.optional_attribute
        for _attr in l_attr:
            if obj_new.is_defined_attribute(_attr):
                setattr(obj, f"__{_attr:}", getattr(obj_new, f"__{_attr:}"))
        if obj.is_defined:
            obj.form_object
    elif isinstance(obj, Item):
        obj.name = obj_new.name
        obj.value = obj_new.value
    elif isinstance(obj, Loop):
        pass
    elif isinstance(obj, Data):
        pass
    elif isinstance(obj, Global):
        pass
    thread.signal_refresh.emit()
    return
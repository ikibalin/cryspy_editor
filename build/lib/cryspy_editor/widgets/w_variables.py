"""WMethods class."""
from typing import Callable, Any, NoReturn
from PyQt5 import QtWidgets, QtGui, QtCore

from cryspy.A_functions_base.function_1_strings import value_error_mark_to_string
from cryspy.A_functions_base.function_1_objects import variable_name_to_string

class WVariables(QtWidgets.QListWidget):
    """WFunction class."""

    def __init__(self, parent=None):
        super(WVariables, self).__init__(parent)
        # self.setWidgetResizable(True)

        self.object = None
        self.variable_names_refined = None
        self.variable_names_fixed = None

        # self.wlist = QtWidgets.QListWidget(self)
        # self.wlist.clicked.connect(self.open_menu)


        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)        
        self.customContextMenuRequested.connect(self.open_menu)
        self.itemDoubleClicked.connect(self.double_click)

        # self.setWidget(self.wlist)
        # self.wlist.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)        
        # self.wlist.customContextMenuRequested.connect(self.open_menu)
        # self.wlist.itemDoubleClicked.connect(self.double_click)

    def focusInEvent(self, event):
        self.get_variables()

    def set_func_object_clicked(self, func_object_clicked:
                                Callable[[Any], Any]) -> NoReturn:
        """Set function when object is clicked."""
        self.func_object_clicked = func_object_clicked

    def double_click(self, w_item):
        self.fix_refine_variable(w_item)

    def set_thread(self, thread):
        """Set text."""
        self.mythread = thread

    def set_object(self, obj):
        self.object = obj
        # self.wlist.clear()
        self.clear()
        self.variable_names_fixed = None
        self.get_variables()

    def get_variables(self):
        """Get methods."""
        obj = self.object
        if obj is None:
            return
        v_n_ref = obj.get_variable_names()

        self.variable_names_refined = v_n_ref
        v_n_fix = self.variable_names_fixed
        if v_n_fix is None:
            v_n_all = v_n_ref
        else:
            l_del = []
            for var_name in v_n_fix:
                try:
                    obj.get_variable_by_name(var_name)
                except AttributeError:
                    l_del.append(var_name)
            for del_name in l_del:
                v_n_fix.remove(del_name)

            for var_name in v_n_ref:
                if var_name in v_n_fix:
                    v_n_fix.remove(var_name)
            v_n_all = v_n_ref + v_n_fix

        qfont = QtGui.QFont()
        qfont.setBold(True)
        # self.wlist.clear()
        self.clear()
        for var_name in v_n_all:
            var_value = obj.get_variable_by_name(var_name)
            var_ref_name = var_name[:-1]+((f"{var_name[-1][0]:}_refinement",
                                             var_name[-1][1]), )
            var_sigma_name = var_name[:-1]+((f"{var_name[-1][0]:}_sigma",
                                             var_name[-1][1]), )
            var_mark_name = var_name[:-1]+((f"{var_name[-1][0]:}_mark",
                                             var_name[-1][1]), )
            var_sigma = obj.get_variable_by_name(var_sigma_name)
            var_ref = obj.get_variable_by_name(var_ref_name)
            var_mark = obj.get_variable_by_name(var_mark_name)
            
            name = variable_name_to_string(var_name, flag_html=False)
            name_sh = name.split(".")[-1]
            if var_ref:
                val_str = value_error_mark_to_string(var_value, var_sigma, var_mark)
                s_val = f"{name_sh:}: {val_str:}"
            else:
                s_val = f"{name_sh:}: {var_value:}"

            list_widget_item = QtWidgets.QListWidgetItem(s_val)
            list_widget_item.variable_name = var_name
            list_widget_item.setFont(qfont)
            # self.wlist.addItem(list_widget_item)
            self.addItem(list_widget_item)
        
        # self.wlist.setSortingEnabled(True)
        self.setSortingEnabled(True)

    def open_menu(self, position):
        """Context menu."""
        obj = self.object
        if obj is None:
            return
        menu = QtWidgets.QMenu(self)
        # w_list = self.wlist
        w_item = self.itemAt(position)
        if w_item is not None:
            # l_ind = find_tree_item_position(self, w_item)
            show_item = QtWidgets.QAction('Show item', menu)
            show_item.triggered.connect(
                lambda x: self.show_item(w_item))
            menu.addAction(show_item)


            fix_variable = QtWidgets.QAction('Delete variable', menu)
            fix_variable.triggered.connect(lambda x: self.delete_variable(
                w_item))
            menu.addAction(fix_variable)

            copy_variable = QtWidgets.QAction('Copy to clipboard', menu)
            copy_variable.triggered.connect(
                lambda x: self.copy_variable_to_clipboard(w_item))
            menu.addAction(copy_variable)
        else:
            fix_variables = QtWidgets.QAction('Fix all variables', menu)
            fix_variables.triggered.connect(lambda x: self.fix_variables())
            menu.addAction(fix_variables)

            copy_variables = QtWidgets.QAction('Copy to clipboard', menu)
            copy_variables.triggered.connect(
                lambda x: self.copy_variables_to_clipboard())
            menu.addAction(copy_variables)

        # menu.exec_(self.wlist.viewport().mapToGlobal(position))
        menu.exec_(self.viewport().mapToGlobal(position))

    def fix_variables(self):
        obj = self.object
        obj.fix_variables()
        # self.wlist.clear()
        self.clear()
        self.variable_names_fixed = None

    def copy_variables_to_clipboard(self):
        obj = self.object
        variable_names = obj.get_variable_names()
        l_name_str, l_val_str = [], []
        for var_name in variable_names:
            var_value = obj.get_variable_by_name(var_name)
            var_sigma_name = var_name[:-1]+((f"{var_name[-1][0]:}_sigma",
                                             var_name[-1][1]), )
            var_mark_name = var_name[:-1]+((f"{var_name[-1][0]:}_mark",
                                             var_name[-1][1]), )
            var_sigma = obj.get_variable_by_name(var_sigma_name)
            var_mark = obj.get_variable_by_name(var_mark_name)
            
            name = variable_name_to_string(var_name, flag_html=False)
            val_str = value_error_mark_to_string(var_value, var_sigma, var_mark)
            l_name_str.append(name)
            l_val_str.append(val_str)
        n_1 = max([len(h) for h in l_name_str])
        n_2 = max([len(h) for h in l_val_str])
        ls_out = [f"|{'parameter'.rjust(n_1):}|  {'value'.rjust(n_2):}|"]
        ls_out.append("|"+n_1*"-"+"|"+(n_2+2)*"-"+"|")
        ls_out.extend([f"|{h1.rjust(n_1):}|  {h2.rjust(n_2):}|" for h1, h2 in
                       zip(l_name_str, l_val_str)])

        cb = QtWidgets.QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText("\n".join(ls_out), mode=cb.Clipboard)

    def delete_variable(self, w_item):
        obj = self.object
        var_name = w_item.variable_name
        var_ref_name = var_name[:-1]+((f"{var_name[-1][0]:}_refinement",
                                       var_name[-1][1]), )
        try:
            obj.set_variable_by_name(var_ref_name, False)
            if self.variable_names_fixed is not None:
                if var_name in self.variable_names_fixed:
                    self.variable_names_fixed.remove(var_name)
        except AttributeError:
            if var_name in self.variable_names_fixed:
                self.variable_names_fixed.remove(var_name)
            if var_name in self.variable_names_refined:
                self.variable_names_refined.remove(var_name)
        # w_list = self.wlist
        # self.removeItemWidget(w_item)

    def show_item(self, w_item):
        obj = self.object
        var_name = w_item.variable_name
        item_name = var_name[:-1]
        item  = obj.get_variable_by_name(item_name)

        self.func_object_clicked(item)
        

    def fix_refine_variable(self, w_item):
        obj = self.object
        var_name = w_item.variable_name
        name = variable_name_to_string(var_name, flag_html=False)
        name_sh = name.split(".")[-1]
        var_value = obj.get_variable_by_name(var_name)
        var_ref_name = var_name[:-1]+((f"{var_name[-1][0]:}_refinement",
                                       var_name[-1][1]), )
        var_sigma_name = var_name[:-1]+((f"{var_name[-1][0]:}_sigma",
                                         var_name[-1][1]), )
        var_mark_name = var_name[:-1]+((f"{var_name[-1][0]:}_mark",
                                         var_name[-1][1]), )
        var_sigma = obj.get_variable_by_name(var_sigma_name)
        try:
            var_ref = obj.get_variable_by_name(var_ref_name)
            var_mark = obj.get_variable_by_name(var_mark_name)
            obj.set_variable_by_name(var_ref_name, not(var_ref))
            if var_ref:
                if self.variable_names_fixed is None:
                    self.variable_names_fixed = [var_name]
                elif not(var_name in self.variable_names_fixed):
                    self.variable_names_fixed.append(var_name)
                if var_name in self.variable_names_refined:
                    self.variable_names_refined.remove(var_name)
                w_item.setText(f"{name_sh:}: {var_value:}")
            else:
                if self.variable_names_fixed is not None:
                    if var_name in self.variable_names_fixed:
                        self.variable_names_fixed.remove(var_name)
                if not(var_name in self.variable_names_refined):
                    self.variable_names_refined.append(var_name)
                val_str = value_error_mark_to_string(var_value, var_sigma, var_mark)
                w_item.setText(f"{name_sh:}: {val_str:}")
                
        except AttributeError:
            if var_name in self.variable_names_fixed:
                self.variable_names_fixed.remove(var_name)
            if var_name in self.variable_names_refined:
                self.variable_names_refined.remove(var_name)
            # w_list = self.wlist
            self.removeItemWidget(w_item)

    def copy_variable_to_clipboard(self, w_item):
        cb = QtWidgets.QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText(w_item.text(), mode=cb.Clipboard)

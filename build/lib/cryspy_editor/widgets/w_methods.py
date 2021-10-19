"""WMethods class."""
from PyQt5 import QtWidgets, QtGui
from types import FunctionType


class WMethods(QtWidgets.QScrollArea):
    """WFunction class."""

    def __init__(self, parent=None):
        super(WMethods, self).__init__(parent)
        self.object = None

        self.setWidgetResizable(True)

        self.wlist = QtWidgets.QListWidget()
        self.wlist.clicked.connect(self.do_func)

        self.setWidget(self.wlist)

    def set_thread(self, thread):
        """Set text."""
        self.mythread = thread

    def set_wfunction(self, wfunction):
        """Set text."""
        self.wfunction = wfunction

    def get_methods(self, obj):
        """Get methods."""
        qfont = QtGui.QFont()
        qfont.setBold(True)
        self.wlist.clear()
        self.object = obj
        l_method = [_1 for _1, _2 in type(obj).__dict__.items()
                    if ((type(_2) == FunctionType) &
                        (not(_1.startswith("_"))))]
        for method in l_method:
            func = getattr(obj, method)
            l_param = [_ for _ in
                       func.__code__.co_varnames[:func.__code__.co_argcount]
                       if _ != "self"]
            s_par = ""
            if len(l_param) > 0:
                s_par = ", ".join(l_param)
            s_val = f"{method:}({s_par:})"

            list_widget_item = QtWidgets.QListWidgetItem(s_val)
            list_widget_item.setFont(qfont)
            # list_widget_item.setToolTip(get_help_for_attribute(obj, method))
            self.wlist.addItem(list_widget_item)
        self.wlist.setSortingEnabled(True)

    def do_func(self, func_name):
        """Do func."""
        func_name = self.wlist.currentItem().text().split("(")[0]
        func = getattr(self.object, func_name)
        # type(self.object).__dict__[func_name]
        self.wfunction.set_function(func, self.mythread)


def do_obj_func(obj, func_name, wfunction, thread):
    """Do obj function."""
    func = type(obj).__dict__[func_name]
    wfunction.set_function(func, thread)

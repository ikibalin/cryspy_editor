from PyQt5 import QtWidgets, QtCore, QtGui

from cryspy import get_functions_of_objet

from .w_editcif import WEditCif

class WLoopItems(QtWidgets.QWidget):
    def __init__(self, w_function, thread, parent=None):
        
        super(WLoopItems, self).__init__(parent)
        self.w_spin_box = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.w_spin_box.setTickInterval(1)
        self.w_spin_box.setMinimum(0)
        self.w_spin_box.setMaximum(0)
        self.w_editcif = WEditCif(self)
        v_layout = QtWidgets.QVBoxLayout(parent)
        v_layout.addWidget(self.w_spin_box)
        v_layout.addWidget(self.w_editcif)
        self.setLayout(v_layout)
        self.object = None
        self.w_function = w_function
        self.thread = thread

        self.w_spin_box.valueChanged.connect(self.refresh_editcif)
        # self.customContextMenuRequested.connect(self.open_menu)

    def set_object(self, object):
        """Set object."""
        self.object = object
        if len(object.items) > 0:
            self.w_spin_box.setMinimum(1)
            self.w_spin_box.setMaximum(len(object.items))

            item = self.object.items[0]
            self.w_editcif.set_object(item)

        else:
            self.w_spin_box.setMinimum(0)
            self.w_spin_box.setMaximum(0)

    #def open_menu(self, position):
    #    print(position)
    #    if self.object is None:
    #        return
    #    items = self.object.items
    #    ind = self.w_spin_box.value()-1
    #    
    #    if not((ind >=0) & (ind < len(items))):
    #        return
    #    
    #    item = items[ind]
    #    l_method = get_functions_of_objet(item)

    #    menu = QtWidgets.QMenu(self)
    #    for method in l_method:
    #        func = getattr(obj, method)
    #        l_param = [_ for _ in func.__code__.co_varnames[
    #            :func.__code__.co_argcount] if _ != "self"]

    #        s_par = ""
    #        if len(l_param) > 0:
    #            s_par = ", ".join(l_param)
    #            s_val = f"{method:}({s_par:})"
    #        
    #        q_action = QtWidgets.QAction(s_val, menu)
    #        q_action.object = item
    #        q_action.triggered.connect(lambda x: self.do_func())
    #        menu.addAction(q_action)
    #    
    #    print(2)
    #    menu.exec_(self.viewport().mapToGlobal(position))

    # def do_func(self):
    #     sender = self.sender()
    #     obj = sender.object
    #     name = sender.text()
    #     func_name = name.split("(")[0]
    #     func = getattr(obj, func_name)
    #     if self.w_function is None:
    #         pass
    #     else:
    #         self.w_function.set_function(func, self.thread)


    def refresh_editcif(self):
        if self.object is None:
            self.w_editcif.set_object("")
        items = self.object.items
        ind = self.w_spin_box.value()-1
        if ((ind >=0) & (ind < len(items))):
            item = items[ind]
            self.w_editcif.set_object(item)
        else:
            self.w_editcif.set_object("")

    def mouseMoveEvent(self, e):
        if e.buttons() != QtCore.Qt.LeftButton:
            return

        if self.object is None:
            return

        items = self.object.items
        ind = self.w_spin_box.value()-1
        if ((ind >=0) & (ind < len(items))):
            item = items[ind]
            object_to_send = item
            string_to_send = type(item).__name__

        mimeData = QtCore.QMimeData()
        mimeData.object_to_send = object_to_send
        mimeData.setText(string_to_send)

        drag = QtGui.QDrag(self)
        drag.setMimeData(mimeData)
        # drag.setHotSpot(e.pos() - self.rect().topLeft())

        dropAction = drag.exec_(QtCore.Qt.MoveAction)

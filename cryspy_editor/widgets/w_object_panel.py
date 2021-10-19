from typing import Union, Callable, Any, NoReturn
from types import FunctionType
import copy
from PyQt5 import QtCore, QtGui, QtWidgets

from cryspy import ItemN, LoopN, DataN, GlobalN, str_to_items, \
    str_to_globaln


from cryspy import L_GLOBAL_CLASS, L_DATA_CLASS, L_ITEM_CLASS, L_LOOP_CLASS
L_GLOBAL_CLS = L_GLOBAL_CLASS
L_DATA_CLS = L_DATA_CLASS
L_LOOP_CLS = L_LOOP_CLASS
L_ITEM_CLS = L_ITEM_CLASS
# import importlib
# additional_module = importlib.import_module("cryspy")


class WObjectPanel(QtWidgets.QTreeWidget):
    """WObjectPanel class."""

    def __init__(self, parent=None) -> NoReturn:
        super(WObjectPanel, self).__init__(parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding))

        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.object = None
        self.itemClicked.connect(self.internal_item_clicked)
        self.customContextMenuRequested.connect(self.open_menu)

    def set_object(self, object: GlobalN) \
            -> NoReturn:
        """Set object GlobalN."""
        self.object = object
        if self.topLevelItemCount() != 0:
            for ind in reversed(range(self.topLevelItemCount())):
                w_del = self.takeTopLevelItem(ind)
                self.removeItemWidget(w_del, ind)
        name_items = [(item.get_name(), item) for item in object.items]
        
        for item_name, item in sorted(name_items):
            wi = make_tree_widget_item(self, item) # object
            self.addTopLevelItem(wi)

        # self.addTopLevelItem(wi)
        self.expandAll()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)

    def set_function_item_clicked(
            self, function_item_clicked: Callable[[Any], Any]) -> NoReturn:
        """Set function when object is clicked."""
        self.func_object_clicked = function_item_clicked
        # self.currentItemChanged.connect(func_object_clicked)

    def set_function_object_refresh(
            self, function_object_refresh: Callable) -> NoReturn:
        """Set function when the object representation has to be refreshed."""
        self.func_object_refresh = function_object_refresh
        # self.currentItemChanged.connect(func_object_clicked)


    def internal_item_clicked(self, *argv):
        gui_object = argv[0]
        object_item = gui_object.object
        self.func_object_clicked(object_item)

    def dragEnterEvent(self, event):
        """Drag enter event."""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):  # FIXME It doesnot work, why?
        """Drop event."""
        print("HERE2_ DROP EVENT!!!!")
        pos = event.pos()
        mime_data = event.mimeData()
        s_cont = mime_data.text()
        object = mime_data.object_to_send
        w_given = self.itemAt(pos)
        print("s_cont:", s_cont)
        print("object:", object)
        print("w_given:", w_given)
        event.acceptProposedAction()

    def mouseMoveEvent(self, event):
        """Mouse move event."""
        w_tree_item = self.itemAt(event.pos())
        if w_tree_item is None:
            return
        object_to_send = w_tree_item.object
        string_to_send = type(object_to_send).__name__

        drag = QtGui.QDrag(self)
        dragMimeData = QtCore.QMimeData()
        dragMimeData.object_to_send = object_to_send
        dragMimeData.setText(string_to_send)

        drag.setMimeData(dragMimeData)
        drag.exec_(QtCore.Qt.MoveAction)

    def open_menu(self, position):
        """Context menu."""
        w_item = self.itemAt(position)

        if w_item is None:
            obj = self.object
        else:
            # l_ind = find_tree_item_position(self, w_item)
            obj = w_item.object

        menu = QtWidgets.QMenu(self)
        if ((type(obj) is GlobalN) | (type(obj) is DataN)):

            if type(obj) is GlobalN:
                menu_data = menu.addMenu("Add data block")

                for cls_item in L_DATA_CLS:
                    prefix = cls_item.PREFIX
                    add_item = QtWidgets.QAction(f'{prefix :}', menu_data)
                    add_item.cls_item = cls_item
                    add_item.triggered.connect(lambda: self.add_item(obj))
                    menu_data.addAction(add_item)

            menu_loop = menu.addMenu("Add loop block")
            for cls_item in L_LOOP_CLS:
                prefix = cls_item.ITEM_CLASS.PREFIX
                add_item = QtWidgets.QAction(f'{prefix :}', menu_loop)
                add_item.cls_item = cls_item
                add_item.triggered.connect(lambda: self.add_item(obj))
                menu_loop.addAction(add_item)

            menu_item = menu.addMenu("Add item")
            for cls_item in L_ITEM_CLS:
                prefix = cls_item.PREFIX
                add_item = QtWidgets.QAction(f'{prefix :}', menu_item)
                add_item.cls_item = cls_item
                add_item.triggered.connect(lambda: self.add_item(obj))
                menu_item.addAction(add_item)
            
        elif isinstance(obj, (GlobalN, DataN)):
            menu_item = menu.addMenu("Add")
            for cls_item in obj.CLASSES_MANDATORY:
                if ((cls_item is not DataN) & (cls_item is not LoopN) &
                    (cls_item is not ItemN)):
                    if "PREFIX" in cls_item.__dict__.keys():
                        prefix = cls_item.PREFIX
                    else:
                        prefix = cls_item.ITEM_CLASS.PREFIX
                    add_item = QtWidgets.QAction(f'{prefix:}', menu_item)
                    add_item.cls_item = cls_item
                    add_item.triggered.connect(
                        lambda: self.add_item(obj))
                    menu_item.addAction(add_item)
            menu_item.addSeparator()
            for cls_item in obj.CLASSES_OPTIONAL:
                if ((cls_item is not DataN) & (cls_item is not LoopN) &
                        (cls_item is not ItemN)):
                    if "PREFIX" in cls_item.__dict__.keys():
                        prefix = cls_item.PREFIX
                    else:
                        prefix = cls_item.ITEM_CLASS.PREFIX
                    add_item = QtWidgets.QAction(f'{prefix :}', menu_item)
                    add_item.cls_item = cls_item
                    add_item.triggered.connect(
                        lambda: self.add_item(obj))
                    menu_item.addAction(add_item)

        if isinstance(obj, (GlobalN, DataN, LoopN)):
            act_add_cif = QtWidgets.QAction("Add by cif...", menu)
            act_add_cif.triggered.connect(lambda: self.add_items(obj))
            menu.addAction(act_add_cif)

            act_rename = QtWidgets.QAction("Rename", menu)
            act_rename.triggered.connect(lambda: self.rename_item(obj))
            menu.addAction(act_rename)

        if isinstance(obj, (DataN, LoopN, ItemN)):
            del_item = QtWidgets.QAction('Delete', menu)
            del_item.triggered.connect(lambda: self.delete_object(w_item))
            menu.addAction(del_item)

        # if isinstance(obj, GlobalN):
        #     menu_tr = menu.addMenu("Transfer")
        #     qaction = QtWidgets.QAction('to global', menu_tr)
        #     qaction.cls_item = GlobalN
        #     qaction.triggered.connect(lambda: self.transfer_item(obj))
        #     menu_tr.addAction(qaction)
        #     for global_cls in L_GLOBAL_CLS:
        #         qaction = QtWidgets.QAction(f'to {global_cls.PREFIX:}',
        #                                     menu_tr)
        #         qaction.cls_item = global_cls
        #         qaction.triggered.connect(
        #             lambda: self.transfer_item(obj))
        #         menu_tr.addAction(qaction)
        # elif isinstance(obj, DataN):
        #     menu_tr = menu.addMenu("Transfer")
        #     qaction = QtWidgets.QAction('to data', menu_tr)
        #     qaction.cls_item = DataN
        #     qaction.triggered.connect(lambda: self.transfer_item(obj))
        #     menu_tr.addAction(qaction)
        #     for data_cls in L_DATA_CLS:
        #         qaction = QtWidgets.QAction(f'to {data_cls.PREFIX:}',
        #                                     menu_tr)
        #         qaction.cls_item = data_cls
        #         qaction.triggered.connect(
        #             lambda: self.transfer_item(obj))
        #         menu_tr.addAction(qaction)
        #     qaction = QtWidgets.QAction('Duplicate', menu)
        #     qaction.triggered.connect(lambda: self.duplicate_data(obj))
        #     menu.addAction(qaction)

        l_method = [_1 for _1, _2 in type(obj).__dict__.items()
                    if ((type(_2) == FunctionType) &
                        (not(_1.startswith("_"))))]
        if len(l_method) != 0:
            menu_method = menu.addMenu("Methods")
            for method in l_method:
                func = getattr(obj, method)
                l_param = [_ for _ in func.__code__.co_varnames[
                    :func.__code__.co_argcount] if _ != "self"]
                s_par = ""
                if len(l_param) > 0:
                    s_par = ", ".join(l_param)
                s_val = f"{method:}({s_par:})"
                qaction = QtWidgets.QAction(s_val, menu_method)
                qaction.object = obj
                qaction.triggered.connect(lambda x: self.do_func())
                menu_method.addAction(qaction)
        if isinstance(obj, (LoopN, ItemN)):
            qaction = QtWidgets.QAction("Refine all variables", menu)
            qaction.object = obj
            qaction.triggered.connect(lambda x: self.do_func())
            menu.addAction(qaction)
        qaction = QtWidgets.QAction("Fix all variables", menu)
        qaction.object = obj
        qaction.triggered.connect(lambda x: self.do_func())
        menu.addAction(qaction)

        menu.exec_(self.viewport().mapToGlobal(position))

    def do_func(self):
        sender = self.sender()
        obj = sender.object
        name = sender.text()
        if name == "Refine all variables":
            name = "refine_all_variables"
        elif name == "Fix all variables":
            name = "fix_variables"
        func_name = name.split("(")[0]
        func = getattr(obj, func_name)
        self.w_function.set_function(func, self.cthread)
        
    def set_thread(self, thread):
        """Set text."""
        self.cthread = thread

    def set_w_function(self, w_function):
        """Set text."""
        self.w_function = w_function

    def duplicate_data(self, widget: QtWidgets.QTreeWidgetItem):
        obj_data = widget.object
        widget_parent = widget.parent()
        obj_global = widget_parent.object
        text, ok = QtWidgets.QInputDialog.getText(
            self, f"Input dialog",
            f"Enter the new name of {obj_data.PREFIX:}")

        if ok:
            obj_data_new = obj_data.copy("".join(text.strip().split()))
            obj_global.add_items([obj_data_new])
            self.set_object(obj_global)

    def rename_item(self, obj):
        """Rename item."""
        
        text, ok = QtWidgets.QInputDialog.getText(
            self, f"Input dialog {obj.get_name():}", "Enter the new name")
        if ok:
            new_name = "".join(text.split())
            if isinstance(obj, GlobalN):
                obj.global_name = new_name
            elif isinstance(obj, DataN):
                obj.data_name = new_name
            elif isinstance(obj, LoopN):
                obj.loop_name = new_name
        self.set_object(self.object)

    def add_item(self, obj) \
            -> NoReturn:
        """Add object."""
        sender = self.sender()
        new_item = sender.cls_item()
        
        if ((type(obj) is DataN) | (type(obj) is GlobalN)):
            item_cls = set([type(item) for item in obj.items])
            if type(new_item) not in item_cls:
                obj.CLASSES_OPTIONAL = tuple(list(obj.CLASSES_OPTIONAL) +
                                             [type(new_item)])
                obj.CLASSES = tuple(list(obj.CLASSES) + [type(new_item)])
        obj.add_items([new_item])
        self.set_object(self.object)

    def transfer_item(self, widget: QtWidgets.QTreeWidgetItem) \
            -> NoReturn:
        """Transfer to choosen item."""
        sender = self.sender()
        cls_item = sender.cls_item
        item_old = widget.object
        if cls_item is GlobalN:
            item_new = cls_item.make_container(
                (), tuple(set([type(item) for item in item_old])), "global")
        elif cls_item is DataN:
            item_new = cls_item.make_container(
                (), tuple(set([type(item) for item in item_old])), "data")
        else:
            item_new = cls_item()
        item_new.add_items(item_old.items)
        if isinstance(item_new, GlobalN):
            self.object = item_new
        else:
            widget_parent = widget.parent()
            item_parent = widget_parent.object
            item_parent.items.remove(item_old)
            item_parent.add_items([item_new])
        self.set_object(self.object)

    def add_items(self, obj) \
            -> NoReturn:
        """Add object."""
        modal_widget = MWAddItem(self)
        modal_widget.func_object_refresh = self.func_object_refresh
        modal_widget.set_object(obj)
        modal_widget.show()
        # obj.add_items([obj_new])

    def delete_object(self, widget: QtWidgets.QTreeWidgetItem) -> NoReturn:
        """Delete object."""
        widget_parent = widget.parent()
        obj = widget.object

        if widget_parent is None:
            widget_parent = self

        obj_parent = widget_parent.object
        if isinstance(obj_parent, (GlobalN, DataN)):
            obj_parent.items.remove(obj)
            if type(widget_parent) is WObjectPanel:
                widget_parent.takeTopLevelItem(widget_parent.indexOfTopLevelItem(widget))
            else:
                widget_parent.removeChild(widget)

    def save_object(self, object_to_save) -> NoReturn:
        """Save as object."""
        f_name, okPressed = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Select a file:', "", "All files (*.*)")
        if not (okPressed):
            return None

        s_out = object_to_save.to_cif()

        with open(f_name, "w") as fid:
            fid.write(s_out)


def find_tree_item_position(
        w_main: QtWidgets.QTreeWidgetItem, child_item: QtWidgets.QTreeWidget)\
        -> int:
    """Find tree item position."""
    ind = w_main.indexOfTopLevelItem(child_item)
    if ind != -1:
        res = [ind]
    else:
        w_parent = child_item.parent()  # FIXME: it gives mistake
        ind_child = w_parent.indexOfChild(child_item)
        res = find_tree_item_position(w_main, w_parent)
        res.append(ind_child)
    return res


def make_tree_widget_item(widg: Union[QtWidgets.QTreeWidget,
                                      QtWidgets.QTreeWidgetItem],
                          object_item: Union[ItemN, LoopN, DataN, GlobalN],
                          name: str = None) \
        -> QtWidgets.QTreeWidgetItem:
    """Make tree widget item for item."""
    wi = QtWidgets.QTreeWidgetItem(widg)
    if name is None:
        wi.setText(0, f"{object_item.get_name():}")
    else:
        wi.setText(0, name)
    wi.object = object_item

    if ((type(object_item) == ItemN) | (type(object_item) == LoopN)):
        wi.setBackground(0, QtGui.QColor(237, 242, 255))
    else:
        wi.setBackground(0, QtGui.QColor(255, 255, 255))

    if object_item.is_defined():
        pass
    else:
        wi.setBackground(0, QtGui.QColor(255, 224, 224))

    if isinstance(object_item, (GlobalN, DataN)):
        l_name = [item.get_name() for item in object_item.items]
        l_name_sort = sorted(l_name)
        for name in l_name_sort:
            ind = l_name.index(name)
            item = object_item.items[ind]
            wii = make_tree_widget_item(wi, item)
            wi.addChild(wii)
    elif isinstance(object_item, ItemN):
        for attr_name in object_item.ATTR_INT_NAMES:
            if object_item.is_attribute(attr_name):
                int_obj = getattr(object_item, attr_name)
                if isinstance(int_obj, (ItemN, LoopN)):
                    wii = make_tree_widget_item(wi, int_obj, name=attr_name)
                    wi.addChild(wii)
        for attr_name in object_item.ATTR_INT_PROTECTED_NAMES:
            if attr_name in object_item.__dict__.keys():
                if object_item.is_attribute(attr_name):
                    int_obj = getattr(object_item, attr_name)
                    if isinstance(int_obj, (ItemN, LoopN)):
                        wii = make_tree_widget_item(wi, int_obj, name=attr_name)
                        wi.addChild(wii)
    return wi


class MWAddItem(QtWidgets.QMainWindow):
    """MWAddItem class."""

    def __init__(self, parent=None):
        super(MWAddItem, self).__init__(parent)
        self.object = None
        self.setWindowTitle("Add Items")
        self.init_widgit()

    def init_widgit(self):
        """Init widgit."""
        widg = QtWidgets.QWidget(self)

        lay_central = QtWidgets.QVBoxLayout()

        self.w_te = QtWidgets.QTextEdit(widg)
        self.w_pb = QtWidgets.QPushButton(widg)
        self.w_pb.setText("Transform to items")
        self.w_pb.clicked.connect(self.add_items)

        lay_central.addWidget(self.w_te)
        lay_central.addWidget(self.w_pb)
        widg.setLayout(lay_central)
        self.setCentralWidget(widg)

    def set_object(self, obj):
        """Set object."""
        self.object = obj

    def add_items(self, obj):
        """Add items to object."""
        obj = self.object
        obj_cls = type(obj)
        s_cont = self.w_te.toPlainText()

        if isinstance(obj, GlobalN):
            l_item = (str_to_globaln(s_cont)).items
        elif isinstance(obj, DataN):
            l_item = str_to_items(s_cont)

        cls_opt_obj = obj.CLASSES_OPTIONAL
        cls_obj = obj.CLASSES
        
        if ((obj_cls is DataN) | (obj_cls is GlobalN)):
            l_cls_item_add = [type(item) for item in l_item
                              if type(item) not in cls_obj]
            l_new_cls_opt_obj = list(cls_opt_obj) + l_cls_item_add
            l_new_cls_obj = list(cls_obj) + l_cls_item_add
            obj.CLASSES_OPTIONAL = tuple(l_new_cls_opt_obj)
            obj.CLASSES = tuple(l_new_cls_obj)
            obj.add_items(l_item)
        elif isinstance(obj, (DataN, GlobalN)):
            obj.add_items(l_item)
        self.func_object_refresh()
        self.close()

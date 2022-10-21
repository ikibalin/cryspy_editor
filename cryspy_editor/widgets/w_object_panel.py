from typing import Callable, NoReturn # Union, Any
from PyQt5 import QtCore, QtWidgets, QtGui



def make_tree_widget_item(widget_tree: QtWidgets.QTreeWidgetItem,
                          dict_tree: dict) \
        -> QtWidgets.QTreeWidgetItem:
    """Make tree widget item for item."""

    keys_dict = dict_tree.keys()
    keys_item = sorted([name for name in keys_dict if name.startswith("ITEM_")])
    widget_tree.method_names = sorted([name[7:] for name in keys_dict if name.startswith("METHOD_")])

    for item_name in keys_item:
        wi = QtWidgets.QTreeWidgetItem(widget_tree)
        wi.setText(0, item_name[5:])

        dict_item = dict_tree[item_name]
        make_tree_widget_item(wi, dict_item) 
        widget_tree.addChild(wi)
    return


class WObjectPanel(QtWidgets.QTreeWidget):
    """WObjectPanel class."""

    def __init__(self, item_clicked: Callable, item_menu: Callable, item_to_rcif: Callable, parent=None) -> NoReturn:
        super(WObjectPanel, self).__init__(parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding))

        self.setColumnCount(1)
        self.setHeaderHidden(True)

        self.method_names = []

        # self.itemClicked.connect(item_clicked)
        self.itemPressed.connect(item_clicked)
        self.customContextMenuRequested.connect(item_menu)
        self.item_to_rcif = item_to_rcif


    def set_dict_tree(self, dict_tree: dict):
        if self.topLevelItemCount() != 0:
            for ind in reversed(range(self.topLevelItemCount())):
                w_del = self.takeTopLevelItem(ind)
                self.removeItemWidget(w_del, ind)

        dict_keys = sorted(dict_tree.keys())
        key_item = [name for name in dict_keys if name.startswith("ITEM_")]
        self.method_names = [name[7:] for name in dict_keys if name.startswith("METHOD_")]

        for item_name in key_item:
            wi = QtWidgets.QTreeWidgetItem(self)
            wi.setText(0, item_name[5:])

            dict_item = dict_tree[item_name]
            make_tree_widget_item(wi, dict_item) 
            self.addTopLevelItem(wi)

        self.expandAll()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setAcceptDrops(False)
        self.setDragEnabled(True)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if not (event.buttons() == QtCore.Qt.LeftButton):
            return 
        drag = QtGui.QDrag(self)
        w_item = self.currentItem()
        rcif = self.item_to_rcif(w_item)
        mimeData = QtCore.QMimeData()
        mimeData.setText(rcif)

        drag.setMimeData(mimeData)
        dropAction = drag.exec_(QtCore.Qt.MoveAction)

    # def dropEvent(self, e):
    #     print("drop: ", e.mimeData().text())
    # def dragEnterEvent(self, e):
    #     if e.mimeData().hasFormat('text/plain'):
    #         e.accept()
    #         print("HERE")
    #     else:
    #         e.ignore()


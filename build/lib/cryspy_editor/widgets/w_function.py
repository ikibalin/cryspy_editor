"""WFunction class."""
from PyQt5 import QtWidgets, QtCore
from typing import NoReturn, Callable
import numpy

import cryspy

class WFunction(QtWidgets.QFrame):
    """WFunction class."""

    def __init__(self, parent=None):
        super(WFunction, self).__init__(parent)
        self.setStyleSheet("background-color:white;")
        self.setFrameShape(QtWidgets.QFrame.Box)

        self.setSizePolicy(QtWidgets.QSizePolicy(
                    QtWidgets.QSizePolicy.Expanding,
                    QtWidgets.QSizePolicy.Fixed))

        self.layout_func = QtWidgets.QHBoxLayout()
        self.push_button = QtWidgets.QPushButton("Run function")
        self.w_cb_hide = QtWidgets.QCheckBox("hide")
        self.w_cb_hide.setCheckState(2)
        self.w_cb_hide.stateChanged.connect(self.show_hide)

        self.hide()

        layout_central = QtWidgets.QHBoxLayout()
        layout_central.addLayout(self.layout_func)
        layout_central.addStretch(1)
        layout_central.addWidget(self.push_button)
        layout_central.addWidget(self.w_cb_hide)

        self.setLayout(layout_central)

        self.l_w_arg = []
        self.function_attached = None
        self.thread_attached = None
        self.push_button.clicked.connect(self.run_function)

    def show_hide(self, *arg) -> NoReturn:
        """Show hide."""
        if arg[0] == 2:
            self.hide()
        else:
            self.show()

    def set_function(self, func: Callable, thread: QtCore.QThread, globaln=None):
        """Set function."""
        self.push_button.setText(f"Run '{func.__name__:}'")
        self.w_cb_hide.setCheckState(0)
        self.setToolTip(func.__doc__)
        n_row_need = func.__code__.co_argcount
        l_var_name = func.__code__.co_varnames[:n_row_need]

        if func.__defaults__ is None:
            l_defaults = []
        else:
            l_defaults = func.__defaults__
        n_defaults = len(l_defaults)
        n_var_names = len(l_var_name)

        layout = self.layout_func
        del_layout(layout)

        self.l_w_arg = []
        self.globaln = None

        d_annotations = func.__annotations__
        var_annotations = d_annotations.keys()

        flag_first_globaln = False
        flag_in_globaln = globaln is not None
        for _i_var, _var_name in enumerate(l_var_name):
            i_default = _i_var-(n_var_names-n_defaults)
            if i_default >= 0:
                s_def = str(l_defaults[i_default]) + " (default)"
            else:
                s_def = "<drop object>"

            var_type = object
            if _var_name in var_annotations:
                var_type = d_annotations[_var_name]

                if var_type.__class__.__name__ == '_UnionGenericAlias':
                    item_types = set(var_type.__args__)
                    cond_1 = False
                    for item_type in item_types:
                        cond_1 |= issubclass(item_type, cryspy.GlobalN)
                else:
                    cond_1 = issubclass(var_type, cryspy.GlobalN)
            else:
                cond_1 = issubclass(var_type, cryspy.GlobalN)

            cond_1 &= flag_in_globaln
            cond_1 &= not(flag_first_globaln)
            if (_var_name == "self"):
                pass
            elif (_var_name == "d_info"):
                pass
            elif cond_1:
                flag_first_globaln = True
                self.globaln = globaln
            else:
                flag_first_globaln = True #globaln should be only on the first place

                flag_special = False
                flag_label = True

                if var_type is bool:
                    widget = QtWidgets.QCheckBox(_var_name)
                    widget.setCheckState(2*l_defaults[i_default])
                    widget.attached_object = l_defaults[i_default]
                    widget.clicked.connect(
                        lambda: setattr(widget, "attached_object",
                                        widget.checkState()//2))
                    flag_special = True
                    flag_label = False

                if not(flag_special):
                    widget = DropLabel(f"{s_def:}")
                    widget.setStyleSheet(
                        "background:lightyellow; border: 2px solid red;")
                    if i_default >= 0:
                        widget.attached_object = l_defaults[i_default]
                        widget.setStyleSheet("")
                if flag_label:
                    layout.addWidget(QtWidgets.QLabel(_var_name))
                layout.addWidget(widget)
                self.l_w_arg.append(widget)

        self.function_attached = func
        self.thread_attached = thread

        if  len(self.l_w_arg) == 0:
            self.run_function()
            self.w_cb_hide.setCheckState(2)

    def is_defined(self):
        """Is defined."""
        return all([w_arg.attached_object is not None
                    for w_arg in self.l_w_arg])

    def run_function(self) -> NoReturn:
        """Run function."""
        func = self.function_attached
        thread = self.thread_attached
        if func is None:
            return

        l_w_arg = self.l_w_arg
        self.push_button.setEnabled(False)
        l_x = [_.attached_object for _ in l_w_arg]

        if self.globaln is not None:
            t_x = tuple([self.globaln, ] + l_x)
        else:
            t_x = tuple(l_x)
        if thread is None:
            try:
                func(*t_x)
            except Exception:
                pass
            self.calculation_finished()
        else:
            thread.function = func
            thread.arguments = t_x
            thread.signal_end.connect(self.calculation_finished)
            thread.start()

    def calculation_finished(self):
        """After calculations."""
        # self.w_cb_hide.setCheckState(2)
        self.push_button.setEnabled(True)


class DropLabel(QtWidgets.QLineEdit):  # FIXME: remove to another file
    """Drop label."""

    def __init__(self, *args, **kwargs):
        super(DropLabel, self).__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.attached_object = None
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.editingFinished.connect(self.convert_to_object)
        self.selectionChanged.connect(lambda: self.setText(""))

    def dragEnterEvent(self, event):
        """Drag enter event."""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Drop event."""
        # pos = event.pos()
        mime_data = event.mimeData()
        if not(mime_data.hasText()):
            event.ignore()
            return
        event.setDropAction(QtCore.Qt.CopyAction)
        s_cont = mime_data.text()

        l_item = cryspy.str_to_items(s_cont)
        if len(l_item) > 0:
            item = l_item[0]
            self.attached_object = item
            s_cont = type(item).__name__
        else:
            event.ignore()
            return

        self.setText(s_cont)
        self.setStyleSheet("")

        event.acceptProposedAction()

    def convert_to_object(self):
        """Convert to object."""
        text = self.text()
        obj = None
        flag = False
        flag_comma = (text.find(',') != -1)
        if flag_comma:
            l_text = text.split(",")
            try:
                obj = numpy.array(l_text, dtype=int)
                flag = True
            except Exception:
                pass
            if not flag:
                try:
                    obj = numpy.array(l_text, dtype=float)
                    flag = True
                except Exception:
                    pass
        else:
            try:
                obj = int(text)
                flag = True
            except Exception:
                pass
            if not flag:
                try:
                    obj = float(text)
                    flag = True
                except Exception:
                    pass
        if not flag:
            obj = str(text)

        self.attached_object = obj
        self.setAlignment(QtCore.Qt.AlignRight)
        self.setStyleSheet("")


def w_for_function(obj: Callable, layout_11: QtWidgets.QBoxLayout,
                    layout_12: QtWidgets.QBoxLayout,
                    layout_13: QtWidgets.QBoxLayout,
                    layout_2: QtWidgets.QBoxLayout,
                    layout_3: QtWidgets.QBoxLayout, w_output: QtWidgets.QWidget,
                    thread: QtCore.QThread) -> NoReturn:  # FIXME delete it
    """Widget for WFunction."""
    w_out = WFunction()
    w_out.set_function(obj, thread)
    layout_11.addWidget(w_out)


def del_layout(layout):  # FIXME delete it
    """Delete all elements from layouts."""
    for i in reversed(range(layout.count())):
        if layout.itemAt(i).widget() is not None:
            layout.itemAt(i).widget().setParent(None)
        elif layout.itemAt(i).layout() is not None:
            del_layout(layout.itemAt(i).layout())
            layout.itemAt(i).layout().setParent(None)
        else:
            layout.removeItem(layout.itemAt(i))

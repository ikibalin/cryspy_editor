"""Form of the parameters of a CrysPy procedure.

The form is made from the description of the procedure given by CrysPy
(cryspy.describe_procedure: type hints and numpydoc docstring), so that
CrysPy Editor keeps no description of its own: the summary and the
description of the procedure are shown on top, every parameter is a field
with its description as tooltip, the items of the object (Cell, ...) are
chosen in a list, and the values are checked by CrysPy
(cryspy.convert_assistant_answer), as the answers to the AI assistant.

Functions that CrysPy cannot describe (methods of the objects with numpy
arrays, ...) get the simpler ArgumentsDialog: a field for every parameter.
Both open in a separate window.
"""
import ast
import html
import inspect

import cryspy
import numpy
from cryspy import DataN, GlobalN, ItemN, LoopN
from cryspy.procedure_assistant.procedures import (
    describe_procedure,
    find_cif_objects,
    take_procedure_parameters,
)
from PyQt5 import QtCore, QtWidgets


def take_description(function):
    """Description of the procedure by CrysPy, None if CrysPy cannot
    describe it (parameters of other types)."""
    try:
        return describe_procedure(function)
    except (TypeError, ValueError, AttributeError):
        return None


def is_autorun(d_procedure: dict) -> bool:
    """The procedure needs only the object: it runs without the form."""
    return all(d_param["kind"] == "global" for d_param in d_procedure["parameters"])


def form_tooltip(d_procedure: dict) -> str:
    return "\n\n".join(text for text in (d_procedure["summary"], d_procedure["description"]) if text)


class ProcedureDialog(QtWidgets.QDialog):
    """Parameters of a procedure; arguments() gives them in the order of the
    signature after the dialog is accepted."""

    def __init__(self, function, d_procedure: dict, cryspy_object, parent=None):
        super().__init__(parent)
        self.function = function
        self.d_procedure = d_procedure
        self.cryspy_object = cryspy_object
        self.setWindowTitle(d_procedure["title"])
        d_types = {param: types for param, _, types, _ in take_procedure_parameters(function)}

        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel(
            f"<b>{html.escape(d_procedure['summary'] or d_procedure['title'])}</b>"
            + (f"<br>{html.escape(d_procedure['description'])}".replace("\n", "<br>")
               if d_procedure["description"] else ""))
        label.setWordWrap(True)
        layout.addWidget(label)

        form = QtWidgets.QFormLayout()
        self.d_widget = {}
        self.d_found = {}
        for d_param in d_procedure["parameters"]:
            name, kind = d_param["name"], d_param["kind"]
            if kind == "global":
                continue
            if kind == "cif":
                d_found = find_cif_objects(cryspy_object, d_types[name])
                self.d_found[name] = d_found
                widget = QtWidgets.QComboBox()
                widget.addItems(list(d_found))
                if len(d_found) == 0:
                    widget.addItem(f"no {' or '.join(d_param['classes'])} in the object")
                    widget.setEnabled(False)
            elif d_param["type"] == "boolean":
                widget = QtWidgets.QCheckBox()
                widget.setChecked(bool(d_param.get("default", False)))
            else:
                widget = QtWidgets.QLineEdit()
                if "default" in d_param:
                    widget.setText(str(d_param["default"]))
                widget.setPlaceholderText(d_param["type"])
            widget.setToolTip(d_param["description"] or d_param.get("question", name))
            self.d_widget[name] = widget
            form.addRow(name, widget)
        layout.addLayout(form)

        self.label_error = QtWidgets.QLabel()
        self.label_error.setStyleSheet("color: red")
        self.label_error.setWordWrap(True)
        self.label_error.hide()
        layout.addWidget(self.label_error)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.button(QtWidgets.QDialogButtonBox.Ok).setText("Run")
        buttons.accepted.connect(self.accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.l_argument = None

    def take_arguments(self) -> tuple:
        """Positional arguments of the procedure (CThread runs
        function(*arguments)): the values of the fields checked by CrysPy
        and the defaults of the other parameters; raises ValueError with a
        message for the user."""
        d_value = {}
        for d_param in self.d_procedure["parameters"]:
            name, kind = d_param["name"], d_param["kind"]
            if kind == "global":
                d_value[name] = self.cryspy_object
                continue
            widget = self.d_widget[name]
            if kind == "cif":
                label = widget.currentText()
                if label not in self.d_found[name]:
                    raise ValueError(f"{name}: the object has no {' or '.join(d_param['classes'])}.")
                d_value[name] = self.d_found[name][label]
            elif d_param["type"] == "boolean":
                d_value[name] = widget.isChecked()
            else:
                try:
                    d_value[name] = cryspy.convert_assistant_answer(d_param, widget.text())
                except ValueError as e:
                    raise ValueError(f"{name}: {e}") from e
        bound = inspect.signature(self.function).bind(**d_value)
        bound.apply_defaults()
        return bound.args

    def accept_if_valid(self):
        try:
            self.l_argument = self.take_arguments()
        except ValueError as e:
            self.label_error.setText(str(e))
            self.label_error.show()
            return
        self.accept()

    def arguments(self) -> tuple:
        return self.l_argument


def text_to_value(text: str, d_object: dict | None = None):
    """Value typed by the user for a parameter that CrysPy does not
    describe: the label of an object ('crystal_name.cell'), an integer, a
    float, numbers separated by commas (numpy array), a Python literal
    (list, tuple, True, None, ...) or else the text itself."""
    text = text.strip()
    if d_object is not None and text in d_object:
        return d_object[text]
    for convert in (int, float):
        try:
            return convert(text)
        except ValueError:
            pass
    if "," in text and not text.startswith(("[", "(", "{")):
        for dtype in (int, float):
            try:
                return numpy.array([_.strip() for _ in text.split(",")], dtype=dtype)
            except ValueError:
                pass
    try:
        value = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text
    if isinstance(value, (list, tuple)):
        try:
            return numpy.array(value, dtype=float)
        except (ValueError, TypeError):
            pass
    return value


class ArgumentsDialog(QtWidgets.QDialog):
    """Parameters of a function (a method of an object) that CrysPy does
    not describe: a field for every parameter, with its default; the object
    and the items of the object are taken by their labels.
    arguments() gives the keyword arguments after the dialog is accepted."""

    def __init__(self, function, cryspy_object, parent=None):
        super().__init__(parent)
        self.function = function
        self.cryspy_object = cryspy_object
        self.d_object = find_cif_objects(cryspy_object, (ItemN, LoopN, DataN))
        name = getattr(function, "__name__", "function")
        self.setWindowTitle(name)
        layout = QtWidgets.QVBoxLayout(self)
        doc = inspect.getdoc(function) or ""
        label = QtWidgets.QLabel(
            f"<b>{html.escape(name)}</b>"
            + (f"<br>{html.escape(doc)}".replace("\n", "<br>") if doc else ""))
        label.setWordWrap(True)
        label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(label)
        scroll.setMaximumHeight(250)
        layout.addWidget(scroll)

        form = QtWidgets.QFormLayout()
        self.d_widget = {}
        self.d_parameter = {}
        for param in take_function_parameters(function):
            annotation = param.annotation
            if isinstance(annotation, type) and issubclass(annotation, GlobalN) \
                    and cryspy_object is not None:
                self.d_parameter[param.name] = param
                continue  # the opened object
            widget = QtWidgets.QLineEdit()
            if param.default is not inspect.Parameter.empty:
                widget.setPlaceholderText(f"{param.default!r} (default)")
            else:
                widget.setPlaceholderText("value or label of an object")
            if annotation is not inspect.Parameter.empty:
                widget.setToolTip(f"{param.name}: {inspect.formatannotation(annotation)}")
            self.d_widget[param.name] = widget
            self.d_parameter[param.name] = param
            form.addRow(param.name, widget)
        if len(self.d_object) > 0 and len(self.d_widget) > 0:
            label_objects = QtWidgets.QLabel(
                "Objects: " + ", ".join(html.escape(_) for _ in self.d_object))
            label_objects.setWordWrap(True)
            form.addRow(label_objects)
        layout.addLayout(form)

        self.label_error = QtWidgets.QLabel()
        self.label_error.setStyleSheet("color: red")
        self.label_error.setWordWrap(True)
        self.label_error.hide()
        layout.addWidget(self.label_error)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.button(QtWidgets.QDialogButtonBox.Ok).setText("Run")
        buttons.accepted.connect(self.accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.d_argument = None

    def take_arguments(self) -> dict:
        """Keyword arguments of the function; raises ValueError with a
        message for the user."""
        d_value = {}
        for name, param in self.d_parameter.items():
            widget = self.d_widget.get(name)
            if widget is None:
                d_value[name] = self.cryspy_object
                continue
            text = widget.text().strip()
            if text == "":
                if param.default is inspect.Parameter.empty:
                    raise ValueError(f"{name}: a value is needed.")
                continue  # the default
            d_value[name] = text_to_value(text, self.d_object)
        return d_value

    def accept_if_valid(self):
        try:
            self.d_argument = self.take_arguments()
        except ValueError as e:
            self.label_error.setText(str(e))
            self.label_error.show()
            return
        self.accept()

    def arguments(self) -> dict:
        return self.d_argument


def split_arguments(function, d_argument: dict):
    """(args, kwargs) to call the function with the values d_argument:
    positional up to the last given parameter (the defaults in between),
    so that CThread, which runs function(*args), can run it; kwargs only for
    keyword-only parameters."""
    signature = inspect.signature(function)
    l_arg, d_kwarg, l_wait = [], {}, []
    for param in signature.parameters.values():
        if param.kind == param.KEYWORD_ONLY:
            if param.name in d_argument:
                d_kwarg[param.name] = d_argument[param.name]
        elif param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD):
            if param.name in d_argument:
                l_arg.extend(l_wait)
                l_wait = []
                l_arg.append(d_argument[param.name])
            else:
                l_wait.append(param.default)
    return tuple(l_arg), d_kwarg


def take_function_parameters(function) -> list:
    """Parameters of the function shown to the user: without self, *args,
    **kwargs and d_info (filled by the editor)."""
    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        return []
    return [param for param in signature.parameters.values()
            if param.name not in ("self", "d_info", "callback")
            and param.kind not in (param.VAR_POSITIONAL, param.VAR_KEYWORD)]

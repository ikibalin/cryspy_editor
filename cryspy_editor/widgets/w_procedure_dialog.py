"""Form of the parameters of a CrysPy procedure.

The form is made from the description of the procedure given by CrysPy
(cryspy.describe_procedure: type hints and numpydoc docstring), so that
CrysPy Editor keeps no description of its own: the summary and the
description of the procedure are shown on top, every parameter is a field
with its description as tooltip, the items of the object (Cell, ...) are
chosen in a list, and the values are checked by CrysPy
(cryspy.convert_assistant_answer), as the answers to the AI assistant.
"""
import html
import inspect

import cryspy
from PyQt5 import QtWidgets

try:
    from cryspy.procedure_assistant.procedures import (
        describe_procedure,
        find_cif_objects,
        take_procedure_parameters,
    )
except ImportError:  # CrysPy before procedure descriptions: the old panel is used
    describe_procedure = find_cif_objects = take_procedure_parameters = None


def take_description(function):
    """Description of the procedure by CrysPy, None if CrysPy cannot
    describe it (older CrysPy, or parameters of other types)."""
    if describe_procedure is None:
        return None
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

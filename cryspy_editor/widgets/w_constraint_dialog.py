"""Dialog to add a constraint between refined parameters: hard (x+y=1 holds
exactly) or soft (x+y=1 within sigma, added to chi-square).

The parameters, their marks and the constraint loop are handled by CrysPy
(cryspy.take_marked_parameters, cryspy.propose_mark, cryspy.add_constraint):
the dialog only lets the user tick the parameters, edit their marks and
write the equation.
"""
import inspect

import cryspy
from PyQt5 import QtCore, QtWidgets

COLUMN_USE, COLUMN_MARK, COLUMN_PATH, COLUMN_VALUE = range(4)


def is_constraint_supported() -> bool:
    """CrysPy knows the loop of constraints."""
    return hasattr(cryspy, "add_constraint") and hasattr(cryspy, "take_marked_parameters")


def is_soft_constraint_supported() -> bool:
    """CrysPy knows soft constraints (add_constraint takes sigma)."""
    if not is_constraint_supported():
        return False
    return "sigma" in inspect.signature(cryspy.add_constraint).parameters


def format_number(value) -> str:
    try:
        return f"{float(value):.6g}"
    except (TypeError, ValueError):
        return str(value)


class ConstraintDialog(QtWidgets.QDialog):
    """Tick the parameters, give them marks and write the equation; the
    check box "Soft constraint" adds sigma (a restraint)."""

    def __init__(self, cryspy_object, parent=None, flag_soft: bool = False):
        super().__init__(parent)
        self.cryspy_object = cryspy_object
        self.added_constraint = None
        self.setWindowTitle("Add constraint")
        self.resize(720, 520)
        self.l_parameter = [
            d_par for d_par in cryspy.take_marked_parameters(cryspy_object)
            if not d_par["constrained"]]

        layout = QtWidgets.QVBoxLayout(self)
        self.label_help = QtWidgets.QLabel("")
        self.label_help.setWordWrap(True)
        layout.addWidget(self.label_help)

        l_expression = cryspy.take_constraints(cryspy_object)
        if len(l_expression) > 0:
            label_old = QtWidgets.QLabel("Constraints: " + ";  ".join(l_expression))
            label_old.setWordWrap(True)
            layout.addWidget(label_old)

        self.line_filter = QtWidgets.QLineEdit()
        self.line_filter.setPlaceholderText("Filter: occupancy, atom_site[Fe], cell ...")
        self.line_filter.setClearButtonEnabled(True)
        self.line_filter.textChanged.connect(self.apply_filter)
        layout.addWidget(self.line_filter)

        self.table = QtWidgets.QTableWidget(len(self.l_parameter), 4)
        self.table.setHorizontalHeaderLabels(["Use", "Mark", "Parameter", "Value"])
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COLUMN_PATH, QtWidgets.QHeaderView.Stretch)
        for i_row, d_par in enumerate(self.l_parameter):
            item_use = QtWidgets.QTableWidgetItem()
            item_use.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            item_use.setCheckState(QtCore.Qt.Unchecked)
            self.table.setItem(i_row, COLUMN_USE, item_use)
            item_mark = QtWidgets.QTableWidgetItem(d_par["mark"])
            item_mark.setToolTip("Name of the parameter in the equation")
            self.table.setItem(i_row, COLUMN_MARK, item_mark)
            for column, text in ((COLUMN_PATH, d_par["path"]),
                                 (COLUMN_VALUE, format_number(d_par["value"]))):
                item = QtWidgets.QTableWidgetItem(text)
                item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                self.table.setItem(i_row, column, item)
        self.table.resizeColumnToContents(COLUMN_USE)
        self.table.itemChanged.connect(self.item_changed)
        layout.addWidget(self.table)

        form = QtWidgets.QFormLayout()
        self.line_expression = QtWidgets.QLineEdit()
        self.line_expression.setPlaceholderText("x + y = 1")
        form.addRow("Equation:", self.line_expression)
        self.check_soft = QtWidgets.QCheckBox("Soft constraint (restraint): holds within sigma")
        self.check_soft.setToolTip(
            "((left - right)/sigma)² is added to chi-square instead of holding the "
            "equation exactly; any formula of the marks is allowed")
        self.line_sigma = QtWidgets.QLineEdit()
        self.line_sigma.setPlaceholderText("0.01")
        self.line_sigma.setToolTip("Allowed deviation of the equation, in its units")
        if is_soft_constraint_supported():
            form.addRow("", self.check_soft)
            form.addRow("Sigma:", self.line_sigma)
        self.check_soft.toggled.connect(self.set_soft)
        layout.addLayout(form)

        self.label_error = QtWidgets.QLabel("")
        self.label_error.setWordWrap(True)
        self.label_error.setStyleSheet("color: #d04040;")
        layout.addWidget(self.label_error)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.button(QtWidgets.QDialogButtonBox.Ok).setText("Add")
        buttons.accepted.connect(self.accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.flag_expression_edited = False
        self.line_expression.textEdited.connect(self.expression_edited)
        self.check_soft.setChecked(flag_soft and is_soft_constraint_supported())
        self.set_soft(self.check_soft.isChecked())

    @property
    def flag_soft(self) -> bool:
        return self.check_soft.isChecked()

    def set_soft(self, flag_soft: bool):
        self.line_sigma.setEnabled(bool(flag_soft))
        if flag_soft:
            text = ("Tick the parameters, check their marks and write an equation of "
                    "the marks, e.g. <b>x + y = 1</b> or <b>sqrt(a**2 + b**2) = 2.5</b>, "
                    "and its sigma. The ticked parameters are refined; ((left - right)/sigma)² "
                    "is added to chi-square, so the equation holds within about sigma.")
        else:
            text = ("Tick the parameters, check their marks and write a linear equation "
                    "of the marks, e.g. <b>x + y = 1</b>. The ticked parameters are refined; "
                    "during the refinement the equation holds exactly.")
        self.label_help.setText(text)

    def expression_edited(self, *argv):
        self.flag_expression_edited = self.line_expression.text().strip() != ""

    def apply_filter(self, text: str):
        text_sh = text.strip().lower()
        for i_row, d_par in enumerate(self.l_parameter):
            flag_hide = text_sh != "" and text_sh not in d_par["path"].lower() and \
                self.table.item(i_row, COLUMN_USE).checkState() != QtCore.Qt.Checked
            self.table.setRowHidden(i_row, flag_hide)

    def item_changed(self, item):
        if item.column() != COLUMN_USE:
            if item.column() == COLUMN_MARK:
                self.propose_expression()
            return
        i_row = item.row()
        item_mark = self.table.item(i_row, COLUMN_MARK)
        if item.checkState() == QtCore.Qt.Checked and item_mark.text().strip() == "":
            mark = cryspy.propose_mark(self.cryspy_object, self.l_parameter[i_row]["path"])
            # also unique among the marks proposed in this dialog
            l_used = {self.table.item(i_other, COLUMN_MARK).text().strip()
                      for i_other in range(self.table.rowCount()) if i_other != i_row}
            base = mark.rstrip("0123456789")
            index = int(mark[len(base):] or 1)
            while f"{base:}{index:}" in l_used:
                index += 1
            self.table.blockSignals(True)
            item_mark.setText(f"{base:}{index:}")
            self.table.blockSignals(False)
        elif item.checkState() != QtCore.Qt.Checked and \
                self.l_parameter[i_row]["mark"] == "":
            self.table.blockSignals(True)
            item_mark.setText("")
            self.table.blockSignals(False)
        self.propose_expression()

    def checked_rows(self) -> list:
        return [i_row for i_row in range(self.table.rowCount())
                if self.table.item(i_row, COLUMN_USE).checkState() == QtCore.Qt.Checked]

    def propose_expression(self):
        """'x + y = <sum of the values>' until the user edits the equation."""
        if self.flag_expression_edited:
            return
        l_row = self.checked_rows()
        l_mark = [self.table.item(i_row, COLUMN_MARK).text().strip() for i_row in l_row]
        if len(l_row) == 0 or "" in l_mark:
            self.line_expression.setText("")
            return
        total = 0.
        for i_row, mark in zip(l_row, l_mark):
            value = float(self.l_parameter[i_row]["value"])
            total += -value if mark.endswith("-") else value
        l_mark = [mark.rstrip("-+") for mark in l_mark]
        self.line_expression.setText(f"{' + '.join(l_mark):} = {format_number(total):}")

    def mark_paths(self) -> dict:
        """Marks to give: mark -> path of the ticked parameters whose mark
        is new or changed."""
        d_mark_path = {}
        for i_row in self.checked_rows():
            mark = self.table.item(i_row, COLUMN_MARK).text().strip()
            d_par = self.l_parameter[i_row]
            if mark != d_par["mark"] or not d_par["refined"]:
                d_mark_path[mark.rstrip("-+") if mark != d_par["mark"] else mark] = d_par["path"]
        return d_mark_path

    def accept_if_valid(self):
        expression = self.line_expression.text().strip()
        if expression == "":
            self.label_error.setText("Write the equation, e.g. x + y = 1.")
            return
        l_empty = [self.l_parameter[i_row]["path"] for i_row in self.checked_rows()
                   if self.table.item(i_row, COLUMN_MARK).text().strip() == ""]
        if len(l_empty) > 0:
            self.label_error.setText(f"Give a mark to {l_empty[0]:}.")
            return
        d_mark_path = {mark: path for mark, path in self.mark_paths().items()
                       if not mark.endswith("-")}
        d_sigma = {}
        if self.flag_soft:
            try:
                d_sigma["sigma"] = float(self.line_sigma.text().strip())
            except ValueError:
                self.label_error.setText("Write sigma as a positive number, e.g. 0.01.")
                return
        try:
            self.added_constraint = cryspy.add_constraint(
                self.cryspy_object, expression, d_mark_path, **d_sigma)
        except (cryspy.CrysPyError, ValueError) as error:
            self.label_error.setText(str(error))
            return
        self.accept()

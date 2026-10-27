"""Window "Parameters": all refinable parameters of the object in one table.

The user ticks the parameters to refine, edits their values and keeps
favorite parameters on top, without walking through every item and loop.
The parameters and their paths come from CrysPy
(cryspy.procedure_assistant.parameters), so every class of CrysPy is shown.

Favorites are paths ('crystal_fe.atom_site[Fe1].occupancy') kept in the
settings of the Editor: they come back on top in every file that has a
parameter with the same path.
"""
from collections.abc import Callable

from cryspy.procedure_assistant.parameters import take_parameter_records
from PyQt5 import QtCore, QtGui, QtWidgets

COLUMN_FAVORITE, COLUMN_REFINE, COLUMN_PATH, COLUMN_VALUE, COLUMN_SIGMA = range(5)
KEY_FAVORITES = "favorite_parameters"
STAR = "★"


def is_number(value) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return not isinstance(value, (str, bool))


def format_number(value) -> str:
    if is_number(value):
        return f"{float(value):.6g}"
    return str(value)


def take_records(cryspy_object) -> list:
    """Refinable parameters which have a value in the object."""
    if cryspy_object is None:
        return []
    try:
        return take_parameter_records(cryspy_object)
    except Exception:
        return []


class ParametersDialog(QtWidgets.QDialog):
    """Table of the parameters: favorite, refinement, path, value, sigma.

    Changes go to the object at once; on_changed(label, text_before) is
    called after each change so that the main window keeps the history
    and renews its panels.
    """

    def __init__(self, take_object: Callable, d_setup: dict, save_settings: Callable,
                 on_changed: Callable, parent=None):
        super().__init__(parent)
        self.take_object = take_object
        self.d_setup = d_setup
        self.save_settings = save_settings
        self.on_changed = on_changed
        self.l_record = []
        self.flag_filling = False
        self.setWindowTitle("Parameters")
        self.resize(820, 620)

        layout = QtWidgets.QVBoxLayout(self)
        label_help = QtWidgets.QLabel(
            f"Tick <b>Refine</b> for the parameters to refine and edit their values "
            f"here. Mark your favorite parameters with {STAR}: they are always on top.")
        label_help.setWordWrap(True)
        layout.addWidget(label_help)

        layout_filter = QtWidgets.QHBoxLayout()
        self.line_filter = QtWidgets.QLineEdit()
        self.line_filter.setPlaceholderText("Filter: occupancy, atom_site[Fe], cell, *.scale ...")
        self.line_filter.setClearButtonEnabled(True)
        self.line_filter.textChanged.connect(self.apply_filter)
        layout_filter.addWidget(self.line_filter)
        self.check_favorites = QtWidgets.QCheckBox(f"Only {STAR}")
        self.check_favorites.setToolTip("Show the favorite parameters only")
        self.check_favorites.toggled.connect(self.apply_filter)
        layout_filter.addWidget(self.check_favorites)
        self.check_refined = QtWidgets.QCheckBox("Only refined")
        self.check_refined.toggled.connect(self.apply_filter)
        layout_filter.addWidget(self.check_refined)
        layout.addLayout(layout_filter)

        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([STAR, "Refine", "Parameter", "Value", "Sigma"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COLUMN_PATH, QtWidgets.QHeaderView.Stretch)
        self.table.itemChanged.connect(self.item_changed)
        layout.addWidget(self.table)

        layout_button = QtWidgets.QHBoxLayout()
        self.label_count = QtWidgets.QLabel("")
        layout_button.addWidget(self.label_count)
        layout_button.addStretch()
        for text, tooltip, slot in (
                ("Refine selected", "Refine the selected rows", self.refine_selected),
                ("Fix selected", "Do not refine the selected rows", self.fix_selected),
                ("Fix all", "Do not refine any parameter", self.fix_all)):
            button = QtWidgets.QPushButton(text)
            button.setToolTip(tooltip)
            button.setAutoDefault(False)
            button.clicked.connect(slot)
            layout_button.addWidget(button)
        button_close = QtWidgets.QPushButton("Close")
        button_close.setAutoDefault(False)
        button_close.clicked.connect(self.close)
        layout_button.addWidget(button_close)
        layout.addLayout(layout_button)
        self.refresh()

    # favorites ----------------------------------------------------------
    def take_favorites(self) -> list[str]:
        l_favorite = self.d_setup.get(KEY_FAVORITES, [])
        return list(l_favorite) if isinstance(l_favorite, (list, tuple)) else []

    def set_favorite(self, path: str, flag: bool):
        l_favorite = [hh for hh in self.take_favorites() if hh != path]
        if flag:
            l_favorite.append(path)
        self.d_setup[KEY_FAVORITES] = l_favorite
        self.save_settings()

    # table ----------------------------------------------------------------
    def refresh(self):
        """Read the parameters of the object again (after a refinement, a
        new file, an edit in the other panels)."""
        l_record = take_records(self.take_object())
        l_favorite = self.take_favorites()
        # favorites on top in the order they were chosen, then the others
        d_order = {path: index for index, path in enumerate(l_favorite)}
        l_record.sort(key=lambda record: d_order.get(record.path, len(d_order)))
        if [record.path for record in l_record] == [record.path for record in self.l_record]:
            self.l_record = l_record
            self.fill_values()
        else:
            self.l_record = l_record
            self.fill_table()
        self.apply_filter()

    def fill_table(self):
        self.flag_filling = True
        l_favorite = set(self.take_favorites())
        self.table.setRowCount(len(self.l_record))
        for i_row, record in enumerate(self.l_record):
            item_favorite = QtWidgets.QTableWidgetItem("")
            item_favorite.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            item_favorite.setCheckState(
                QtCore.Qt.Checked if record.path in l_favorite else QtCore.Qt.Unchecked)
            item_favorite.setToolTip("Favorite: always on top")
            self.table.setItem(i_row, COLUMN_FAVORITE, item_favorite)
            item_refine = QtWidgets.QTableWidgetItem("")
            self.table.setItem(i_row, COLUMN_REFINE, item_refine)
            item_path = QtWidgets.QTableWidgetItem(record.path)
            item_path.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            font = item_path.font()
            font.setBold(record.path in l_favorite)
            item_path.setFont(font)
            self.table.setItem(i_row, COLUMN_PATH, item_path)
            self.table.setItem(i_row, COLUMN_VALUE, QtWidgets.QTableWidgetItem(""))
            item_sigma = QtWidgets.QTableWidgetItem("")
            item_sigma.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.table.setItem(i_row, COLUMN_SIGMA, item_sigma)
        self.flag_filling = False
        self.fill_values()
        self.table.resizeColumnToContents(COLUMN_FAVORITE)
        self.table.resizeColumnToContents(COLUMN_REFINE)

    def fill_values(self):
        """Refinement flags, values and sigmas of the rows."""
        self.flag_filling = True
        color_fixed = self.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text)
        for i_row, record in enumerate(self.l_record):
            item_refine = self.table.item(i_row, COLUMN_REFINE)
            if record.flag_constraint:
                # fixed by symmetry: cannot be refined
                item_refine.setFlags(QtCore.Qt.ItemIsSelectable)
                item_refine.setToolTip("Fixed by symmetry")
                self.table.item(i_row, COLUMN_PATH).setForeground(color_fixed)
            else:
                item_refine.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled
                                     | QtCore.Qt.ItemIsSelectable)
                item_refine.setToolTip("")
            item_refine.setCheckState(
                QtCore.Qt.Checked if record.flag_refinement else QtCore.Qt.Unchecked)
            self.table.item(i_row, COLUMN_VALUE).setText(format_number(record.value))
            try:
                sigma = record.sigma if record.flag_refinement else 0.
            except (TypeError, ValueError):
                sigma = 0.
            self.table.item(i_row, COLUMN_SIGMA).setText(
                format_number(sigma) if sigma != 0. else "")
        self.flag_filling = False
        n_refined = sum(record.flag_refinement for record in self.l_record)
        self.label_count.setText(f"Refined: {n_refined:} of {len(self.l_record):}")

    def apply_filter(self, *argv):
        text = self.line_filter.text().strip().lower()
        l_favorite = set(self.take_favorites())
        flag_only_favorites = self.check_favorites.isChecked()
        flag_only_refined = self.check_refined.isChecked()
        for i_row, record in enumerate(self.l_record):
            flag_favorite = record.path in l_favorite
            if (flag_only_favorites and not flag_favorite) or \
                    (flag_only_refined and not record.flag_refinement):
                flag_hide = True
            else:
                # favorites stay in view whatever the filter is
                flag_hide = not flag_favorite and not match_filter(record.path, text)
            self.table.setRowHidden(i_row, flag_hide)

    # changes ----------------------------------------------------------------
    def take_text_before(self):
        try:
            return self.take_object().to_cif()
        except Exception:
            return None

    def item_changed(self, item):
        if self.flag_filling:
            return
        i_row, column = item.row(), item.column()
        record = self.l_record[i_row]
        if column == COLUMN_FAVORITE:
            self.set_favorite(record.path, item.checkState() == QtCore.Qt.Checked)
            self.apply_filter()
        elif column == COLUMN_REFINE:
            flag = item.checkState() == QtCore.Qt.Checked
            if flag != record.flag_refinement:
                self.set_refinement([record], flag)
        elif column == COLUMN_VALUE:
            self.set_value(record, item.text())

    def set_value(self, record, text: str):
        try:
            value = float(text.replace(",", "."))
        except ValueError:
            self.fill_values()
            return
        if is_number(record.value) and float(record.value) == value:
            return
        text_before = self.take_text_before()
        record.set_value(value)
        self.changed(f"{record.path:} = {value:g}", text_before)

    def set_refinement(self, l_record: list, flag: bool):
        l_record = [record for record in l_record
                    if record.flag_refinement != flag and not record.flag_constraint]
        if len(l_record) == 0:
            self.fill_values()
            return
        text_before = self.take_text_before()
        for record in l_record:
            record.set_refinement(flag)
        if len(l_record) == 1:
            label = ("refine " if flag else "fix ") + l_record[0].path
        else:
            label = ("refine " if flag else "fix ") + f"{len(l_record):} parameters"
        self.changed(label, text_before)

    def changed(self, label: str, text_before):
        self.fill_values()
        self.apply_filter()
        self.on_changed(label, text_before)

    def selected_records(self) -> list:
        l_row = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        return [self.l_record[i_row] for i_row in l_row if not self.table.isRowHidden(i_row)]

    def refine_selected(self):
        self.set_refinement(self.selected_records(), True)

    def fix_selected(self):
        self.set_refinement(self.selected_records(), False)

    def fix_all(self):
        self.set_refinement(self.l_record, False)


def match_filter(path: str, text: str) -> bool:
    """Substring of the path, or a pattern with '*' ('*.scale')."""
    if text == "":
        return True
    path_lower = path.lower()
    if "*" in text:
        return QtCore.QRegExp(text, QtCore.Qt.CaseInsensitive,
                              QtCore.QRegExp.Wildcard).exactMatch(path_lower)
    return text in path_lower

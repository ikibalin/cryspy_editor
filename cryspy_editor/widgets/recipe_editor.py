"""Window to read, write and edit the recipes of the AI assistant.

A recipe is a text file of CrysPy (cryspy.procedure_assistant.recipes):
the steps of a typical analysis that the assistant follows one action at a
time. The recipes of CrysPy are read only; saving one of them writes a copy
in the folder of the user (the settings folder of CrysPy Editor), which
replaces it. Reading, checking and saving are done by CrysPy.
"""
import os

from cryspy.procedure_assistant.recipes import set_user_recipe_folder
from PyQt5 import QtCore, QtGui, QtWidgets

from cryspy_editor.settings import take_config_dir

S_RECIPE_FOLDER = "recipes"
WINDOW_TITLE = "AI assistant: CookBook (recipes)"
S_INFO = ("A recipe is the steps of an analysis that the assistant follows one action at "
          "a time. Write it in the format below (get_help 'recipe' explains it); 'Actions' "
          "are tool calls of CrysPy. Saving a recipe of CrysPy makes your copy, which "
          "replaces it; delete the copy to use the recipe of CrysPy again.")


def take_user_recipe_folder() -> str:
    return os.path.join(take_config_dir(), S_RECIPE_FOLDER)


def init_user_recipe_folder():
    """Give CrysPy the folder of the recipes of the user."""
    set_user_recipe_folder(take_user_recipe_folder())


def form_item_text(d_file: dict) -> str:
    s_text = d_file["name"]
    if d_file["flag_user"]:
        s_text += "  [yours]"
    elif d_file["flag_replaced"]:
        s_text += "  [replaced by yours]"
    if d_file["error"]:
        s_text += "  [error]"
    return s_text


class RecipeEditorDialog(QtWidgets.QDialog):
    """List of the recipes and the text of the chosen one."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from cryspy.procedure_assistant import recipes
        self.recipes = recipes
        init_user_recipe_folder()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1000, 650)
        self.l_file = []
        self.index_current = -1
        self.flag_modified = False

        layout = QtWidgets.QVBoxLayout(self)
        label_info = QtWidgets.QLabel(S_INFO)
        label_info.setWordWrap(True)
        layout.addWidget(label_info)
        label_folder = QtWidgets.QLabel(f"Your recipes: {take_user_recipe_folder()}")
        label_folder.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(label_folder)

        splitter = QtWidgets.QSplitter()
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.currentRowChanged.connect(self.on_row_changed)
        splitter.addWidget(self.list_widget)
        self.text_edit = QtWidgets.QPlainTextEdit()
        self.text_edit.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        self.text_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth)
        self.text_edit.textChanged.connect(self.on_text_changed)
        splitter.addWidget(self.text_edit)
        splitter.setSizes([250, 750])
        layout.addWidget(splitter, 1)

        self.label_status = QtWidgets.QLabel("")
        self.label_status.setWordWrap(True)
        layout.addWidget(self.label_status)

        layout_buttons = QtWidgets.QHBoxLayout()
        self.button_new = QtWidgets.QPushButton("New")
        self.button_new.clicked.connect(self.new_recipe)
        self.button_check = QtWidgets.QPushButton("Check")
        self.button_check.clicked.connect(self.check_text)
        self.button_save = QtWidgets.QPushButton("Save")
        self.button_save.clicked.connect(self.save_recipe)
        self.button_delete = QtWidgets.QPushButton("Delete")
        self.button_delete.clicked.connect(self.delete_recipe)
        button_close = QtWidgets.QPushButton("Close")
        button_close.clicked.connect(self.close)
        for button in (self.button_new, self.button_check, self.button_save, self.button_delete):
            layout_buttons.addWidget(button)
        layout_buttons.addStretch(1)
        layout_buttons.addWidget(button_close)
        layout.addLayout(layout_buttons)
        self.update_list()

    def update_list(self, name: str = ""):
        """Read the recipe files again; choose the recipe of the user named
        name, else the first one."""
        self.l_file = self.recipes.list_recipe_files()
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for d_file in self.l_file:
            self.list_widget.addItem(form_item_text(d_file))
            self.list_widget.item(self.list_widget.count() - 1).setToolTip(d_file["title"] or d_file["error"])
        l_index = [ind for ind, d_file in enumerate(self.l_file) if d_file["name"] == name]
        l_index.sort(key=lambda ind: not self.l_file[ind]["flag_user"])  # yours first
        index = l_index[0] if l_index else 0
        if len(self.l_file) > 0:
            self.list_widget.setCurrentRow(index)
            self.show_file(index)
        self.list_widget.blockSignals(False)

    def current_file(self):
        index = self.list_widget.currentRow()
        if 0 <= index < len(self.l_file):
            return self.l_file[index]
        return None

    def show_file(self, index: int):
        self.index_current = index
        d_file = self.l_file[index]
        try:
            with open(d_file["path"], "r", encoding="utf-8") as fid:
                text = fid.read()
        except (OSError, UnicodeDecodeError) as error:
            text = ""
            d_file = dict(d_file, error=str(error))
        self.set_text(text)
        self.button_delete.setEnabled(bool(d_file["flag_user"]))
        if d_file["error"]:
            self.set_status(f"Error: {d_file['error']}", flag_error=True)
        elif d_file["flag_user"]:
            self.set_status(f"Your recipe {d_file['path']}.")
        elif d_file["flag_replaced"]:
            self.set_status("A recipe of CrysPy, replaced by your recipe with the same name.")
        else:
            self.set_status("A recipe of CrysPy: Save makes your copy of it.")

    def set_text(self, text: str):
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(text)
        self.text_edit.blockSignals(False)
        self.flag_modified = False

    def set_status(self, text: str, flag_error: bool = False):
        self.label_status.setText(text)
        self.label_status.setStyleSheet("color: #d04040;" if flag_error else "")

    def on_text_changed(self):
        self.flag_modified = True

    def confirm_discard(self) -> bool:
        if not self.flag_modified:
            return True
        answer = QtWidgets.QMessageBox.question(
            self, WINDOW_TITLE, "The recipe is changed and not saved. Discard the changes?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        return answer == QtWidgets.QMessageBox.Yes

    def on_row_changed(self, index: int):
        if index < 0 or index >= len(self.l_file):
            return
        if not self.confirm_discard():
            self.list_widget.blockSignals(True)
            self.list_widget.setCurrentRow(self.index_current)
            self.list_widget.blockSignals(False)
            return
        self.show_file(index)

    def new_recipe(self):
        if not self.confirm_discard():
            return
        self.list_widget.blockSignals(True)
        self.list_widget.clearSelection()
        self.list_widget.setCurrentRow(-1)
        self.list_widget.blockSignals(False)
        self.index_current = -1
        self.set_text(self.recipes.S_TEMPLATE)
        self.flag_modified = True
        self.button_delete.setEnabled(False)
        self.set_status("A new recipe: change its name and steps, then Save.")

    def check_text(self) -> bool:
        """Parse and check the text; the result is shown in the status line."""
        try:
            recipe = self.recipes.parse_recipe(self.text_edit.toPlainText())
            l_problem = self.recipes.check_recipe(recipe)
        except ValueError as error:
            self.set_status(f"Error: {error}", flag_error=True)
            return False
        if len(l_problem) > 0:
            self.set_status("Error: " + "; ".join(l_problem), flag_error=True)
            return False
        self.set_status(f"Recipe {recipe.name} is correct: {len(recipe.steps)} steps.")
        return True

    def save_recipe(self):
        try:
            path = self.recipes.save_user_recipe(self.text_edit.toPlainText())
        except (OSError, ValueError) as error:
            self.set_status(f"Error: {error}. The recipe is not saved.", flag_error=True)
            return
        self.flag_modified = False
        name = os.path.splitext(os.path.basename(path))[0]
        self.update_list(name)
        self.set_status(f"Saved: {path}. The assistant uses it from the next request.")

    def delete_recipe(self):
        d_file = self.current_file()
        if d_file is None or not d_file["flag_user"]:
            return
        answer = QtWidgets.QMessageBox.question(
            self, WINDOW_TITLE, f"Delete your recipe {d_file['name']}?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if answer != QtWidgets.QMessageBox.Yes:
            return
        self.recipes.delete_user_recipe(d_file["name"])
        self.flag_modified = False
        self.update_list(d_file["name"])

    def closeEvent(self, event):
        if self.confirm_discard():
            event.accept()
        else:
            event.ignore()

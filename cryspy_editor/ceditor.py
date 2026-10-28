import os
import sys
import random
import string

import numpy
from typing import Union, NoReturn
from types import FunctionType

from PyQt5 import QtCore
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui

from PyQt5.QtWidgets import QMainWindow, QAction
from PyQt5.QtGui import QIcon

import matplotlib.pyplot as plt

from importlib import import_module
from cryspy_editor.widgets.ui_setting import is_dark_mode
from cryspy import (
    load_file,
    GlobalN,
    DataN,
    LoopN,
    ItemN,
    Pd2dMeas,
    Pd2dProc,
    ChannelAni,
    ChannelCol,
    str_to_globaln,
)
from cryspy import L_GLOBAL_CLASS, L_DATA_CLASS, L_ITEM_CLASS, L_LOOP_CLASS

L_GLOBAL_CLS = L_GLOBAL_CLASS
L_DATA_CLS = L_DATA_CLASS
L_LOOP_CLS = L_LOOP_CLASS
L_ITEM_CLS = L_ITEM_CLASS


from cryspy_editor.widgets.w_function import WFunction
from cryspy_editor.widgets.w_constraint_dialog import (
    ConstraintDialog,
    is_constraint_supported,
)
from cryspy_editor.widgets.w_parameters_dialog import ParametersDialog
from cryspy_editor.widgets.w_procedure_dialog import (
    ProcedureDialog,
    form_tooltip,
    is_autorun,
    take_description,
)
from cryspy_editor.widgets.w_object_panel import WObjectPanel
from cryspy_editor.widgets.w_editcif import (
    WEditCif, take_value_choices)
from cryspy_editor.widgets.w_textedit import WTextEdit
from cryspy_editor.widgets.matplotlib_g import Graph
from cryspy.procedure_assistant.parameters import take_parameter_records, is_number
from cryspy_editor.widgets.w_structure_view import (
    WStructureView, has_structure_view)
from cryspy_editor.widgets.cryspy_objects import (
    cryspy_procedures_to_dictionary,
    check_function_to_auto_run,
    check_function_for_procedure,
    get_plot_functions_for_data_loop_item,
    check_function_reserved_for_cryspy_editor,
)
from cryspy_editor.widgets.ui_assistant import AssistantController

from cryspy_editor.cl_thread import CThread
from cryspy_editor.history import RcifHistory
from cryspy_editor.settings import (
    take_settings, save_settings, add_recent_file)
from cryspy_editor import update_check

from cryspy import __version__ as cryspy_version
from cryspy_editor import __version__ as cryspy_editor_version


import os, sys, subprocess

# Cmd+. on macOS (the usual stop key there), Ctrl+. elsewhere; Esc as well.
STOP_SHORTCUT = "Ctrl+."
STOP_SHORTCUT_TEXT = "Cmd+. or Esc" if sys.platform == "darwin" else "Ctrl+. or Esc"


def open_file_wm(filename):
    if sys.platform == "win32":
        os.startfile(filename)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, filename])


def get_external_functions(l_f_name_external: list, l_error: list = None):
    """Procedures from user scripts; reading errors are added to l_error."""
    l_func_external = []
    for f_name in l_f_name_external:
        try:
            f_name_sh = f_name.strip()
            if os.path.isfile(f_name_sh):
                module_name = os.path.basename(f_name_sh)[:-3]
                module_way = os.path.dirname(f_name_sh)
                sys.path.append(module_way)
                module = import_module(module_name)
                for obj_name in dir(module):
                    if not (
                        (
                            obj_name.startswith("__")
                            or (
                                obj_name
                                in [
                                    "Callable",
                                ]
                            )
                        )
                    ):
                        obj = getattr(module, obj_name)

                        if hasattr(obj, "__call__"):
                            if check_function_for_procedure(obj):  #
                                l_func_external.append(obj)
                            elif check_function_reserved_for_cryspy_editor(
                                obj
                            ):
                                l_func_external.append(obj)
                    else:
                        pass
        except Exception as e:
            if l_error is not None:
                l_error.append(
                    f"User script '{f_name:}' is not loaded: "
                    f"{type(e).__name__}: {e}")
    return l_func_external


def take_item(rcif_object: Union[GlobalN, DataN, LoopN, ItemN], way: tuple):
    if len(way) > 0:
        way_1 = way[0]
        if rcif_object.is_attribute(way_1):
            item_object = getattr(rcif_object, way_1)
            item = take_item(item_object, way[1:])
            return item
        else:
            return None
    else:
        return rcif_object


def form_way(tree_widget_item: QtWidgets.QTreeWidgetItem):
    name_item = tree_widget_item.text(0)
    parent_tree_widget_item = tree_widget_item.parent()
    if isinstance(parent_tree_widget_item, QtWidgets.QTreeWidgetItem):
        way = form_way(parent_tree_widget_item)
        way_full = way + (name_item,)
    else:
        return (name_item,)
    return way_full


def form_dict_tree_for_rcif_object(rcif_object: GlobalN):
    dict_rcif = {}
    if isinstance(rcif_object, (GlobalN, DataN)):
        l_name = [item.get_name() for item in rcif_object.items]
        for item in rcif_object.items:
            name = item.get_name()
            key_name = f"ITEM_{name:}"
            dict_item = form_dict_tree_for_rcif_object(item)
            dict_rcif[key_name] = dict_item
    elif isinstance(rcif_object, ItemN):
        for attr_name in rcif_object.ATTR_INT_NAMES:
            if rcif_object.is_attribute(attr_name):
                int_obj = getattr(rcif_object, attr_name)
                if isinstance(int_obj, (ItemN, LoopN)):
                    key_name = f"ITEM_{attr_name:}"
                    dict_item = form_dict_tree_for_rcif_object(int_obj)
                    dict_rcif[key_name] = dict_item
        for attr_name in rcif_object.ATTR_INT_PROTECTED_NAMES:
            if attr_name in rcif_object.__dict__.keys():
                if rcif_object.is_attribute(attr_name):
                    int_obj = getattr(rcif_object, attr_name)
                    if isinstance(int_obj, (ItemN, LoopN)):
                        key_name = f"ITEM_{attr_name:}"
                        dict_item = form_dict_tree_for_rcif_object(int_obj)
                        dict_rcif[key_name] = dict_item
    return dict_rcif


class OptionsWindow(QMainWindow):
    def __init__(self, parent):
        super(OptionsWindow, self).__init__(parent)
        self.setWindowTitle("Cryspy Editor: User Scripts")
        self.parent = parent
        widget_main = QtWidgets.QWidget(self)

        lay_hor = QtWidgets.QHBoxLayout()
        self.q_list = QtWidgets.QListWidget(widget_main)
        self.q_list.itemClicked.connect(self.item_clicked)
        lay_hor.addWidget(self.q_list)

        lay_buttons = QtWidgets.QVBoxLayout()
        button_add = QtWidgets.QPushButton("Add")
        button_add.clicked.connect(self.add_function)
        button_delete = QtWidgets.QPushButton("Delete")
        button_delete.clicked.connect(self.delete_function)
        button_template = QtWidgets.QPushButton("Show template")
        button_template.clicked.connect(self.show_template)

        lay_buttons.addWidget(button_add)
        lay_buttons.addWidget(button_delete)
        lay_buttons.addStretch(1)
        lay_buttons.addWidget(button_template)

        lay_hor.addLayout(lay_buttons)

        widget_main.setLayout(lay_hor)

        self.setCentralWidget(widget_main)

        self.form_q_list()

    def item_clicked(self, item: QtWidgets.QListWidgetItem):
        s_text = item.text()
        dir_name = os.path.dirname(s_text)
        if os.path.isdir(dir_name):
            open_file_wm(dir_name)

    def form_q_list(self):
        l_names = sorted(
            self.parent.d_setup["file_names_for_external_functions"].split(";")
        )
        self.q_list.addItems(l_names)

    def add_function(self):

        if "data_dir_name" in self.parent.d_setup.keys():
            f_dir = self.parent.d_setup["data_dir_name"]
        else:
            f_dir = "."

        QtWidgets.QMessageBox.information(
            self,
            "Tips",
            "File name must not match any of the Python modules!\nThen reboot 'CrysPy editor' to use the added procedures.",
        )

        file_name, ok = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open file", f_dir, "Python Files (*.py);; All Files (*)"
        )
        if ok:
            if (
                "file_names_for_external_functions"
                in self.parent.d_setup.keys()
            ):
                if (
                    self.parent.d_setup["file_names_for_external_functions"]
                    == ""
                ):
                    self.parent.d_setup[
                        "file_names_for_external_functions"
                    ] = file_name
                else:
                    self.parent.d_setup[
                        "file_names_for_external_functions"
                    ] += (";" + file_name)
            else:
                self.parent.d_setup["file_names_for_external_functions"] = (
                    file_name
                )
            self.q_list.addItem(file_name)
            save_settings()

    def delete_function(self):
        f_item = self.q_list.currentItem()
        try:
            f_delete = f_item.text()
            l_names = self.parent.d_setup[
                "file_names_for_external_functions"
            ].split(";")
            l_names_new = sorted(
                [name for name in l_names if not (name.startswith(f_delete))]
            )
            self.q_list.clear()
            self.parent.d_setup["file_names_for_external_functions"] = (
                ";".join(l_names_new)
            )
            save_settings()
            self.q_list.addItems(l_names_new)
        except AttributeError:  # nothing is selected
            pass

    def show_template(self):
        s_template = """import cryspy

def user_script_name(cryspy_object: cryspy.GlobalN):
    # define your procedure
    pass
    return         
        """
        QtWidgets.QMessageBox.information(self, "Tips", s_template)


class CMainWindow(QMainWindow):
    def __init__(self, file_name: str = None):
        """Main window; file_name is opened instead of the last used file."""
        super(CMainWindow, self).__init__()

        self.dir_prog = os.path.dirname(__file__)
        self.d_setup = take_settings()
        if file_name is not None:
            self.d_setup["data_file_name"] = os.path.abspath(file_name)

        self.functions_plot_data = []
        self.functions_plot_loop = []
        self.functions_plot_item = []
        # Thread block
        # states of the object before each change, to go back
        self.history = RcifHistory()
        self.cthread = CThread(self)
        self.cthread.signal_start.connect(self.run_calculations)
        self.cthread.signal_end.connect(self.end_calculations)
        self.cthread.signal_progress.connect(self.show_progress_text)
        self.cthread.functions_before_start.append(self.apply_cif_edits)
        self.cthread.functions_before_start.append(self.remember_before_run)

        self.setWindowTitle("Cryspy Editor")
        self.init_user_interface()

        self.show()

        self.print_welcome()
        for message in self.l_startup_error:
            self.text_edit.append(f"ERROR: {message}")
        self.take_rcif_object_from_d_setup()
        self.print_object_info()
        self.assistant_controller.autoload_model()
        self.start_update_check()

    def write(self):
        out_terminal = getattr(self.cthread, "out_terminal", None)
        if out_terminal is None:
            return
        text = out_terminal.text_last
        text_permanent = "\n".join(out_terminal.l_text_permanent)
        self.text_edit.setText(text_permanent + "\n" + text)
        self.text_edit.upload_font_size()
        self.label_progress.setText(text.strip()[:120])

    def show_progress_text(self, text: str):
        if self.action_stop.isEnabled():  # keep "Stopping..." after Stop
            self.label_progress.setText(text)

    def user_scripts(self):
        options_window = OptionsWindow(self)
        options_window.show()

    def show_error(self, title: str, error: Exception):
        """Error of an external function in the output window, not in print."""
        self.text_edit.append(
            f"ERROR: {title}: {type(error).__name__}: {error}")

    def init_status_bar(self):
        """Progress of a running procedure and the button to stop it."""
        status_bar = self.statusBar()
        # A slim bar of one text line. QStatusBar takes its height from the
        # size hints of all its widgets, hidden ones too, so a native
        # QPushButton (tall bezel on macOS) made a thick empty bar.
        status_bar.setSizeGripEnabled(False)
        status_bar.setContentsMargins(4, 0, 4, 0)
        bar_height = status_bar.fontMetrics().height() + 6
        status_bar.setFixedHeight(bar_height)
        self.label_progress = QtWidgets.QLabel("", status_bar)
        self.progress_bar = QtWidgets.QProgressBar(status_bar)
        self.progress_bar.setRange(0, 0)  # busy indicator, length is unknown
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setFixedHeight(max(bar_height - 10, 6))
        self.progress_bar.setTextVisible(False)
        # A red button with a frame: the flat text button of #12 was easy
        # to miss in the corner of the window.
        self.button_stop = QtWidgets.QToolButton(status_bar)
        self.button_stop.setDefaultAction(self.action_stop)
        self.button_stop.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.button_stop.setFixedHeight(bar_height - 2)
        self.button_stop.setStyleSheet(
            "QToolButton {background-color: #c0392b; color: white;"
            " font-weight: bold; border: none; border-radius: 3px;"
            " padding: 0px 10px;}"
            "QToolButton:hover {background-color: #e74c3c;}"
            "QToolButton:disabled {background-color: #808080;}")
        status_bar.addPermanentWidget(self.label_progress, 1)
        status_bar.addPermanentWidget(self.progress_bar)
        status_bar.addPermanentWidget(self.button_stop)
        self.show_progress(False)

    def show_progress(self, flag: bool):
        self.label_progress.setVisible(flag)
        self.progress_bar.setVisible(flag)
        self.button_stop.setVisible(flag)
        self.action_stop.setEnabled(flag)
        if not flag:
            self.label_progress.setText("")

    def stop_calculations(self):
        if not self.cthread.isRunning():
            return
        self.cthread.request_stop()
        self.action_stop.setEnabled(False)
        self.label_progress.setText("Stopping...")

    def apply_cif_edits(self):
        """Apply the text typed in the RCIF tab to the object.

        The text is applied when the tab loses focus, but a menu action or a
        shortcut does not take the focus. Before, the text was applied on
        signal_start, i.e. after the calculation had already started in its
        thread, so the procedure sometimes used the old item.
        """
        w_item_tabs = getattr(self, "w_item_tabs", None)
        if w_item_tabs is None:
            return
        for ind in range(w_item_tabs.count()):
            widget = w_item_tabs.widget(ind)
            if isinstance(widget, WEditCif):
                widget.rewrite_item_by_printed_text()

    def run_calculations(self):  # d_info: dict = None
        thread = self.cthread
        self.text_edit.setText(
            "Calculations are running ... "
            f"(Stop: the red button or {STOP_SHORTCUT_TEXT})")
        self.text_edit.upload_font_size()
        if is_dark_mode():
            self.text_edit.setStyleSheet("background-color:#521F13;")
        else:
            self.text_edit.setStyleSheet("background-color:yellow;")

        self.cthread.out_terminal.signal_refresh.connect(self.write)
        self.show_progress(True)

    def end_calculations(self):  # output_data
        self.show_progress(False)
        if is_dark_mode():
            self.text_edit.setStyleSheet("background-color:black;")
        else:
            self.text_edit.setStyleSheet("background-color:white;")
        if not (self.cthread.out_terminal.out_terminal.closed):
            self.write()
            self.cthread.out_terminal.close()
        self.renew_w_object_panel()

    def init_user_interface(self):
        self.location_on_the_screen()
        dir_prog_icon = os.path.join(self.dir_prog, "f_icon")

        self.menu_bar = self.menuBar()
        toolbar_1 = self.addToolBar("Actions")

        # Menu file
        menu_file = self.menu_bar.addMenu("File")

        open_action = QAction(
            QtGui.QIcon(os.path.join(dir_prog_icon, "open.png")), "&Open", self
        )
        open_action.setShortcut("Ctrl+O")
        open_action.setStatusTip("Open file")
        open_action.triggered.connect(self.open_file)
        menu_file.addAction(open_action)
        toolbar_1.addAction(open_action)

        save_action = QtWidgets.QAction(
            QtGui.QIcon(os.path.join(dir_prog_icon, "save.png")), "&Save", self
        )
        save_action.setShortcut("Ctrl+S")
        save_action.setStatusTip("Save")
        save_action.triggered.connect(self.save_file)
        menu_file.addAction(save_action)
        toolbar_1.addAction(save_action)

        save_as_action = QtWidgets.QAction(
            QtGui.QIcon(os.path.join(dir_prog_icon, "save_as.png")),
            "Save &as...",
            self,
        )
        save_as_action.setStatusTip("Save as ...")
        save_as_action.triggered.connect(self.save_file_as)
        menu_file.addAction(save_as_action)
        toolbar_1.addAction(save_as_action)

        self.menu_recent = menu_file.addMenu("Open recent")
        self.update_menu_recent()

        self.menu_history = menu_file.addMenu("History")
        self.menu_history.setToolTipsVisible(True)
        self.menu_history.aboutToShow.connect(self.update_menu_history)

        exit_button = QAction(
            QIcon(os.path.join(dir_prog_icon, "exit24.png")), "Exit", self
        )
        exit_button.setShortcut("Ctrl+Q")
        exit_button.setStatusTip("Exit application")
        exit_button.triggered.connect(self.close)
        menu_file.addAction(exit_button)

        open_folder = QAction(
            QIcon(os.path.join(dir_prog_icon, "open_folder.png")),
            "Open folder",
            self,
        )
        open_folder.setStatusTip("Open folder")
        open_folder.triggered.connect(
            lambda: open_file_wm(self.d_setup["data_dir_name"])
        )
        toolbar_1.addAction(open_folder)

        refresh_view = QAction(
            QIcon(os.path.join(dir_prog_icon, "refresh.png")), "Refresh", self
        )
        refresh_view.setStatusTip("Refresh")
        refresh_view.triggered.connect(self.refresh_view)
        toolbar_1.addAction(refresh_view)

        # Stop of a running calculation: in the toolbar and in the status
        # bar, enabled only while it runs.
        self.action_stop = QAction(
            self.style().standardIcon(QtWidgets.QStyle.SP_BrowserStop),
            "Stop", self)
        self.action_stop.setShortcuts(
            [QtGui.QKeySequence(STOP_SHORTCUT),
             QtGui.QKeySequence(QtCore.Qt.Key_Escape)])
        self.action_stop.setToolTip(
            f"Stop the running calculation ({STOP_SHORTCUT_TEXT}). "
            "A refinement stops after the current iteration and keeps "
            "the refined parameters.")
        self.action_stop.setStatusTip("Stop the running calculation")
        self.action_stop.setEnabled(False)
        self.action_stop.triggered.connect(self.stop_calculations)
        toolbar_1.addSeparator()
        toolbar_1.addAction(self.action_stop)

        # Menu Options
        menu_options = self.menu_bar.addMenu("Options")
        manual_site = menu_options.addAction("Manual (site)")
        manual_site.triggered.connect(
            lambda x: open_file_wm(
                r"https://sites.google.com/view/cryspy/main"
            )
        )

        cryspy_help = menu_options.addAction("CrysPy help...")
        cryspy_help.setShortcut("F1")
        cryspy_help.triggered.connect(self.show_cryspy_help)

        add_user_scripts = menu_options.addAction("User scripts")
        add_user_scripts.triggered.connect(self.user_scripts)

        menu_options.addSeparator()
        self.action_check_updates = menu_options.addAction(
            "Check for new versions at startup")
        self.action_check_updates.setCheckable(True)
        self.action_check_updates.setChecked(
            bool(self.d_setup.get("check_for_updates", True)))
        self.action_check_updates.toggled.connect(
            self.set_check_for_updates)
        check_now = menu_options.addAction("Check for new version now")
        check_now.triggered.connect(
            lambda x: self.start_update_check(flag_manual=True))

        about = menu_options.addAction("About")
        about.triggered.connect(self.display_about)

        # Menu Parameters: refinement flags, values, favorites, constraints
        self.parameters_dialog = None
        menu_parameters = self.menu_bar.addMenu("Parameters")
        menu_parameters.setToolTipsVisible(True)
        act_parameters = menu_parameters.addAction("Parameters...")
        act_parameters.setShortcut("Ctrl+P")
        act_parameters.setToolTip(
            "All parameters with a filter: what to refine, values, favorites")
        act_parameters.triggered.connect(self.show_parameters)
        if is_constraint_supported():
            act_constraint = menu_parameters.addAction("Add constraint...")
            act_constraint.setToolTip(
                "Constraint between refined parameters, e.g. x + y = 1, "
                "exact or soft (within sigma)")
            act_constraint.triggered.connect(self.add_constraint)

        # Menu CrysPy
        self.init_menu_cryspy()

        # Menu AI assistant (optional local LLM, in a window of its own)
        self.assistant_controller = AssistantController(
            self, self.d_setup, save_settings, self.take_rcif_object,
            self.assistant_object_changed)
        self.assistant_controller.init_menu(self.menu_bar)

        self.init_central_widget()
        self.init_status_bar()

    def show_cryspy_help(self):
        from cryspy_editor.widgets.help_dialog import HelpDialog
        dialog = HelpDialog(self)
        dialog.show()

    def display_about(self):
        QtWidgets.QMessageBox.information(
            self,
            "About CrysPy",
            f"Versions:\n CrysPy Editor - {cryspy_editor_version:} \n CrysPy library - {cryspy_version:}",
        )

    def set_check_for_updates(self, flag: bool):
        self.d_setup["check_for_updates"] = bool(flag)
        save_settings()

    def start_update_check(self, flag_manual: bool = False):
        """Look for a newer release on GitHub in the background.

        At startup it is silent when there is nothing new or no internet;
        by the menu (flag_manual) it always reports the result."""
        if not flag_manual:
            if not self.d_setup.get("check_for_updates", True):
                return
            if update_check.is_check_disabled_by_environment():
                return
        checker = getattr(self, "update_checker", None)
        if checker is not None and not checker.is_done():
            return
        if flag_manual:
            function = update_check.fetch_latest_release
        else:
            function = update_check.check_for_update
        self.update_checker = update_check.UpdateChecker(
            cryspy_editor_version, function)
        self.update_checker_manual = flag_manual
        self.update_checker.start()
        self.timer_update_check = QtCore.QTimer(self)
        self.timer_update_check.timeout.connect(self.end_update_check)
        self.timer_update_check.start(300)

    def end_update_check(self):
        checker = self.update_checker
        if not checker.is_done():
            return
        self.timer_update_check.stop()
        d_release = checker.result
        if self.update_checker_manual:
            if d_release is None:
                QtWidgets.QMessageBox.warning(
                    self, "New version",
                    "GitHub cannot be reached. Check the internet "
                    "connection or open the download page:\n"
                    f"{update_check.URL_DOWNLOAD_PAGE}")
            elif update_check.is_newer(d_release["version"],
                                       cryspy_editor_version):
                self.show_new_version(d_release, flag_manual=True)
            else:
                QtWidgets.QMessageBox.information(
                    self, "New version",
                    f"CrysPy Editor {cryspy_editor_version} is the latest "
                    "version.")
            return
        if d_release is None:
            return
        if d_release["version"] == self.d_setup.get(
                "skipped_update_version", ""):
            return
        self.show_new_version(d_release)

    def show_new_version(self, d_release: dict, flag_manual: bool = False):
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle("New version of CrysPy Editor")
        box.setIcon(QtWidgets.QMessageBox.Information)
        box.setTextFormat(QtCore.Qt.RichText)
        box.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        box.setText(update_check.form_message(
            d_release, cryspy_editor_version))
        b_download = box.addButton(
            "Open download page", QtWidgets.QMessageBox.AcceptRole)
        b_skip = None
        if not flag_manual:
            b_skip = box.addButton(
                "Skip this version", QtWidgets.QMessageBox.RejectRole)
        box.addButton("Later", QtWidgets.QMessageBox.RejectRole)
        box.setDefaultButton(b_download)
        check_box = QtWidgets.QCheckBox(
            "Do not check for new versions at startup")
        check_box.setChecked(not self.d_setup.get("check_for_updates", True))
        box.setCheckBox(check_box)
        for label in box.findChildren(QtWidgets.QLabel):
            label.setOpenExternalLinks(True)
        box.exec_()
        if box.clickedButton() is b_download:
            QtGui.QDesktopServices.openUrl(
                QtCore.QUrl(update_check.URL_DOWNLOAD_PAGE))
        elif b_skip is not None and box.clickedButton() is b_skip:
            self.d_setup["skipped_update_version"] = d_release["version"]
        # the menu item follows the check box and saves the settings
        self.action_check_updates.setChecked(not check_box.isChecked())
        save_settings()

    def refresh_view(self):
        self.text_edit.setText("")
        self.print_welcome()
        self.w_item_tabs.item_way_in_w_item_tabs = None
        self.renew_w_object_panel()
        self.print_object_info()

    def print_welcome(self):
        ls_text = ["*************************"]
        ls_text.append("Welcome to CrysPy Editor.")
        ls_text.append("*************************")
        self.text_edit.setText("\n".join(ls_text))

    def print_object_info(self):
        """Refined parameters with the paths of the window Parameters."""
        try:
            l_record = [
                record for record in take_parameter_records(self.rcif_object)
                if is_number(record.value) and record.flag_refinement
                and not record.flag_constraint]
            ls_text = [f"\nNumber of variables is {len(l_record):}.\n"]
            if len(l_record) > 0:
                width = max(len(record.path) for record in l_record)
                ls_text.append(f"   {'NAME':{width}}      VALUE      ERROR")
            for record in l_record:
                ls_text.append(
                    f" - {record.path:{width}}  {float(record.value):9.5f}  "
                    f"{record.sigma:9.5f}")
            self.text_edit.append("\n".join(ls_text))
        except Exception as e:
            self.show_error("Variables of the object are not shown", e)

    def init_menu_cryspy(self):
        if not ("file_names_for_external_functions" in self.d_setup.keys()):
            self.d_setup["file_names_for_external_functions"] = ""
        l_f_name_external_not_checked = self.d_setup[
            "file_names_for_external_functions"
        ].split(";")
        l_f_name_external = [
            f_name
            for f_name in l_f_name_external_not_checked
            if os.path.isfile(f_name)
        ]
        self.d_setup["file_names_for_external_functions"] = ";".join(
            l_f_name_external
        )
        l_error = []
        l_func_external = get_external_functions(l_f_name_external, l_error)
        self.l_startup_error = l_error

        (
            self.functions_plot_data,
            self.functions_plot_loop,
            self.functions_plot_item,
        ) = get_plot_functions_for_data_loop_item(l_func_external)

        d_procedures = cryspy_procedures_to_dictionary(l_func_external)

        for key, functions in sorted(d_procedures.items()):
            menu_cryspy = self.menu_bar.addMenu(key)
            menu_cryspy.setToolTipsVisible(True)
            for func in functions:
                d_procedure = take_description(func)
                if d_procedure is not None:  # title and tooltip from the docstring
                    func_name = d_procedure["title"]
                    if func_name.lower().startswith(key.lower() + " "):
                        func_name = func_name[len(key) + 1:]
                    if is_autorun(d_procedure):
                        func_name += " (autorun)"
                    f_action = QtWidgets.QAction(func_name, menu_cryspy)
                    f_action.object = func
                    f_action.setToolTip(form_tooltip(d_procedure))
                    f_action.setStatusTip(d_procedure["summary"])
                    f_action.triggered.connect(
                        lambda: self.object_to_procedure(self.press_procedure)
                    )
                    menu_cryspy.addAction(f_action)
                    continue
                if key.lower().startswith(func.__name__.split("_")[0].lower()):
                    func_name = (
                        " ".join(func.__name__.split("_")[1:])
                        .lower()
                        .strip()
                        .title()
                    )
                else:
                    func_name = (
                        func.__name__.replace("_", " ").lower().strip().title()
                    )
                if check_function_to_auto_run(func):
                    func_name += " (autorun)"
                f_action = QtWidgets.QAction(func_name, menu_cryspy)
                f_action.object = func
                if func.__doc__ is not None:
                    f_action.setToolTip(func.__doc__)
                    f_action.setStatusTip(func.__doc__.strip().split("\n")[0])
                f_action.triggered.connect(
                    lambda: self.object_to_procedure(self.press_procedure)
                )
                menu_cryspy.addAction(f_action)

    def object_to_procedure(self, procedure):
        f_action = self.sender()
        func_to_do = f_action.object
        procedure(func_to_do)

    # procedures which is sended to  local classes to have connection with whole object
    def press_procedure(self, procedure):
        """Run procedure to performe procedure."""
        d_procedure = take_description(procedure)
        if d_procedure is not None:
            self.run_described_procedure(procedure, d_procedure)
            return
        if check_function_to_auto_run(procedure):
            self.cthread.function = procedure
            self.cthread.arguments = (self.rcif_object,)
            self.cthread.start()
        else:
            self.w_function.set_function(
                procedure, self.cthread, globaln=self.rcif_object
            )

    def run_described_procedure(self, procedure, d_procedure: dict):
        """Run a procedure described by CrysPy: at once when it needs only
        the object, otherwise after the form of its parameters."""
        if self.cthread.isRunning():
            return
        self.apply_cif_edits()  # the items of the form are taken from the current object
        if is_autorun(d_procedure):
            arguments = (self.rcif_object,)
        else:
            dialog = ProcedureDialog(procedure, d_procedure, self.rcif_object, self)
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                return
            arguments = dialog.arguments()
        self.cthread.function = procedure
        self.cthread.arguments = arguments
        self.cthread.start()

    def location_on_the_screen(self):
        """Location on the screen."""
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        self.setMinimumSize(
            int(screen.width() * 1 / 4), int(screen.height() * 1 / 4)
        )
        self.info_width = int(screen.width() * 8.0 / 10.0)
        self.info_height = int(screen.height() * 14.0 / 16.0)
        self.move(int(screen.width() / 10), int(screen.height() / 20))
        self.resize(
            int(screen.width() * 8.0 / 10.0),
            int(screen.height() * 14.0 / 16.0),
        )

    def save_file(self):
        self.apply_cif_edits()  # Ctrl+S does not take the focus
        file_name = self.d_setup.get("data_file_name", "")
        if file_name == "" or os.path.isdir(file_name):
            self.save_file_as()
            return
        try:
            with open(file_name, "w") as fid:
                fid.write(self.rcif_object.to_cif())
        except OSError as error:
            QtWidgets.QMessageBox.warning(
                self, "Save", f"File '{file_name}' is not saved:\n{error}")
            return
        add_recent_file(file_name)
        self.update_menu_recent()
        save_settings()

    def save_file_as(self):
        f_dir = self.d_setup.get("data_dir_name", "")
        if not os.path.isdir(f_dir):
            f_dir = os.path.expanduser("~")
        file_name, ok = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save file as ...",
            f_dir,
            "RCIF Files (*.rcif);; CIF Files (*.cif);; All Files (*)",
        )
        if ok and file_name != "":
            self.d_setup["data_file_name"] = file_name
            self.d_setup["data_dir_name"] = os.path.dirname(file_name)
            self.cthread.work_dir = os.path.dirname(file_name)
            self.setWindowTitle(
                f"CrysPy Editor: {os.path.basename(file_name):}")
            self.save_file()

    def open_file(self):
        f_dir = self.d_setup.get("data_dir_name", "")
        if not os.path.isdir(f_dir):
            f_dir = os.path.expanduser("~")
        file_name, ok = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open file",
            f_dir,
            "RCIF Files (*.rcif);; CIF Files (*.cif);; All Files (*)",
        )
        if ok and file_name != "":
            self.open_file_name(file_name)

    def open_file_name(self, file_name: str):
        """Open the file given by name (dialog, recent files, command line)."""
        self.d_setup["data_file_name"] = os.path.abspath(file_name)
        self.take_rcif_object_from_d_setup()
        self.print_object_info()

    def update_menu_recent(self):
        self.menu_recent.clear()
        l_recent = [file_name for file_name in self.d_setup["recent_files"]
                    if os.path.isfile(file_name)]
        for file_name in l_recent:
            action = self.menu_recent.addAction(file_name)
            action.triggered.connect(
                lambda checked, f_name=file_name: self.open_file_name(f_name))
        self.menu_recent.setEnabled(len(l_recent) > 0)

    def take_rcif_object_from_d_setup(self):
        """Load object from d_setup."""
        file_name = self.d_setup.get("data_file_name", "")
        if os.path.isfile(file_name):
            self.text_edit.append(
                f"Loading data from file '{os.path.basename(file_name)}'...")
            try:
                rcif_object = load_file(file_name)
            except Exception as e:
                ls_out = [80 * "*", "ERROR during data opening", str(e),
                          80 * "*"]
                self.text_edit.append("\n".join(ls_out))
                if not hasattr(self, "rcif_object"):
                    self.rcif_object = GlobalN.make_container((), (), "global")
                    self.renew_w_object_panel()
                return
            self.d_setup["data_dir_name"] = os.path.dirname(file_name)
            # procedures write output files (.den, sections) next to the data
            self.cthread.work_dir = os.path.dirname(file_name)
            self.setWindowTitle(
                f"CrysPy Editor: {os.path.basename(file_name):}"
            )
            add_recent_file(file_name)
            self.update_menu_recent()
            save_settings()
        else:
            if file_name != "":
                self.text_edit.append(f"File '{file_name}' is not found.")
            rcif_object = GlobalN.make_container((), (), "global")
        self.rcif_object = rcif_object
        self.history.clear()  # states of another file are not mixed in
        self.renew_w_object_panel()

    def renew_w_object_panel(self):
        """Renew object_presentation."""
        rcif_object = self.rcif_object
        dict_tree = form_dict_tree_for_rcif_object(rcif_object)
        self.w_object_panel.set_dict_tree(dict_tree)

        way_item = self.w_item_tabs.item_way_in_w_item_tabs
        self.renew_w_item_tabs(way_item)
        parameters_dialog = getattr(self, "parameters_dialog", None)
        if parameters_dialog is not None and parameters_dialog.isVisible():
            parameters_dialog.refresh()

    def renew_w_item_tabs(self, way_item):
        # print("id(self.rcif_object): ", id(self.rcif_object))
        # print("id(item): ", [id(loop_item) for loop_item in item.items], id(item))
        # print("way_item: ", way_item)
        try:
            w_item_tabs = self.w_item_tabs
            w_item_tabs.item_way_in_w_item_tabs = way_item

            tab_text = ""
            if w_item_tabs.count() != 0:
                tab_text = str(w_item_tabs.tabText(w_item_tabs.currentIndex()))

            for ind_item in range(w_item_tabs.count() - 1, -1, -1):
                w_item_tabs.removeTab(ind_item)
            plt.close()
            plt.close()

            if way_item is not None:
                item = take_item(self.rcif_object, way_item)
                if item is None:
                    item = self.rcif_object
            else:
                item = self.rcif_object
        except Exception as e:
            self.show_error(f"Item {way_item} is not found", e)
            return
        # RCIF tab
        if isinstance(item, (LoopN, ItemN)) and not (
            isinstance(item, (Pd2dMeas, Pd2dProc, ChannelAni, ChannelCol))
        ):
            l_hh = []
            s_info = ""
            if isinstance(item, ItemN):
                s_item = item.to_cif(separator="_", flag_all_attributes=True)
                try:
                    prefix = item.PREFIX
                    l_hh = [f"_{prefix:}_{hh:}" for hh in item.ATTR_CIF]
                    s_info = item.__doc__
                except AttributeError:  # ItemN without PREFIX
                    pass
            else:
                s_item = str(item)
                try:
                    item_class = item.ITEM_CLASS
                    if item_class == ItemN:
                        l_hh = []
                    else:
                        prefix = item_class.PREFIX
                        l_hh = [
                            "loop_",
                        ] + [f"_{prefix:}_{hh:}" for hh in item_class.ATTR_CIF]
                    s_info = item.__doc__
                except AttributeError:  # LoopN without ITEM_CLASS
                    pass
            text_placeholder = "\n".join(l_hh)

            w_edit_cif = WEditCif(
                s_item,
                self.rewrite_item_in_edit_cif,
                parent=w_item_tabs,
                text_placeholder=text_placeholder,
                s_info=s_info,
                value_choices=take_value_choices(item),
            )
            # w_edit_cif.setToolTip(item.__doc__)
            w_item_tabs.addTab(w_edit_cif, "RCIF format")

        # if isinstance(object_, LoopN):
        #     w_loop_items = WLoopItems(None, self.thread, self)
        #     w_loop_items.set_object(object_)
        #     self.addTab(w_loop_items, "Items")

        # Figure tab
        try:
            l_fig_ax = [
                fig_ax for fig_ax in item.plots() if fig_ax is not None
            ]
        except Exception as e:
            l_fig_ax = []
            self.show_error(f"Plots of '{item.get_name()}' are not made", e)

        for fig, ax in l_fig_ax:
            widget = QtWidgets.QWidget(w_item_tabs)
            layout = QtWidgets.QVBoxLayout()
            item_plot = Graph(fig, parent=widget)
            toolbar = item_plot.get_toolbar(parent=widget)
            layout.addWidget(toolbar)
            layout.addWidget(item_plot)
            widget.setLayout(layout)
            if isinstance(ax, tuple):
                s_text = f"Fig: {ax[0].title.get_text():}"
            else:
                s_text = f"Fig: {ax.title.get_text():}"
            if len(s_text) > 20:
                s_text = s_text[:20] + "..."
            w_item_tabs.addTab(widget, s_text)
            # self.insertTab(0, widget, s_text)
        if len(l_fig_ax) == 0:
            fig = None
            if isinstance(item, DataN):
                for func in self.functions_plot_data:
                    fig = func(item)
                    if fig is not None:
                        break

            if isinstance(item, LoopN):
                for func in self.functions_plot_loop:
                    fig = func(item)
                    if fig is not None:
                        break

            if isinstance(item, ItemN):
                for func in self.functions_plot_item:
                    fig = func(item)
                    if fig is not None:
                        break
            if fig is not None:
                widget = QtWidgets.QWidget(w_item_tabs)
                layout = QtWidgets.QVBoxLayout()
                item_plot = Graph(fig, parent=widget)
                toolbar = item_plot.get_toolbar(parent=widget)
                layout.addWidget(toolbar)
                layout.addWidget(item_plot)
                widget.setLayout(layout)
                if len(fig.axes) != 0:
                    s_text = f"Fig: {fig.axes[0].title.get_text():}"
                if len(s_text) > 20:
                    s_text = s_text[:20] + "..."
                w_item_tabs.addTab(widget, s_text)

        # 3D view tab (crystal structure)
        if has_structure_view(item):
            w_item_tabs.addTab(WStructureView(item, parent=w_item_tabs), "3D view")

        # Report tab
        try:
            report_html = item.report_html()
        except Exception as e:
            report_html = ""
            self.show_error(f"Report of '{item.get_name()}' is not made", e)

        if report_html != "":
            # wide tables (correlation matrix of many parameters) scroll
            # instead of being cut or widening the window
            w_scroll = QtWidgets.QScrollArea(w_item_tabs)
            w_scroll.setWidgetResizable(True)
            w_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
            w_plain_text = QtWidgets.QLabel(w_scroll)
            w_plain_text.setText(report_html)
            w_plain_text.setSizePolicy(
                QtWidgets.QSizePolicy(
                    QtWidgets.QSizePolicy.Expanding,
                    QtWidgets.QSizePolicy.Expanding,
                )
            )
            w_plain_text.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
            w_plain_text.setWordWrap(True)
            w_plain_text.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse
            )
            w_scroll.setWidget(w_plain_text)
            w_item_tabs.addTab(w_scroll, "View")

        if w_item_tabs.count() == 0:
            q_label = QtWidgets.QLabel(
                f"No graphs or other information for '{item.get_name():}'."
            )
            # f"{item.__doc__:}")
            q_label.setSizePolicy(
                QtWidgets.QSizePolicy(
                    QtWidgets.QSizePolicy.Expanding,
                    QtWidgets.QSizePolicy.Expanding,
                )
            )
            w_item_tabs.addTab(q_label, "")

        # if tab_text == "Notes":
        #     self.setCurrentIndex(0)
        # else:
        #     flag_first = True
        flag_first = True
        for ind_tab in range(w_item_tabs.count()):
            if tab_text == str(w_item_tabs.tabText(ind_tab)):
                w_item_tabs.setCurrentIndex(ind_tab)
                flag_first = False
                break
        if flag_first:
            w_item_tabs.setCurrentIndex(0)

    def init_central_widget(self):
        widget_main = QtWidgets.QWidget(self)
        layout_main = QtWidgets.QVBoxLayout()

        # First
        self.w_function = WFunction(widget_main)
        layout_main.addWidget(self.w_function)

        # Second
        w_splitter = QtWidgets.QSplitter(widget_main)

        # Panel from left site
        self.w_object_panel = WObjectPanel(
            self.item_clicked_on_w_object_panel,
            self.display_item_menu,
            self.item_to_rcif,
            parent=w_splitter,
        )
        w_splitter.addWidget(self.w_object_panel)

        self.w_item_tabs = QtWidgets.QTabWidget(w_splitter)
        self.w_item_tabs.item_way_in_w_item_tabs = None
        w_splitter.addWidget(self.w_item_tabs)

        self.text_edit = WTextEdit(w_splitter)  # QtWidgets.QTextEdit
        # self.text_edit.setLineWrapMode(QtWidgets.QTextEdit.FixedPixelWidth)
        # self.text_edit.setFont(QtGui.QFont("Courier", 8, QtGui.QFont.Normal))
        # self.text_edit.setLineWrapColumnOrWidth(648)
        self.text_edit.rewrite_undo_last_line = False

        w_splitter.addWidget(self.text_edit)

        width_m_1 = int(1 * self.info_width / 6.0)
        width_m_2 = int(3 * self.info_width / 6.0)
        width_m_3 = int(self.info_width - (width_m_1 + width_m_2))
        w_splitter.setSizes([width_m_1, width_m_2, width_m_3])

        layout_main.addWidget(w_splitter)
        widget_main.setLayout(layout_main)
        self.setCentralWidget(widget_main)

    def take_rcif_object(self):
        self.apply_cif_edits()
        self.remember("AI assistant request")
        return getattr(self, "rcif_object", None)

    def remember(self, label: str):
        """Keep the state of the object before the change `label`."""
        rcif_object = getattr(self, "rcif_object", None)
        if rcif_object is None:
            return
        try:
            self.history.push(label, rcif_object.to_cif())
        except Exception as e:
            self.show_error("The state is not kept in History", e)

    def remember_before_run(self):
        func = self.cthread.function
        name = getattr(func, "__name__", "procedure")
        self.remember(name.replace("_", " "))

    def update_menu_history(self):
        menu = self.menu_history
        menu.clear()
        if len(self.history) == 0:
            action = menu.addAction("No changes yet")
            action.setEnabled(False)
            return
        flag_free = not self.cthread.isRunning()
        for entry in reversed(self.history.entries):
            action = menu.addAction(entry.title())
            action.setToolTip("Go back to the object as it was at that time")
            action.setEnabled(flag_free)
            action.triggered.connect(
                lambda checked=False, entry=entry: self.restore_history(entry))

    def restore_history(self, entry):
        """Go back to a kept state; the current one is kept too, so that
        going back can itself be undone."""
        if self.cthread.isRunning():
            return
        try:
            rcif_object = str_to_globaln(entry.text)
        except Exception as e:
            self.show_error("The state is not restored", e)
            return
        self.apply_cif_edits()
        self.remember(f"going back to {entry.title().split()[0]}")
        self.rcif_object = rcif_object
        self.w_item_tabs.item_way_in_w_item_tabs = None
        self.renew_w_object_panel()
        self.text_edit.setText(
            f"The object is as it was {entry.title()}.\n"
            "Save the file to keep it.")
        self.print_object_info()

    def assistant_object_changed(self):
        self.renew_w_object_panel()
        self.print_object_info()

    def closeEvent(self, event):
        self.assistant_controller.save_window_state()
        save_settings()
        self.assistant_controller.shutdown()
        super().closeEvent(event)

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def item_clicked_on_w_object_panel(self, *argv):
        rcif_object = self.rcif_object
        tree_widget_item = argv[0]
        way_item = form_way(tree_widget_item)
        if way_item is not None:
            item = take_item(rcif_object, way_item)
            self.renew_w_item_tabs(way_item)
        else:
            self.renew_w_object_panel()

    def rewrite_item_in_edit_cif(self, text: str):
        rcif_object = self.rcif_object
        way_item = self.w_item_tabs.item_way_in_w_item_tabs
        if way_item is not None:
            item = take_item(rcif_object, way_item)
            try:
                item_2 = item.from_cif(text)
                if item_2 is not None:
                    self.remember(f"edit of {way_item[-1]}")
                    item.copy_from(item_2)
            except Exception as e:
                ls_out = ["Item defined incorrectly: "]
                ls_out.append(str(e))
                self.text_edit.append("\n".join(ls_out))
        else:
            self.renew_w_object_panel()

    @QtCore.pyqtSlot(
        QtCore.QPoint,
    )
    def display_item_menu(self, *argv):
        w_object_panel = self.sender()
        position = argv[0]
        tree_widget_item = w_object_panel.itemAt(position)

        if tree_widget_item is None:
            way_item = ()
            item = self.rcif_object
        else:
            way_item = form_way(tree_widget_item)

            rcif_object = self.rcif_object
            item = take_item(rcif_object, way_item)
            if item is None:
                item = self.rcif_object

        menu = QtWidgets.QMenu(w_object_panel)
        menu.setToolTipsVisible(True)

        if (type(item) is GlobalN) | (type(item) is DataN):

            if type(item) is GlobalN:
                menu_data = menu.addMenu("Add data block")
                menu_data.setToolTipsVisible(True)

                for cls_item in L_DATA_CLS:
                    prefix = cls_item.PREFIX
                    add_item = QtWidgets.QAction(f"{prefix :}", menu_data)
                    add_item.cls_item = cls_item
                    add_item.way_item = way_item
                    add_item.setToolTip(cls_item.__doc__)
                    add_item.triggered.connect(self.add_item)
                    menu_data.addAction(add_item)

            menu_loop = menu.addMenu("Add loop block")
            menu_loop.setToolTipsVisible(True)
            for cls_item in L_LOOP_CLS:
                prefix = cls_item.ITEM_CLASS.PREFIX
                add_item = QtWidgets.QAction(f"{prefix :}", menu_loop)
                add_item.cls_item = cls_item
                add_item.way_item = way_item
                add_item.setToolTip(cls_item.__doc__)
                add_item.triggered.connect(self.add_item)
                menu_loop.addAction(add_item)

            menu_item = menu.addMenu("Add item")
            menu_item.setToolTipsVisible(True)
            for cls_item in L_ITEM_CLS:
                prefix = cls_item.PREFIX
                add_item = QtWidgets.QAction(f"{prefix :}", menu_item)
                add_item.cls_item = cls_item
                add_item.way_item = way_item
                add_item.setToolTip(cls_item.__doc__)
                add_item.triggered.connect(self.add_item)
                menu_item.addAction(add_item)

        elif isinstance(item, (GlobalN, DataN)):
            menu_item = menu.addMenu("Add")
            menu_item.setToolTipsVisible(True)
            for cls_item in item.CLASSES_MANDATORY:
                if (
                    (cls_item is not DataN)
                    & (cls_item is not LoopN)
                    & (cls_item is not ItemN)
                ):
                    if "PREFIX" in cls_item.__dict__.keys():
                        prefix = cls_item.PREFIX
                    else:
                        prefix = cls_item.ITEM_CLASS.PREFIX
                    add_item = QtWidgets.QAction(f"{prefix:}", menu_item)
                    add_item.cls_item = cls_item
                    add_item.way_item = way_item
                    add_item.setToolTip(cls_item.__doc__)
                    add_item.triggered.connect(self.add_item)
                    menu_item.addAction(add_item)
            menu_item.addSeparator()
            for cls_item in item.CLASSES_OPTIONAL:
                if (
                    (cls_item is not DataN)
                    & (cls_item is not LoopN)
                    & (cls_item is not ItemN)
                ):
                    if "PREFIX" in cls_item.__dict__.keys():
                        prefix = cls_item.PREFIX
                    else:
                        prefix = cls_item.ITEM_CLASS.PREFIX
                    add_item = QtWidgets.QAction(f"{prefix :}", menu_item)
                    add_item.cls_item = cls_item
                    add_item.way_item = way_item
                    add_item.setToolTip(cls_item.__doc__)
                    add_item.triggered.connect(self.add_item)
                    menu_item.addAction(add_item)

        if isinstance(item, GlobalN) and is_constraint_supported():
            act_constraint = QtWidgets.QAction("Add constraint...", menu)
            act_constraint.setToolTip(
                "Constraint between refined parameters, e.g. x + y = 1, "
                "exact or soft (within sigma)")
            act_constraint.triggered.connect(self.add_constraint)
            menu.addAction(act_constraint)

        if isinstance(item, (GlobalN, DataN, LoopN)):
            act_rename = QtWidgets.QAction("Rename", menu)
            act_rename.way_item = way_item
            act_rename.triggered.connect(self.do_function)
            menu.addAction(act_rename)

        if isinstance(item, (DataN, LoopN, ItemN)):
            del_item = QtWidgets.QAction("Delete", menu)
            del_item.way_item = way_item
            del_item.triggered.connect(self.do_function)
            menu.addAction(del_item)

        if isinstance(item, (GlobalN, DataN, LoopN, ItemN)):
            act_copy_to_clipboard = QtWidgets.QAction(
                "Copy to clipboard", menu
            )
            act_copy_to_clipboard.way_item = way_item
            act_copy_to_clipboard.triggered.connect(self.do_function)
            menu.addAction(act_copy_to_clipboard)

            act_paste_from_clipboard = QtWidgets.QAction(
                "Paste from clipboard", menu
            )
            act_paste_from_clipboard.way_item = way_item
            act_paste_from_clipboard.triggered.connect(self.do_function)
            menu.addAction(act_paste_from_clipboard)

        method_names = [
            _1
            for _1, _2 in type(item).__dict__.items()
            if ((type(_2) == FunctionType) & (not (_1.startswith("_"))))
        ]

        if len(method_names) != 0:
            menu_methods = menu.addMenu("Methods")
            for name in method_names:
                func = getattr(item, name)
                l_param = [
                    _
                    for _ in func.__code__.co_varnames[
                        : func.__code__.co_argcount
                    ]
                    if _ != "self"
                ]
                s_par = ""
                if len(l_param) > 0:
                    s_par = ", ".join(l_param)
                s_val = f"{name:}({s_par:})"
                action_method = QtWidgets.QAction(s_val, menu_methods)
                action_method.way_item = way_item
                action_method.triggered.connect(self.do_function)
                menu_methods.addAction(action_method)

        if isinstance(item, (LoopN, ItemN)):
            qaction = QtWidgets.QAction("Refine all variables", menu)
            qaction.way_item = way_item
            qaction.triggered.connect(self.do_function)
            menu.addAction(qaction)
        qaction = QtWidgets.QAction("Fix all variables", menu)
        qaction.way_item = way_item
        qaction.triggered.connect(self.do_function)
        menu.addAction(qaction)

        act_info = QtWidgets.QAction("Info", menu)
        act_info.way_item = way_item
        act_info.triggered.connect(self.do_function)
        menu.addAction(act_info)

        menu.exec_(w_object_panel.viewport().mapToGlobal(position))

    @QtCore.pyqtSlot(
        bool,
    )
    def do_function(self, *argv):
        sender = self.sender()
        name = sender.text()
        flag_do = True
        if name == "Refine all variables":
            name = "refine_all_variables"
        elif name == "Fix all variables":
            name = "fix_variables"
        elif name == "Info":
            flag_do = False
        elif name in [
            "Delete",
            "Rename",
            "Copy to clipboard",
            "Paste from clipboard",
        ]:
            flag_do = False

        if flag_do:
            func_name = name.split("(")[0]
            way_item = sender.way_item
            if way_item == ():
                item = self.rcif_object
            else:
                item = take_item(self.rcif_object, way_item)
            if item is not None:
                func = getattr(item, func_name)
                self.w_function.set_function(func, self.cthread)
        else:
            if name == "Delete":
                way_item = sender.way_item
                if len(way_item) > 0:
                    item = take_item(self.rcif_object, way_item)
                    way_parent_item = way_item[:-1]
                    if way_parent_item == ():
                        parent_item = self.rcif_object
                    else:
                        parent_item = take_item(
                            self.rcif_object, way_parent_item
                        )
                    if (parent_item is not None) and (item is not None):
                        if "items" in dir(parent_item):
                            if item in parent_item.items:
                                parent_item.items.remove(item)
                                self.renew_w_object_panel()
            elif name == "Rename":
                way_item = sender.way_item
                if way_item == ():
                    item = self.rcif_object
                else:
                    item = take_item(self.rcif_object, way_item)

                if item is not None:
                    text, ok = QtWidgets.QInputDialog.getText(
                        self,
                        f"Input dialog {item.get_name():}",
                        "Enter the new name",
                    )
                    if ok:
                        new_name = "".join(text.split())
                        if isinstance(item, GlobalN):
                            item.global_name = new_name
                        elif isinstance(item, DataN):
                            item.data_name = new_name
                        elif isinstance(item, LoopN):
                            item.loop_name = new_name
                        self.renew_w_object_panel()
            elif name == "Info":
                way_item = sender.way_item
                if way_item == ():
                    item = self.rcif_object
                else:
                    item = take_item(self.rcif_object, way_item)
                if item is not None:
                    info_text = (
                        type(item).__doc__
                        or "No documentation available for this item class."
                    )
                    self.text_edit.setText(info_text)
            elif name == "Copy to clipboard":
                way_item = sender.way_item
                if way_item == ():
                    item = self.rcif_object
                else:
                    item = take_item(self.rcif_object, way_item)
                if not item is None:
                    s_text = item.to_cif()

                    cb = QtWidgets.QApplication.clipboard()
                    cb.clear(mode=cb.Clipboard)
                    cb.setText(s_text, mode=cb.Clipboard)
            elif name == "Paste from clipboard":
                way_item = sender.way_item
                if way_item == ():
                    item = self.rcif_object
                else:
                    item = take_item(self.rcif_object, way_item)
                if not item is None:
                    cb = QtWidgets.QApplication.clipboard()
                    s_text = cb.text()
                    globaln = str_to_globaln(s_text)
                    self.rcif_object.add_items(globaln.items)
                    self.renew_w_object_panel()

    def item_to_rcif(self, tree_widget_item: QtWidgets.QTreeWidgetItem):
        rcif_object = self.rcif_object
        if tree_widget_item is None:
            return ""
        way_item = form_way(tree_widget_item)
        item = take_item(rcif_object, way_item)
        return item.to_cif()

    @QtCore.pyqtSlot(
        bool,
    )
    def add_constraint(self, *argv):
        """Dialog of a constraint between refined parameters."""
        rcif_object = self.rcif_object
        if not isinstance(rcif_object, GlobalN):
            return
        try:
            text_before = rcif_object.to_cif()
        except Exception:
            text_before = None
        dialog = ConstraintDialog(rcif_object, self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        if text_before is not None:
            self.history.push("add constraint", text_before)
        self.renew_w_object_panel()
        self.text_edit.append(
            f"Constraint added: {dialog.added_constraint.expression:}")

    def show_parameters(self, *argv):
        """Window of all parameters; it stays open next to the main window."""
        self.apply_cif_edits()
        if self.parameters_dialog is None:
            self.parameters_dialog = ParametersDialog(
                lambda: getattr(self, "rcif_object", None), self.d_setup, save_settings,
                self.parameters_changed, self)
        else:
            self.parameters_dialog.refresh()
        self.parameters_dialog.show()
        self.parameters_dialog.raise_()
        self.parameters_dialog.activateWindow()

    def parameters_changed(self, label: str, text_before):
        """A change made in the window Parameters."""
        if text_before is not None:
            self.history.push(label, text_before)
        self.renew_w_object_panel()

    def add_item(self, *argv) -> NoReturn:
        """Add object."""
        sender = self.sender()
        way_item = sender.way_item
        if way_item == ():
            item = self.rcif_object
        else:
            item = take_item(self.rcif_object, way_item)
        if item is not None:
            new_item = sender.cls_item()
            if isinstance(new_item, DataN):
                s_name = "".join(
                    random.choices(string.ascii_letters, k=4)
                ).lower()
                new_item.data_name = s_name
            if (type(item) is DataN) | (type(item) is GlobalN):
                item_cls = set([type(item) for item in item.items])
                if type(new_item) not in item_cls:
                    item.CLASSES_OPTIONAL = tuple(
                        list(item.CLASSES_OPTIONAL) + [type(new_item)]
                    )
                    item.CLASSES = tuple(list(item.CLASSES) + [type(new_item)])
            item.add_items([new_item])
            self.renew_w_object_panel()

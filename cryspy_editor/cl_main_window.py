# -*- coding: utf-8 -*-
__author__ = 'ikibalin'
__version__ = "2020_08_21"
# import logging

import os
import os.path
import sys

from typing import NoReturn

import traceback

from PyQt5 import QtCore, QtGui, QtWidgets, Qt



class OutputLogger(QtCore.QObject):
    emit_write = QtCore.pyqtSignal(str, int)

    class Severity:
        DEBUG = 0
        ERROR = 1

    def __init__(self, io_stream, severity):
        super().__init__()

        self.io_stream = io_stream
        self.severity = severity

    def write(self, text):
        self.io_stream.write(text)
        self.emit_write.emit(text, self.severity)

    def flush(self):
        self.io_stream.flush()


OUTPUT_LOGGER_STDOUT = OutputLogger(sys.stdout, OutputLogger.Severity.DEBUG)
OUTPUT_LOGGER_STDERR = OutputLogger(sys.stderr, OutputLogger.Severity.ERROR)

sys.stdout = OUTPUT_LOGGER_STDOUT
sys.stderr = OUTPUT_LOGGER_STDERR



from cryspy import GlobalN, load_file
from cryspy_editor.procedures_d_setup import save_d_setup, load_d_setup

from cryspy_editor.widgets.w_item_tabs import WItemTabs
# from cryspy_editor.widgets.w_output import WOutput
from cryspy_editor.widgets.w_function import WFunction
# from cryspy_editor.widgets.w_variables import WVariables
from cryspy_editor.widgets.w_object_panel import WObjectPanel


from cryspy_editor.widgets.cryspy_objects import cryspy_procedures_to_dictionary, check_function_to_auto_run
from cryspy_editor.cl_thread import CThread
# from cryspy_editor.cl_calc_window import CCalcWindow
from cryspy_editor.widgets.w_packages import WPackages

# from cryspy_editor.w_about import w_about
# from cryspy_editor.widgets.w_panel import WPanel, \
#     find_tree_item_position, L_GLOBAL_CLS

from cryspy_editor.widgets.w_presentation import define_tool_buttons
# from cryspy_editor.widgets.at_procedures import form_actions, form_toolbar


class CMainWindow(QtWidgets.QMainWindow):
    """
    Main Window class.

    Attributes
    ----------
        - toolbar
        - menu
        - w_function
        - w_object_panel
        - w_item_toolbar (deleted)
        - w_item_tabs
        - w_output
        - w_variables

        - object
        - cthread
        - calc_window
        - dir_program
        - dir_data
        - file_data
        - file_setup
        - d_setup

    """
    def __init__(self):
        super(CMainWindow, self).__init__()

        OUTPUT_LOGGER_STDOUT.emit_write.connect(self.append_log)
        OUTPUT_LOGGER_STDERR.emit_write.connect(self.append_log)

        self.dir_prog = os.path.dirname(__file__)
        self.location_on_the_screen()

        # Thread block        
        self.cthread = CThread(self)
        self.cthread.signal_start.connect(self.run_calculations)
        self.cthread.signal_end.connect(self.end_calculations)

        # # Window CCalcWindow
        # self.cthread.calc_window = CCalcWindow(self)
        # screen = QtWidgets.QDesktopWidget().screenGeometry()
        # self.cthread.calc_window.resize(screen.width() * 0.5,
        #                             screen.height() * 0.2)
        f_calc = os.path.join(self.dir_prog, "f_icon", "pm.gif")
        # q_label = QtWidgets.QLabel()
        # gif = QtGui.QMovie(f_calc)
        # q_label.setMovie(gif)
        # gif.start()
        # self.cthread.calc_window.layout.addWidget(q_label)

        self.setWindowTitle('CrysPy editor')

        self.create_graphic_elements()
        self.create_cryspy_actions()
        self.file_setup = os.path.join(os.path.dirname(__file__), 'setup.json')
        self.d_setup = load_d_setup(self.file_setup)

        self.take_object_from_d_setup()
        

    def print_welcome(self):
        print("*************************")
        print("Welcome to CrysPy Editor.")
        print("*************************")

    def print_help(self):
        print("GUI")
        print("---")
        print("GUI is separated on three blocks:")
        print(" - Three widget of input '.rcif' file")
        print(" - Block with figures and tabs.")
        print(" - Output window.")
        print("Basic actions")
        print("-------------")
        print(" - to open file click File/Open")
        print(" - to run Rietveld refinement click RhoChi/Rietveld refinement")
        print(" - to run MEM (for single crystals) click MEMPy/Spin density reconstruction")
        print(" - to interact with data/loop/item blocks click right mouse button over it in the threeview")

    def append_log(self, text, severity):
        # text = repr(text)

        if severity == OutputLogger.Severity.ERROR:
            text = '<b>{}</b>'.format(text)
        else:
            if text.endswith("\r"):
                self.text_edit.rewrite_undo_last_line = True
            elif text == "\n":
                pass
            else:
                if self.text_edit.rewrite_undo_last_line:
                    self.text_edit.undo()
                    self.text_edit.rewrite_undo_last_line = False
                self.text_edit.append(text.rstrip())


    def run_calculations(self):# d_info: dict = None
        thread = self.cthread
        self.text_edit.setText("Calculations are running ...")
        self.text_edit.setStyleSheet("background-color:yellow;")
        pass

    def end_calculations(self): #output_data
        self.text_edit.setStyleSheet("background-color:white;")
        self.renew_object_presentation()

    def location_on_the_screen(self) -> NoReturn:
        """Location on the screen."""
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        self.setMinimumSize(int(screen.width() * 1 / 4), int(screen.height() * 1 / 4))
        self.info_width = int(screen.width() * 8. / 10.)
        self.info_height = int(screen.height() * 14. / 16.)
        self.move(int(screen.width() / 10), int(screen.height() / 20))
        self.resize(int(screen.width() * 8. / 10.), int(screen.height() * 14. / 16.))
        return 

    def create_graphic_elements(self):
        """
        - menubar
        - toolbar_1
        - w_function
        - w_object_panel
        - w_output
        - w_variables
        - w_item_tabs
        - w_item_toolbar (deleted)

        """
        self.menubar = self.menuBar()
        self.toolbar_1 = self.addToolBar("Actions")

        widget_main = QtWidgets.QWidget(self)
        layout_main = QtWidgets.QVBoxLayout()

        # First
        self.w_function = WFunction(widget_main)
        layout_main.addWidget(self.w_function)

        # Second
        w_splitter = QtWidgets.QSplitter(widget_main)

        # Panel from left site
        self.w_object_panel = WObjectPanel(w_splitter)

        # FIXME: replace it
        self.w_object_panel.set_thread(self.cthread)
        self.w_object_panel.set_w_function(self.w_function)
        
        w_splitter.addWidget(self.w_object_panel)
        self.w_object_panel.set_function_item_clicked(self.press_item)
        self.w_object_panel.set_function_object_refresh(self.renew_object_presentation)

        self.w_item_tabs = WItemTabs(w_splitter)
        w_splitter.addWidget(self.w_item_tabs)
        
        
        self.text_edit = QtWidgets.QTextEdit(w_splitter)
        self.text_edit.setLineWrapMode(QtWidgets.QTextEdit.FixedPixelWidth)
        self.text_edit.setFont(QtGui.QFont("Courier", 8, QtGui.QFont.Normal))
        self.text_edit.setLineWrapColumnOrWidth(648)
        self.text_edit.rewrite_undo_last_line = False
        w_splitter.addWidget(self.text_edit)


        # # Panel from right site  
        # self.w_variables = WVariables(w_splitter)
        # w_splitter.addWidget(self.w_variables)
        # self.w_variables.set_func_object_clicked(self.display_item)
        # self.w_item_tabs.set_function_object_refresh(
        #     lambda: self.w_variables.set_object(self.object))


        width_m_1 = int(1 * self.info_width / 6.)
        width_m_2 = int(3 * self.info_width / 6.)
        width_m_3 = int(self.info_width - (width_m_1 + width_m_2))

        w_splitter.setSizes([width_m_1, width_m_2, width_m_3])

        layout_main.addWidget(w_splitter)
        widget_main.setLayout(layout_main)
        self.setCentralWidget(widget_main)

    def create_cryspy_actions(self):
        """Initialization of cryspy procedures in toolbar and menu.
        Creates actions for toolbar and menu.
        """
        dir_prog_icon = os.path.join(self.dir_prog, 'f_icon')
        self.setWindowIcon(
            QtGui.QIcon(os.path.join(dir_prog_icon, 'icon.png')))

        self.menu_file = self.menubar.addMenu('&File')
        self.form_menu_file()
        self.menu_options = self.menubar.addMenu('&Options')
        self.form_menu_options()

        self.form_cryspy_menus()

        self.statusBar()
        self.show()
        # cryspy_procedures_to_menubar(menubar, L_FUNCTION+L_FUNCTION_ADD)

    def form_menu_file(self):
        """Form menu "File".
        """
        dir_prog_icon = os.path.join(self.dir_prog, 'f_icon')

        new_action = QtWidgets.QAction(QtGui.QIcon(
            os.path.join(dir_prog_icon, 'new.png')), '&New', self)
        new_action.setStatusTip('New')
        new_action.triggered.connect(self.new)
        self.menu_file.addAction(new_action)
        self.toolbar_1.addAction(new_action)

        open_action = QtWidgets.QAction(QtGui.QIcon(
            os.path.join(dir_prog_icon, 'open.png')), '&Open', self)
        open_action.setShortcut('Ctrl+O')
        open_action.setStatusTip('Open file')
        open_action.triggered.connect(self.open)
        self.menu_file.addAction(open_action)
        self.toolbar_1.addAction(open_action)

        save_action = QtWidgets.QAction(QtGui.QIcon(
            os.path.join(dir_prog_icon, 'save.png')), '&Save', self)
        save_action.setShortcut('Ctrl+S')
        save_action.setStatusTip('Save')
        save_action.triggered.connect(self.save)
        self.menu_file.addAction(save_action)
        self.toolbar_1.addAction(save_action)

        save_as_action = QtWidgets.QAction(
            QtGui.QIcon(os.path.join(dir_prog_icon, 'save_as.png')),
            'Save &as...', self)
        save_as_action.setStatusTip('Save as ...')
        save_as_action.triggered.connect(self.save_as)
        self.menu_file.addAction(save_as_action)
        self.toolbar_1.addAction(save_as_action)
        
        self.menu_file.addSeparator()

        exit_action = QtWidgets.QAction('&Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(QtWidgets.qApp.quit)
        self.menu_file.addAction(exit_action)

        open_folder = QtWidgets.QAction(
            QtGui.QIcon(os.path.join(dir_prog_icon, 'open_folder.png')),
            'Open folder', self)
        open_folder.setStatusTip('Open folder')
        open_folder.triggered.connect(self.open_folder)
        self.toolbar_1.addAction(open_folder)

        refresh_view = QtWidgets.QAction(
            QtGui.QIcon(os.path.join(dir_prog_icon, 'refresh.png')),
            'Refresh', self)
        refresh_view.setStatusTip('Refresh')
        refresh_view.triggered.connect(self.refresh_view)
        self.toolbar_1.addAction(refresh_view)

    def refresh_view(self):
        self.text_edit.setText("")
        self.print_welcome()
        self.renew_object_presentation()
        self.print_object_info()

    def form_menu_options(self):
        """Form menu "Options".
        """
        action_packages = self.menu_options.addAction("Packages")
        action_packages.triggered.connect(self.show_packages)

        manual_site = self.menu_options.addAction("Manual (site)")
        manual_site.triggered.connect(lambda x: os.startfile(r"https://ikibalin.github.io/cryspy/"))

        about = self.menu_options.addAction("About")
        about.triggered.connect(self.print_help)

    def form_cryspy_menus(self):
        d_procedures = cryspy_procedures_to_dictionary()
        for key, functions in sorted(d_procedures.items()):
            menu_cryspy = self.menubar.addMenu(key)
            menu_cryspy.setToolTipsVisible(True)
            for func in functions:
                if key.lower().startswith(func.__name__.split("_")[0].lower()):
                    func_name =  " ".join(func.__name__.split("_")[1:]).lower().strip().title()
                else:
                    func_name = func.__name__.replace("_", " ").lower().strip().title()
                if check_function_to_auto_run(func):
                    func_name += " (autorun)"
                f_action = QtWidgets.QAction(func_name, menu_cryspy)
                f_action.object = func
                if func.__doc__ is not None:
                    f_action.setToolTip(func.__doc__)
                    f_action.setStatusTip(func.__doc__.strip().split("\n")[0])
                f_action.triggered.connect(lambda: self.object_to_procedure(self.press_procedure))
                menu_cryspy.addAction(f_action)

    def object_to_procedure(self, procedure):
        gui_object = self.sender()
        item_object = gui_object.object
        procedure(item_object)

    def renew_file_data_from_d_setup(self):
        d_setup = self.d_setup
        if "last_directory" in d_setup.keys():
            file_data = d_setup["last_directory"]
        else:
            file_data = ""
        if os.path.isfile(file_data):
            dir_data = os.path.dirname(file_data)
            self.file_data = file_data
            self.dir_data = dir_data
            print(f"Working directory is \n'{dir_data:}'")
        elif os.path.isdir(file_data):
            self.file_data = ""
            self.dir_data = file_data
            print(f"Working directory is \n'{file_data:}'")
        else:
            self.file_data = ""
            self.dir_data = self.dir_prog
            
        if self.file_data != "":
            self.setWindowTitle(f"CrysPy Editor: {self.file_data:}")
        elif self.dir_data != "":
            self.setWindowTitle(f"CrysPy Editor: {self.dir_data:} (not saved)")
        else:
            self.setWindowTitle(f"CrysPy Editor (not saved)")
        
        if self.dir_data != "":
            os.chdir(self.dir_data)

    def take_object_from_d_setup(self):
        """Load object from d_setup.
        """
        self.text_edit.setText("")
        self.print_welcome()
        self.renew_file_data_from_d_setup()
        if os.path.isfile(self.file_data):
            print(f"Loading data from file '{os.path.basename(self.file_data)}'...", end="\r")
            try:
                object = load_file(self.file_data)
            except Exception as e:
                print(80*"*")
                print("ERROR during data opening", end="\n")
                print(e)
                print(80*"*")
                return
            print(f"Data is loaded from file '{os.path.basename(self.file_data)}'.", end="\n")
        else:
            object = GlobalN.make_container((), (), "global")
        self.object = object
        self.renew_object_presentation()
        self.print_object_info()
    
    def print_object_info(self):
        try:
            object = self.object
            variable_names = object.get_variable_names()
            print(f"\nNumber of variables is {len(variable_names):}")
            for name in variable_names:
                value = object.get_variable_by_name(name)
                print(f" - {name[-1][0]:}  {value:.5f}")
        except:
            pass

    def renew_object_presentation(self):
        """Renew object_presentation.
        """
        object_ = self.object
        self.w_object_panel.set_object(object_)
        # self.w_variables.set_object(object_)
        self.display_item(object_)
        

    # procedures which is sended to  local classes to have connection with whole object
    def press_procedure(self, procedure):
        """Run procedure to performe procedure.
        """
        if check_function_to_auto_run(procedure):
            self.cthread.function = procedure
            self.cthread.arguments = (self.object, )
            self.cthread.start()
        else:
            self.w_function.set_function(procedure, self.cthread, globaln=self.object)

    def press_method(self, *argv):
        """Run procedure to performe method of item.
        """
        print("argv:", argv)
        print("sender:", self.sender())

    # @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def press_item(self, *argv):
        """Display item and its methods.
        """
        if len(argv) == 0:
            return
        gui_object = argv[0]
        if gui_object is not None:
            self.display_item(gui_object)

    def display_item(self, object_item):
        self.w_item_tabs.set_object(object_item)
        

    def add_item(self, *argv):
        """Run procedure to add item to the object.
        """
        print("argv:", argv)
        print("sender:", self.sender())

    def delete_item(self, *argv):
        """Run procedure to delete item from the object.
        """
        print("argv:", argv)
        print("sender:", self.sender())

    def replace_item(self, *argv):
        """Run procedure to replace item from the object.
        """
        print("argv:", argv)
        print("sender:", self.sender())


    def new(self) -> NoReturn:
        """Define new object."""
        obj = GlobalN.make_container((), (), "global")
        self.object = obj
        self.d_setup["last_directory"] = ""
        file_setup = os.path.join(os.path.dirname(__file__), 'setup.json')
        save_d_setup(self.d_setup, file_setup)
        self.renew_object_presentation()

    def save(self) -> NoReturn:
        """Save."""
        file_data = self.file_data
        object_ = self.object

        with open(file_data, "w") as fid:
            fid.write(object_.to_cif())

    def save_as(self) -> NoReturn:
        """Save as."""
        file_data, okPressed = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Select a file:', self.dir_data, "Rcif files (*.rcif)")
        if not (okPressed):
            return None
        self.d_setup["last_directory"] = file_data
        self.file_data = file_data
        self.save()
        self.renew_file_data_from_d_setup()

        file_setup = os.path.join(os.path.dirname(__file__), 'setup.json')
        save_d_setup(self.d_setup, file_setup)

    def open_folder(self) -> NoReturn:
        """Open folder."""
        os.startfile(self.dir_data)

    def open(self) -> NoReturn:
        """Open."""
        file_data, okPressed = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Select a cif file:', self.dir_data, "All files (*.*)")
        if not (okPressed):
            return None
        
        self.d_setup["last_directory"] = file_data
        self.take_object_from_d_setup()

        file_setup = os.path.join(os.path.dirname(__file__), 'setup.json')
        save_d_setup(self.d_setup, file_setup)
        
    def show_packages(self):
        obj = WPackages(self)
        obj.show()

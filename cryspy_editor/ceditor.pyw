import os
import sys
import numpy

from typing import Union, NoReturn
from types import FunctionType

from PyQt5 import QtCore
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui

from PyQt5.QtWidgets import QMainWindow, QAction
from PyQt5.QtGui import QIcon

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView # install module PyQtWebEngine
    flag_web_engine = True
except:
    flag_web_engine = False

import matplotlib.pyplot as plt

from importlib import import_module

from cryspy import load_file, GlobalN, DataN, LoopN, ItemN, Pd2dMeas, Pd2dProc, ChannelChi, ChannelPlusMinus
from cryspy import L_GLOBAL_CLASS, L_DATA_CLASS, L_ITEM_CLASS, L_LOOP_CLASS
L_GLOBAL_CLS = L_GLOBAL_CLASS
L_DATA_CLS = L_DATA_CLASS
L_LOOP_CLS = L_LOOP_CLASS
L_ITEM_CLS = L_ITEM_CLASS


from cryspy_editor.widgets.w_function import WFunction
from cryspy_editor.widgets.w_object_panel import WObjectPanel
from cryspy_editor.widgets.w_editcif import WEditCif
from cryspy_editor.widgets.matplotlib import Graph
from cryspy_editor.widgets.cryspy_objects import cryspy_procedures_to_dictionary, check_function_to_auto_run, check_function_for_procedure

from cryspy_editor.cl_thread import CThread

from cryspy import __version__ as cryspy_version
from cryspy_editor import __version__ as cryspy_editor_version

def get_external_functions(l_f_name_external: list):
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
                    if not(obj_name.startswith("__")):
                        obj = getattr(module, obj_name)
                        if hasattr(obj, "__call__"):
                            if check_function_for_procedure(obj): # 
                                l_func_external.append(obj)
        except:
            pass
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
        way_full = way + (name_item, ) 
    else:
        return (name_item, )
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
             os.startfile(dir_name)

    def form_q_list(self):
        l_names = sorted(self.parent.d_setup["file_names_for_external_functions"].split(";"))
        self.q_list.addItems(l_names)

    def add_function(self):

        if "data_dir_name" in self.parent.d_setup.keys():
            f_dir = self.parent.d_setup["data_dir_name"]
        else:
            f_dir = "."
        
        QtWidgets.QMessageBox.information(self, "Tips", 
            "File name must not match any of the Python modules!\nThen reboot 'CrysPy editor' to use the added procedures.")

        file_name, ok = QtWidgets.QFileDialog.getOpenFileName(self,"Open file", f_dir,"Python Files (*.py);; All Files (*)")
        if ok:
            if "file_names_for_external_functions" in self.parent.d_setup.keys():
                if self.parent.d_setup["file_names_for_external_functions"] == "":
                    self.parent.d_setup["file_names_for_external_functions"] = file_name
                else:
                    self.parent.d_setup["file_names_for_external_functions"] += ";" + file_name
            else:
                self.parent.d_setup["file_names_for_external_functions"] = file_name
            self.q_list.addItem(file_name)
            numpy.save(self.parent.f_setup, self.parent.d_setup)

    def delete_function(self):
        f_item = self.q_list.currentItem()
        try:
            f_delete = f_item.text()
            l_names = self.parent.d_setup["file_names_for_external_functions"].split(";")
            l_names_new = sorted([name for name in l_names if not(name.startswith(f_delete))])
            self.q_list.clear()
            self.parent.d_setup["file_names_for_external_functions"] = ";".join(l_names_new)
            numpy.save(self.parent.f_setup, self.parent.d_setup)
            self.q_list.addItems(l_names_new)
        except:
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
    def __init__(self):
        super(CMainWindow, self).__init__()

        self.dir_prog = os.path.dirname(__file__)
        self.d_setup = {
            "data_file_name": os.path.join(self.dir_prog, ), "data_dir_name": self.dir_prog,
            "file_names_for_external_functions": ""}
        self.f_setup = os.path.join(self.dir_prog, "setup.npy")
        if os.path.isfile(self.f_setup):
            self.d_setup = numpy.load(self.f_setup, allow_pickle='TRUE').item()

        # Thread block        
        self.cthread = CThread(self)
        self.cthread.signal_start.connect(self.run_calculations)
        self.cthread.signal_end.connect(self.end_calculations)

        self.setWindowTitle("Cryspy Editor")
        self.init_user_interface()

        self.show()
        

        self.print_welcome()
        if "data_file_name" in self.d_setup.keys():
            self.take_rcif_object_from_d_setup()
            self.print_object_info()


    def write(self):
        try:
            # text = self.cthread.out_terminal.getvalue()
            # self.text_edit.setText(text)

            text = self.cthread.out_terminal.text_last
            text_permanent = "\n".join(self.cthread.out_terminal.l_text_permanent)
            self.text_edit.setText(text_permanent+"\n"+text)
            # if text.endswith("\r"):
            #     self.text_edit.rewrite_undo_last_line = True
            # elif text == "\n":
            #     pass
            # else:
            #     if self.text_edit.rewrite_undo_last_line:
            #         self.text_edit.undo()
            #         self.text_edit.rewrite_undo_last_line = False
            #     self.text_edit.append(text.rstrip())
        except:
            pass

    def user_scripts(self):
        options_window = OptionsWindow(self)
        options_window.show()

    def run_calculations(self):# d_info: dict = None
        thread = self.cthread
        self.text_edit.setText("Calculations are running ...")
        self.text_edit.setStyleSheet("background-color:yellow;")
        self.cthread.out_terminal.signal_refresh.connect(self.write)


    def end_calculations(self): #output_data
        self.text_edit.setStyleSheet("background-color:white;")
        if not(self.cthread.out_terminal.out_terminal.closed):
            self.write()
            self.cthread.out_terminal.close()
        self.renew_w_object_panel()


    def init_user_interface(self):
        self.location_on_the_screen()
        dir_prog_icon = os.path.join(self.dir_prog, 'f_icon')

        self.menu_bar = self.menuBar()
        toolbar_1 = self.addToolBar("Actions")

        # Menu file
        menu_file = self.menu_bar.addMenu('File')

        open_action = QAction(QtGui.QIcon(
            os.path.join(dir_prog_icon, 'open.png')), '&Open', self)
        open_action.setShortcut('Ctrl+O')
        open_action.setStatusTip('Open file')
        open_action.triggered.connect(self.open_file)
        menu_file.addAction(open_action)
        toolbar_1.addAction(open_action)


        save_action = QtWidgets.QAction(QtGui.QIcon(
            os.path.join(dir_prog_icon, 'save.png')), '&Save', self)
        save_action.setShortcut('Ctrl+S')
        save_action.setStatusTip('Save')
        save_action.triggered.connect(self.save_file)
        menu_file.addAction(save_action)
        toolbar_1.addAction(save_action)

        save_as_action = QtWidgets.QAction(
            QtGui.QIcon(os.path.join(dir_prog_icon, 'save_as.png')),
            'Save &as...', self)
        save_as_action.setStatusTip('Save as ...')
        save_as_action.triggered.connect(self.save_file_as)
        menu_file.addAction(save_as_action)
        toolbar_1.addAction(save_as_action)

        exit_button=QAction(QIcon(os.path.join(dir_prog_icon, 'exit24.png')), 'Exit', self)
        exit_button.setShortcut('Ctrl+Q')
        exit_button.setStatusTip('Exit application')
        exit_button.triggered.connect(self.close)
        menu_file.addAction(exit_button)


        open_folder = QAction(QIcon(os.path.join(dir_prog_icon, 'open_folder.png')), 'Open folder', self)
        open_folder.setStatusTip('Open folder')
        open_folder.triggered.connect(lambda: os.startfile(self.d_setup["data_dir_name"]))
        toolbar_1.addAction(open_folder)

        refresh_view = QAction(QIcon(os.path.join(dir_prog_icon, 'refresh.png')), 'Refresh', self)
        refresh_view.setStatusTip('Refresh')
        refresh_view.triggered.connect(self.refresh_view)
        toolbar_1.addAction(refresh_view)

        # Menu Options
        menu_options = self.menu_bar.addMenu('Options')
        manual_site = menu_options.addAction("Manual (site)")
        manual_site.triggered.connect(lambda x: os.startfile(r"https://sites.google.com/view/cryspy/main"))

        add_user_scripts = menu_options.addAction("User scripts")
        add_user_scripts.triggered.connect(self.user_scripts)

        about = menu_options.addAction("About")
        about.triggered.connect(self.display_about)

        # Menu CrysPy
        self.init_menu_cryspy()

        self.init_central_widget()
        

    def display_about(self):
        QtWidgets.QMessageBox.information(
            self, "About CrysPy",
            f"Versions:\n CrysPy Editor - {cryspy_editor_version:} \n CrysPy library - {cryspy_version:}")


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
        try:
            rcif_object = self.rcif_object
            variable_names = rcif_object.get_variable_names()
            ls_text =[f"\nNumber of variables is {len(variable_names):}"]
            for name in variable_names:
                value = rcif_object.get_variable_by_name(name)
                ls_text.append(f" - {name[-1][0]:}  {value:.5f}")
            self.text_edit.append("\n".join(ls_text))
        except:
            pass

    def init_menu_cryspy(self):
        if not("file_names_for_external_functions" in self.d_setup.keys()):
            self.d_setup["file_names_for_external_functions"] = ""
        l_f_name_external_not_checked = self.d_setup["file_names_for_external_functions"].split(";")
        l_f_name_external = [f_name for f_name in l_f_name_external_not_checked if os.path.isfile(f_name)]
        self.d_setup["file_names_for_external_functions"] = ";".join(l_f_name_external)
        numpy.save(self.f_setup, self.d_setup)
        l_func_external = get_external_functions(l_f_name_external)
        
        
        d_procedures = cryspy_procedures_to_dictionary(l_func_external)
        for key, functions in sorted(d_procedures.items()):
            menu_cryspy = self.menu_bar.addMenu(key)
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
        f_action = self.sender()
        func_to_do = f_action.object
        procedure(func_to_do)

    # procedures which is sended to  local classes to have connection with whole object
    def press_procedure(self, procedure):
        """Run procedure to performe procedure.
        """

        if check_function_to_auto_run(procedure):
            self.cthread.function = procedure
            self.cthread.arguments = (self.rcif_object, )
            self.cthread.start()
        else:
            self.w_function.set_function(procedure, self.cthread, globaln=self.rcif_object)


    def location_on_the_screen(self):
        """Location on the screen."""
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        self.setMinimumSize(int(screen.width() * 1 / 4), int(screen.height() * 1 / 4))
        self.info_width = int(screen.width() * 8. / 10.)
        self.info_height = int(screen.height() * 14. / 16.)
        self.move(int(screen.width() / 10), int(screen.height() / 20))
        self.resize(int(screen.width() * 8. / 10.), int(screen.height() * 14. / 16.))

    def save_file(self):
        if "data_file_name" in self.d_setup.keys():
            file_name = self.d_setup["data_file_name"]
            rcif_object = self.rcif_object

            with open(file_name, "w") as fid:
                fid.write(rcif_object.to_cif())
            numpy.save(self.f_setup, self.d_setup) 
            
    def save_file_as(self):
        # Save
        if "data_dir_name" in self.d_setup.keys():
            f_dir = self.d_setup["data_dir_name"]
        else:
            f_dir = "."

        file_name, ok = QtWidgets.QFileDialog.getSaveFileName(self, "Save file as ...", f_dir, "RCIF Files (*.rcif);; CIF Files (*.cif);; All Files (*)")
        if ok:
            self.d_setup["data_file_name"] = file_name
            self.d_setup["data_dir_name"] = os.path.dirname(file_name)
            self.save_file()

    def open_file(self):
        # Load
        f_dir = self.d_setup["data_dir_name"]
        if not(os.path.isdir(f_dir)):
            f_dir = "."
        # options = QtWidgets.QFileDialog.Options()
        file_name, ok = QtWidgets.QFileDialog.getOpenFileName(self,"Open file", f_dir,"RCIF Files (*.rcif);; CIF Files (*.cif);; All Files (*)")
        if ok:
            self.d_setup["data_file_name"] = file_name
            self.d_setup["data_dir_name"] = os.path.dirname(file_name)
            self.take_rcif_object_from_d_setup()

            # self.setWindowTitle(f"CrysPy Editor: {os.path.basename(file_name):}")
            numpy.save(self.f_setup, self.d_setup)
            self.print_object_info()
    
    def take_rcif_object_from_d_setup(self):
        """Load object from d_setup.
        """
        # self.text_edit.setText("")
        # self.print_welcome()
        # self.renew_file_data_from_d_setup()
        file_name = self.d_setup["data_file_name"]
        ls_out = []
        if os.path.isfile(file_name):
            ls_out.append(f"Loading data from file '{os.path.basename(file_name)}'...")
            self.text_edit.append("\n".join(ls_out))
            try:
                rcif_object = load_file(file_name)
                self.d_setup["data_dir_name"] = os.path.dirname(file_name)
            except Exception as e:
                ls_out.append(80*"*")
                ls_out.append("ERROR during data opening")
                ls_out.append(str(e))
                ls_out.append(80*"*")
                self.text_edit.append("\n".join(ls_out))
                return
            self.setWindowTitle(f"CrysPy Editor: {os.path.basename(file_name):}")
        else:
            rcif_object = GlobalN.make_container((), (), "global")
        self.rcif_object = rcif_object
        self.renew_w_object_panel()


    def renew_w_object_panel(self):
        """Renew object_presentation.
        """
        rcif_object = self.rcif_object
        dict_tree = form_dict_tree_for_rcif_object(rcif_object)
        self.w_object_panel.set_dict_tree(dict_tree)

        way_item = self.w_item_tabs.item_way_in_w_item_tabs
        self.renew_w_item_tabs(way_item)


    def renew_w_item_tabs(self, way_item):
        # print("id(self.rcif_object): ", id(self.rcif_object))
        # print("id(item): ", [id(loop_item) for loop_item in item.items], id(item))
        # print("way_item: ", way_item)
        w_item_tabs = self.w_item_tabs
        w_item_tabs.item_way_in_w_item_tabs = way_item
        
        tab_text = ""
        if w_item_tabs.count() != 0:
            tab_text = str(w_item_tabs.tabText(w_item_tabs.currentIndex()))

        for ind_item in range(w_item_tabs.count()-1, -1, -1):
            w_item_tabs.removeTab(ind_item)
        plt.close()
        plt.close()
        
        if way_item is not None:
            item = take_item(self.rcif_object, way_item)
            if item is None:
                item = self.rcif_object
        else:
            item = self.rcif_object

        # RCIF tab
        if (isinstance(item, (LoopN, ItemN)) and not(isinstance(item, (Pd2dMeas, Pd2dProc, ChannelChi, ChannelPlusMinus)))):
            if isinstance(item, ItemN):
                s_item = item.to_cif(separator="_", flag_all_attributes=True)
            else:
                s_item = str(item)
            w_edit_cif = WEditCif(s_item, self.rewrite_item_in_edit_cif, parent=w_item_tabs)
            # w_edit_cif.setToolTip(item.__doc__)
            w_item_tabs.addTab(w_edit_cif, "RCIF format") 

        # if isinstance(object_, LoopN):
        #     w_loop_items = WLoopItems(None, self.thread, self)
        #     w_loop_items.set_object(object_)
        #     self.addTab(w_loop_items, "Items") 

        # Figure tab
        try:
            l_fig_ax = ([fig_ax for fig_ax in item.plots() if fig_ax is not None])
        except Exception as e:
            l_fig_ax = []
            print("ERROR in obj.plots")
            print(e)

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

        # Report tab
        try:
            report_html = item.report_html()
        except Exception as e:
            report_html = ""
            print("ERROR in object_.report_html")
            print(e)

        if report_html != "":
            if flag_web_engine:
                w_plain_text = QWebEngineView(w_item_tabs)
                w_plain_text.setHtml(report_html)
                w_item_tabs.addTab(w_plain_text, "View") 
                # self.insertTab(0, w_plain_text, "View")

        if w_item_tabs.count() == 0:
            q_label = QtWidgets.QLabel(
                f"No graphs or other information for '{item.get_name():}'.")
            q_label.setSizePolicy(
                QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                      QtWidgets.QSizePolicy.Expanding))
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
        self.w_object_panel = WObjectPanel(self.item_clicked_on_w_object_panel, self.display_item_menu, self.item_to_rcif, parent=w_splitter)
        w_splitter.addWidget(self.w_object_panel)

        self.w_item_tabs = QtWidgets.QTabWidget(w_splitter)
        self.w_item_tabs.item_way_in_w_item_tabs = None
        w_splitter.addWidget(self.w_item_tabs)

        self.text_edit = QtWidgets.QTextEdit(w_splitter)
        self.text_edit.setLineWrapMode(QtWidgets.QTextEdit.FixedPixelWidth)
        self.text_edit.setFont(QtGui.QFont("Courier", 8, QtGui.QFont.Normal))
        self.text_edit.setLineWrapColumnOrWidth(648)
        self.text_edit.rewrite_undo_last_line = False
        w_splitter.addWidget(self.text_edit)

        width_m_1 = int(1 * self.info_width / 6.)
        width_m_2 = int(3 * self.info_width / 6.)
        width_m_3 = int(self.info_width - (width_m_1 + width_m_2))
        w_splitter.setSizes([width_m_1, width_m_2, width_m_3])

        layout_main.addWidget(w_splitter)
        widget_main.setLayout(layout_main)
        self.setCentralWidget(widget_main)

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


    def rewrite_item_in_edit_cif(self, text:str):
        rcif_object = self.rcif_object
        way_item = self.w_item_tabs.item_way_in_w_item_tabs
        if way_item is not None:
            item = take_item(rcif_object, way_item)
            item_2 = item.from_cif(text)
            if item_2 is not None:
                item.copy_from(item_2)
        else:
            self.renew_w_object_panel()

    @QtCore.pyqtSlot(QtCore.QPoint,)
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

        if ((type(item) is GlobalN) | (type(item) is DataN)):

            if type(item) is GlobalN:
                menu_data = menu.addMenu("Add data block")

                for cls_item in L_DATA_CLS:
                    prefix = cls_item.PREFIX
                    add_item = QtWidgets.QAction(f'{prefix :}', menu_data)
                    add_item.cls_item = cls_item
                    add_item.way_item = way_item
                    add_item.triggered.connect(self.add_item)
                    menu_data.addAction(add_item)

            menu_loop = menu.addMenu("Add loop block")
            for cls_item in L_LOOP_CLS:
                prefix = cls_item.ITEM_CLASS.PREFIX
                add_item = QtWidgets.QAction(f'{prefix :}', menu_loop)
                add_item.cls_item = cls_item
                add_item.way_item = way_item
                add_item.triggered.connect(self.add_item)
                menu_loop.addAction(add_item)

            menu_item = menu.addMenu("Add item")
            for cls_item in L_ITEM_CLS:
                prefix = cls_item.PREFIX
                add_item = QtWidgets.QAction(f'{prefix :}', menu_item)
                add_item.cls_item = cls_item
                add_item.way_item = way_item
                add_item.triggered.connect(self.add_item)
                menu_item.addAction(add_item)
            
        elif isinstance(item, (GlobalN, DataN)):
            menu_item = menu.addMenu("Add")
            for cls_item in item.CLASSES_MANDATORY:
                if ((cls_item is not DataN) & (cls_item is not LoopN) &
                    (cls_item is not ItemN)):
                    if "PREFIX" in cls_item.__dict__.keys():
                        prefix = cls_item.PREFIX
                    else:
                        prefix = cls_item.ITEM_CLASS.PREFIX
                    add_item = QtWidgets.QAction(f'{prefix:}', menu_item)
                    add_item.cls_item = cls_item
                    add_item.way_item = way_item
                    add_item.triggered.connect(self.add_item)
                    menu_item.addAction(add_item)
            menu_item.addSeparator()
            for cls_item in item.CLASSES_OPTIONAL:
                if ((cls_item is not DataN) & (cls_item is not LoopN) &
                        (cls_item is not ItemN)):
                    if "PREFIX" in cls_item.__dict__.keys():
                        prefix = cls_item.PREFIX
                    else:
                        prefix = cls_item.ITEM_CLASS.PREFIX
                    add_item = QtWidgets.QAction(f'{prefix :}', menu_item)
                    add_item.cls_item = cls_item
                    add_item.way_item = way_item
                    add_item.triggered.connect(self.add_item)
                    menu_item.addAction(add_item)


        if isinstance(item, (GlobalN, DataN, LoopN)):
            act_rename = QtWidgets.QAction("Rename", menu)
            act_rename.way_item = way_item
            act_rename.triggered.connect(self.do_function)
            menu.addAction(act_rename)

        if isinstance(item, (DataN, LoopN, ItemN)):
            del_item = QtWidgets.QAction('Delete', menu)
            del_item.way_item = way_item
            del_item.triggered.connect(self.do_function)
            menu.addAction(del_item)


        method_names = [_1 for _1, _2 in type(item).__dict__.items()
                     if ((type(_2) == FunctionType) &
                         (not(_1.startswith("_"))))]

        if len(method_names)!= 0:
            menu_methods = menu.addMenu("Methods")
            for name in method_names:
                func = getattr(item, name)
                l_param = [_ for _ in func.__code__.co_varnames[
                    :func.__code__.co_argcount] if _ != "self"]
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

        menu.exec_(w_object_panel.viewport().mapToGlobal(position))

    @QtCore.pyqtSlot(bool,)
    def do_function(self, *argv):
        sender = self.sender()
        name = sender.text()
        flag_do = True
        if name == "Refine all variables":
            name = "refine_all_variables"
        elif name == "Fix all variables":
            name = "fix_variables"
        elif (name in ["Delete", "Rename"]):
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
                        parent_item = take_item(self.rcif_object, way_parent_item)
                    if ((parent_item is not None) and (item is not None)):
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
                        self, f"Input dialog {item.get_name():}", "Enter the new name")
                    if ok:
                        new_name = "".join(text.split())
                        if isinstance(item, GlobalN):
                            item.global_name = new_name
                        elif isinstance(item, DataN):
                            item.data_name = new_name
                        elif isinstance(item, LoopN):
                            item.loop_name = new_name
                        self.renew_w_object_panel()

    def item_to_rcif(self, tree_widget_item: QtWidgets.QTreeWidgetItem):
        rcif_object = self.rcif_object
        way_item = form_way(tree_widget_item)
        item = take_item(rcif_object, way_item)
        return item.to_cif()



    @QtCore.pyqtSlot(bool,)
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
        
            if ((type(item) is DataN) | (type(item) is GlobalN)):
                item_cls = set([type(item) for item in item.items])
                if type(new_item) not in item_cls:
                    item.CLASSES_OPTIONAL = tuple(list(item.CLASSES_OPTIONAL) +
                                                 [type(new_item)])
                    item.CLASSES = tuple(list(item.CLASSES) + [type(new_item)])
            item.add_items([new_item])
            self.renew_w_object_panel()


# if __name__=='__main__':
#     app = QApplication(sys.argv)
#     f_icon = os.path.join(os.path.dirname(__file__), "f_icon", "logo.png")
#     app.setWindowIcon(QtGui.QIcon(f_icon))
#     ex = CMainWindow()
#     sys.exit(app.exec_())
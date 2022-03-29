import os
import sys
import numpy

from typing import Union, NoReturn
from types import FunctionType

from PyQt5 import QtCore
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui

from PyQt5.QtWidgets import QApplication, QMainWindow, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView # install module PyQtWebEngine
    flag_web_engine = True
except:
    flag_web_engine = False

import matplotlib.pyplot as plt


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
from cryspy_editor.widgets.cryspy_objects import cryspy_procedures_to_dictionary, check_function_to_auto_run

from cryspy_editor.cl_thread import CThread

from cryspy import __version__ as cryspy_version
from cryspy_editor import __version__ as cryspy_editor_version


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



class CMainWindow(QMainWindow):
    def __init__(self):
        super(CMainWindow, self).__init__()
        
        OUTPUT_LOGGER_STDOUT.emit_write.connect(self.append_log)
        OUTPUT_LOGGER_STDERR.emit_write.connect(self.append_log)

        self.dir_prog = os.path.dirname(__file__)
        self.d_setup = {"data_file_name": os.path.join(self.dir_prog, ), "data_dir_name": self.dir_prog}
        self.f_setup = os.path.join(self.dir_prog, "setup.npy")
        if os.path.isfile(self.f_setup):
            self.d_setup = numpy.load(self.f_setup, allow_pickle='TRUE').item()


        # Thread block        
        self.cthread = CThread(self)
        self.cthread.signal_start.connect(self.run_calculations)
        self.cthread.signal_end.connect(self.end_calculations)

        self.setWindowTitle("Cryspy Editor")
        self.init_user_interface()
        
        self.print_welcome()
        if "data_file_name" in self.d_setup.keys():
            self.take_rcif_object_from_d_setup()
            self.print_object_info()



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


    def end_calculations(self): #output_data
        self.text_edit.setStyleSheet("background-color:white;")
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
        manual_site.triggered.connect(lambda x: os.startfile(r"https://ikibalin.github.io/cryspy/"))

        about = menu_options.addAction("About")
        about.triggered.connect(self.display_about)

        # Menu CrysPy
        self.init_menu_cryspy()

        self.init_central_widget()
        self.show()


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
        print("*************************")
        print("Welcome to CrysPy Editor.")
        print("*************************")

    def print_object_info(self):
        try:
            rcif_object = self.rcif_object
            variable_names = rcif_object.get_variable_names()
            print(f"\nNumber of variables is {len(variable_names):}")
            for name in variable_names:
                value = rcif_object.get_variable_by_name(name)
                print(f" - {name[-1][0]:}  {value:.5f}")
        except:
            pass

    def init_menu_cryspy(self):
        d_procedures = cryspy_procedures_to_dictionary()
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

            self.setWindowTitle(f"CrysPy Editor: {os.path.basename(file_name):}")
            numpy.save(self.f_setup, self.d_setup)
            self.print_object_info()
    
    def take_rcif_object_from_d_setup(self):
        """Load object from d_setup.
        """
        # self.text_edit.setText("")
        # self.print_welcome()
        # self.renew_file_data_from_d_setup()
        file_name = self.d_setup["data_file_name"]
        if os.path.isfile(file_name):
            print(f"Loading data from file '{os.path.basename(file_name)}'...", end="\r")
            try:
                rcif_object = load_file(file_name)
                self.d_setup["data_dir_name"] = os.path.dirname(file_name)
            except Exception as e:
                print(80*"*")
                print("ERROR during data opening", end="\n")
                print(e)
                print(80*"*")
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
        self.w_object_panel = WObjectPanel(
            self.item_clicked_on_w_object_panel, self.display_item_menu, parent=w_splitter)
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

        item = take_item(rcif_object, way_item)
        if item is None:
            self.renew_w_object_panel()
        else:
            self.renew_w_item_tabs(way_item)


    def rewrite_item_in_edit_cif(self, text:str):
        rcif_object = self.rcif_object
        way_item = self.w_item_tabs.item_way_in_w_item_tabs

        item = take_item(rcif_object, way_item)
        if item is None:
            self.renew_w_object_panel()
        else:
            item_2 = item.from_cif(text)
            if item_2 is not None:
                item.copy_from(item_2)

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
        way_full = way+(name_item, ) 
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

if __name__=='__main__':
    app = QApplication(sys.argv)
    ex = CMainWindow()
    sys.exit(app.exec_())
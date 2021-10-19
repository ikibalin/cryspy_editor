"""WFunction class."""
from typing import Callable, NoReturn
from PyQt5 import QtWidgets, QtCore

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView # install module PyQtWebEngine
    flag_web_engine = True
except:
    flag_web_engine = False


from cryspy import LoopN, ItemN

from cryspy_editor.widgets.w_editcif import WEditCif
# from cryspy_editor.widgets.w_interactive import w_for_interaction

# from cryspy_editor.widgets.w_console import WConsole

from cryspy_editor.widgets.w_loop_items import WLoopItems

from cryspy import Pd2dMeas, Pd2dProc

from cryspy_editor.widgets.matplotlib import Graph
import matplotlib.pyplot as plt


class WItemTabs(QtWidgets.QTabWidget):
    """
    WBaseObj class.

    Attributes
    ----------
        - thread
    Mehtods
    -------
        - set_object
    """

    def __init__(self, parent=None):
        super(WItemTabs, self).__init__(parent)
        self.thread = None
        # self.w_notes = QWebEngineView(self)
        # self.w_notes.setHtml("<h1>Notes</h1>")
        # self.addTab(self.w_notes, "Notes")         

        # self.w_console = WConsole(self)
        # self.addTab(self.w_console, "Output")

    def set_function_object_refresh(
            self, function_object_refresh: Callable) -> NoReturn:
        """Set function when the object representation has to be refreshed."""
        self.func_object_refresh = function_object_refresh

    def set_thread(self, thread: QtCore.QThread):
        """Set thread."""
        self.thread = thread

    def setText(self, text: str):
        """Set text."""
        pass

    def write_to_object(self):
        """Write to object."""
        if self.object is None:
            return
        # stext = self.wlabel.toPlainText()
        # obj2 = self.object.from_cif(stext)
        # if obj2 is not None:
        #     self.object.copy_from(obj2)
        # run_function(pass_func, (), self.thread)

    def set_object(self, object_):
        """Set text."""
        if object_ is None:
            return
        self.object = object_

        tab_text = ""
        if self.count() != 0:
            tab_text = str(self.tabText(self.currentIndex()))

        for ind_item in range(self.count()-1, -1, -1):
            self.removeTab(ind_item)
        plt.close()
        plt.close()

        # RCIF tab
        
        if (isinstance(object_, (LoopN, ItemN)) and not(isinstance(object_, (Pd2dMeas, Pd2dProc)))):
            w_plain_text = WEditCif(self)
            # w_plain_text.set_function_object_refresh(self.func_object_refresh)
            w_plain_text.set_object(object_)
            self.addTab(w_plain_text, "RCIF format") 
        
        if isinstance(object_, LoopN):
            w_loop_items = WLoopItems(None, self.thread, self)
            w_loop_items.set_object(object_)
            self.addTab(w_loop_items, "Items") 
        # Figure tab
        try:
            l_fig_ax = ([fig_ax for fig_ax in object_.plots() if fig_ax is not None])
        except Exception as e:
            l_fig_ax = []
            print("ERROR in obj.plots")
            print(e)

        for fig, ax in l_fig_ax:
            widget = QtWidgets.QWidget(self)
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
            self.addTab(widget, s_text)
            # self.insertTab(0, widget, s_text)

        # Report tab
        try:
            report_html = object_.report_html()
        except Exception as e:
            report_html = ""
            print("ERROR in object_.report_html")
            print(e)

        if report_html != "":
            if flag_web_engine:
                w_plain_text = QWebEngineView(self)
                w_plain_text.setHtml(report_html)
                self.addTab(w_plain_text, "View") 
                # self.insertTab(0, w_plain_text, "View")

        if self.count() == 0:
            q_label = QtWidgets.QLabel(
                f"No graphs or other information for '{object_.get_name():}'.")
            q_label.setSizePolicy(
                QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                      QtWidgets.QSizePolicy.Expanding))
            self.addTab(q_label, "")


        # if tab_text == "Notes":
        #     self.setCurrentIndex(0)
        # else:
        #     flag_first = True
        flag_first = True
        for ind_tab in range(self.count()):
            if tab_text == str(self.tabText(ind_tab)):
                self.setCurrentIndex(ind_tab)
                flag_first = False
                break
        if flag_first:
            self.setCurrentIndex(0)

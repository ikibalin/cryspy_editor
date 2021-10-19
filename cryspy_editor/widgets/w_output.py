"""WConsole class."""
from PyQt5 import QtWidgets, QtCore, QtGui
import matplotlib
import matplotlib.pyplot as plt
from cryspy_editor.widgets.matplotlib import Graph

class WOutput(QtWidgets.QScrollArea):
    """WFunction class."""

    def __init__(self, parent=None):
        super(WOutput, self).__init__(parent)

        self.setWidgetResizable(True)

        self.wlabel = QtWidgets.QLabel()
        self.wlabel.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                  QtWidgets.QSizePolicy.Expanding))
        self.wlabel.setFont(QtGui.QFont("Courier", 8, QtGui.QFont.Normal))
        self.wlabel.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.wlabel.setAlignment(QtCore.Qt.AlignTop)
        self.wlabel.setWordWrap(True)
        self.wlabel.setStyleSheet("background-color:white;")

        self.setWidget(self.wlabel)

    def setText(self, text: str):
        """Set text."""
        self.wlabel.setText(text)

    def setObjects(self, tuple_objects):
        """Display object."""
        flag = False
        if tuple_objects is None:
            self.wlabel.setText("No output information.")
        elif isinstance(tuple_objects, str):
            self.wlabel.setText(tuple_objects)
        elif isinstance(tuple_objects, (list, tuple, )):
            flag = True
            flag_tab = True
            tuple_objects_new = []
            for i_obj, obj in enumerate(tuple_objects):
                if isinstance(obj, plt.Figure):
                    if flag_tab:
                        window_fig = QtWidgets.QMainWindow(self)
                        window_fig.setWindowTitle('Graphs')
                        window_fig.resize(500, 500)

                        widget_tab = QtWidgets.QTabWidget(parent=window_fig)

                        window_fig.setCentralWidget(widget_tab)
                        flag_tab = False
                    widget = QtWidgets.QWidget(self)
                    layout = QtWidgets.QVBoxLayout()
                    item_plot = Graph(obj, parent=widget)
                    toolbar = item_plot.get_toolbar(parent=widget)

                    layout.addWidget(toolbar)
                    layout.addWidget(item_plot)
                    widget.setLayout(layout)
                    s_text = f"Output{i_obj+1:}"
                    widget_tab.addTab(widget, s_text)
                else:
                    tuple_objects_new.append(obj)
        else: 
            self.wlabel.setText(str(tuple_objects))

        if flag:
            self.wlabel.setText(str(tuple_objects_new))
            if not(flag_tab):
                window_fig.show()

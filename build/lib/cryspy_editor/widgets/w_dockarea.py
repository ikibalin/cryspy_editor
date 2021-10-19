"""WFunction class."""
from PyQt5 import QtCore, QtWidgets
import pyqtgraph.dockarea as pg_da

from cryspy_editor.widgets.w_presentation import w_for_presentation


class WDockArea(pg_da.DockArea):
    """
    WDockArea class.

    Attributes
    ----------
        - thread
    Mehtods
    -------
        - set_object
    """

    def __init__(self, parent=None):
        super(WDockArea, self).__init__(parent)
        self.thread = None

    def set_thread(self, thread: QtCore.QThread):
        """Set thread."""
        self.thread = thread

    def normal_clear(self):
        """Clear procedure has a bug."""
        self.clear()
        if self.count() != 0:
            self.normal_clear()

    def set_object(self, obj):
        """Set text.

        Output is actions
        """
        if obj is None:
            return
        self.normal_clear()
        # When number of docks is high the one clear method is not enough
        # I think that it is the bug of pyqtgraph.dockarea.
        # if self.count() != 0:
        #     self.clear()

        docks = []
        docks, w_actions = w_for_presentation(obj, self.thread)
        l_ordered_docks = []
        i_actions = 0
        for i_dock, dock in enumerate(docks):
            dock.setParent(self)
            if dock.title().startswith("Actions"):
                dock.label.hide()
                l_ordered_docks.insert(i_actions, dock)
                i_actions += 1
            else:
                l_ordered_docks.append(dock)

        for i_dock, dock in enumerate(l_ordered_docks):
            if (i_dock < i_actions):
                dock.setStretch(x=1, y=1)
                if i_dock == 0:
                    self.addDock(dock, "bottom")
                else:
                    self.addDock(dock, "right", l_ordered_docks[i_dock-1])
            elif (i_dock == i_actions):
                dock.setStretch(x=10, y=10)
                self.addDock(dock, "bottom")
            elif (i_dock == i_actions+1):
                dock.setStretch(x=10, y=10)
                self.addDock(dock, "right", l_ordered_docks[i_dock-1])
            elif (i_dock == i_actions+2):
                dock.setStretch(x=1, y=1)
                self.addDock(dock, "bottom")
            else:
                dock.setStretch(x=1, y=1)
                self.addDock(dock, "right", l_ordered_docks[i_dock-1])
        return w_actions

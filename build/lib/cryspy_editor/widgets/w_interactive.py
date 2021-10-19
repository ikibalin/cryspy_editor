"""Functions to create docks for dock-area."""
from PyQt5 import QtWidgets

from cryspy import Pd, RhoChi, Pd2d, TOF

def w_for_interaction(obj, parent=None) -> tuple:
    """Give tuple of docks for Dockarea."""
    widget = None
    if isinstance(obj, RhoChi):
        widget = interaction_rhochi(obj, parent)
    elif isinstance(obj, (Pd, Pd2d, TOF)):
        widget = interaction_experiment(obj, parent)
    return widget

def interaction_rhochi(obj: RhoChi, parent=None):
    """Dock for RhoChi object."""
    widget = None
    experiments = obj.experiments()
    flag_none = True
    for experiment in experiments:
        widget = QtWidgets.QWidget(parent)
        layout = QtWidgets.QVBoxLayout()
        widg_exp = interaction_experiment(experiment, widget)
        if widg_exp != None:
            layout.addWidget(widg_exp)
            flag_none = False
    if flag_none:
        del(widget)
        return None
    return widget

def interaction_experiment(obj, parent=None):
    widget = None
    if obj.is_attribute("chi2"):
        chi2 = obj.chi2
        widget = QtWidgets.QGroupBox(obj.data_name, parent)
        grid_layout = QtWidgets.QGridLayout()

        cb_sum = QtWidgets.QCheckBox("sum", widget)
        cb_sum.setCheckState(2*int(chi2.sum))
        cb_sum.stateChanged.connect(
            lambda x: setattr(chi2, "sum", bool(x/2)))
        grid_layout.addWidget(cb_sum, 0, 0, 1, 1)

        cb_diff = QtWidgets.QCheckBox("diff", widget)
        cb_diff.setCheckState(2*int(chi2.diff))
        cb_diff.stateChanged.connect(
            lambda x: setattr(chi2, "diff", bool(x/2)))
        grid_layout.addWidget(cb_diff, 1, 0, 1, 1)

        cb_up = QtWidgets.QCheckBox("up", widget)
        cb_up.setCheckState(2*int(chi2.up))
        cb_up.stateChanged.connect(
            lambda x: setattr(chi2, "up", bool(x/2)))
        grid_layout.addWidget(cb_up, 0, 1, 1, 1)

        cb_down = QtWidgets.QCheckBox("down", widget)
        cb_down.setCheckState(2*int(chi2.down))
        cb_down.stateChanged.connect(
            lambda x: setattr(chi2, "down", bool(x/2)))
        grid_layout.addWidget(cb_down, 1, 1, 1, 1)
        widget.setLayout(grid_layout)
    return widget








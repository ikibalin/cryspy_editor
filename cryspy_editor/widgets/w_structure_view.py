"""Tab with the 3D view of a crystal structure.

CrysPy makes the page (py3Dmol, ``get_structure_view_html``) and the
settings (``cryspy.StructureViewSettings``); this widget only shows the page
in a web view and builds the settings panel from the fields of the
dataclass, so new settings of CrysPy appear here without changes.
"""
import dataclasses
import os
import tempfile

from PyQt5 import QtCore, QtWidgets

try:  # must be imported before QApplication is created
    from PyQt5.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebEngineView = None

try:
    from cryspy import StructureViewSettings
except ImportError:  # CrysPy without the 3D view
    StructureViewSettings = None

# 3Dmol.js bundled with the editor: the view works without internet
F_JS = os.path.join(os.path.dirname(__file__), "js", "3Dmol-min.js")
# the page fills the web view, its size is not a setting here
HIDDEN_FIELDS = ("width", "height")


def has_structure_view(item) -> bool:
    """The item can be shown in 3D (any CrysPy class with the method)."""
    return (StructureViewSettings is not None and
            callable(getattr(type(item), "get_structure_view_html", None)))


class WStructureView(QtWidgets.QWidget):
    """Web view of the structure and a panel with its settings."""

    # the settings are kept when another crystal is selected
    settings = None

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        if WStructureView.settings is None:
            WStructureView.settings = StructureViewSettings()
        self.dir_tmp = tempfile.TemporaryDirectory(prefix="cryspy_editor_3d_")
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(300)
        self.timer.timeout.connect(self.redraw)

        self.w_view = None
        if QWebEngineView is None:
            layout = QtWidgets.QHBoxLayout(self)
            layout.addWidget(QtWidgets.QLabel(
                "The 3D view needs PyQtWebEngine: pip install PyQtWebEngine"))

    def showEvent(self, event):
        # the web view (OpenGL) is made only when the tab is opened
        if self.w_view is None and QWebEngineView is not None:
            self.make_view()
        super().showEvent(event)

    def make_view(self):
        layout = QtWidgets.QHBoxLayout(self)
        self.w_view = QWebEngineView(self)
        self.w_message = QtWidgets.QLabel(self)
        self.w_message.setWordWrap(True)
        self.w_message.hide()
        w_left = QtWidgets.QWidget(self)
        layout_left = QtWidgets.QVBoxLayout(w_left)
        layout_left.setContentsMargins(0, 0, 0, 0)
        layout_left.addWidget(self.w_message)
        layout_left.addWidget(self.w_view, 1)
        layout.addWidget(w_left, 1)
        layout.addWidget(self.make_settings_panel())
        self.redraw()

    def make_settings_panel(self) -> QtWidgets.QWidget:
        w_scroll = QtWidgets.QScrollArea(self)
        w_scroll.setWidgetResizable(True)
        w_panel = QtWidgets.QWidget(w_scroll)
        form = QtWidgets.QFormLayout(w_panel)
        settings = WStructureView.settings
        for field in dataclasses.fields(settings):
            if field.name in HIDDEN_FIELDS:
                continue
            widget = self.make_field_widget(field, getattr(settings, field.name))
            widget.setToolTip(field.metadata.get("description", ""))
            form.addRow(field.name.replace("_", " "), widget)
        w_scroll.setWidget(w_panel)
        w_scroll.setMaximumWidth(330)
        return w_scroll

    def make_field_widget(self, field, value) -> QtWidgets.QWidget:
        meta = field.metadata
        name = field.name
        if isinstance(value, bool):
            widget = QtWidgets.QCheckBox(self)
            widget.setChecked(value)
            widget.toggled.connect(lambda v, n=name: self.set_setting(n, bool(v)))
        elif isinstance(value, int):
            widget = QtWidgets.QSpinBox(self)
            widget.setRange(int(meta.get("min", 0)), int(meta.get("max", 1000)))
            widget.setSingleStep(int(meta.get("step", 1)))
            widget.setValue(value)
            widget.valueChanged.connect(lambda v, n=name: self.set_setting(n, int(v)))
        elif isinstance(value, float):
            widget = QtWidgets.QDoubleSpinBox(self)
            widget.setDecimals(2)
            widget.setRange(float(meta.get("min", 0.)), float(meta.get("max", 100.)))
            widget.setSingleStep(float(meta.get("step", 0.1)))
            widget.setValue(value)
            widget.valueChanged.connect(lambda v, n=name: self.set_setting(n, float(v)))
        else:
            widget = QtWidgets.QLineEdit(str(value), self)
            widget.editingFinished.connect(
                lambda w=widget, n=name: self.set_setting(n, w.text()))
        return widget

    def set_setting(self, name: str, value):
        WStructureView.settings = dataclasses.replace(
            WStructureView.settings, **{name: value})
        self.timer.start()

    def redraw(self):
        js = None
        if os.path.isfile(F_JS):
            js = QtCore.QUrl.fromLocalFile(F_JS).toString()
        try:
            html = self.item.get_structure_view_html(
                WStructureView.settings, js=js)
        except Exception as error:  # e.g. py3Dmol is not installed
            self.w_message.setText(f"The 3D view is not made: {error}")
            self.w_message.show()
            return
        self.w_message.hide()
        # a file, not setHtml: no 2 MB limit and the local script loads
        f_html = os.path.join(self.dir_tmp.name, "structure.html")
        with open(f_html, "w", encoding="utf-8") as fid:
            fid.write(html)
        self.w_view.load(QtCore.QUrl.fromLocalFile(f_html))

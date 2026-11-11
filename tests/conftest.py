"""Common fixtures: Qt without a display."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# no requests to GitHub for a new version from the tests
os.environ.setdefault("CRYSPY_EDITOR_NO_UPDATE_CHECK", "1")

import pytest
from PyQt5 import QtWidgets

try:  # the 3D view: QtWebEngine must be loaded before QApplication
    import PyQt5.QtWebEngineWidgets  # noqa: F401
except ImportError:
    pass


@pytest.fixture(autouse=True)
def settings_dir(tmp_path, monkeypatch):
    """Each test has its own empty settings folder."""
    from cryspy_editor import settings
    dir_settings = tmp_path / "settings"
    monkeypatch.setenv("CRYSPY_EDITOR_CONFIG_DIR", str(dir_settings))
    monkeypatch.setattr(settings, "F_OLD_SETUP_NPY", str(tmp_path / "no.npy"))
    monkeypatch.setattr(settings, "F_OLD_SETUP_INTERNAL",
                        str(tmp_path / "no.internal"))
    settings.reload_settings()
    yield dir_settings
    settings.reload_settings()


@pytest.fixture(scope="session")
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app


@pytest.fixture
def editor_window(qapp, monkeypatch, tmp_path):
    """Main window with a crystal (Ho2Ti2O7) opened; the 3D view without
    QtWebEngine."""
    import cryspy

    from cryspy_editor.ceditor import CMainWindow
    from cryspy_editor.widgets import w_structure_view

    class FakeWebView(QtWidgets.QWidget):
        def load(self, url):
            self.url = url

    monkeypatch.setattr(w_structure_view, "QWebEngineView", FakeWebView)
    monkeypatch.chdir(tmp_path)
    f_crystal = os.path.join(os.path.dirname(cryspy.__file__),
                             "procedure_simulation", "crystal_Ho2Ti2O7.rcif")
    f_name = tmp_path / "crystal.rcif"
    with open(f_crystal, "r") as fid:
        f_name.write_text("global_test\n" + fid.read())
    main_window = CMainWindow()
    main_window.d_setup["data_file_name"] = str(f_name)
    main_window.take_rcif_object_from_d_setup()
    yield main_window
    main_window.close()

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

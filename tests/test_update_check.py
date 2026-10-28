"""Check for a new version at startup (no network: GitHub is mocked)."""
import io
import json
import time

import pytest
from PyQt5 import QtWidgets

from cryspy_editor import settings, update_check


@pytest.mark.parametrize("text, t_version", [
    ("1.11.0", (1, 11)),
    ("v1.11.2", (1, 11, 2)),
    ("1.11.0+dev3", (1, 11)),
    ("1.12", (1, 12)),
    ("abc", ()),
])
def test_parse_version(text, t_version):
    assert update_check.parse_version(text) == t_version


@pytest.mark.parametrize("latest, installed, flag", [
    ("1.12.0", "1.11.0", True),
    ("1.11.1", "1.11.0", True),
    ("1.11.0", "1.11.0", False),
    ("1.11.0", "1.11.0+dev5", False),
    ("1.10.0", "1.11.0", False),
    ("1.12.0", "0.0.0", False),  # unknown installed version
    ("", "1.11.0", False),
])
def test_is_newer(latest, installed, flag):
    assert update_check.is_newer(latest, installed) is flag


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *argv):
        return False


def test_check_for_update(monkeypatch):
    answer = json.dumps({
        "tag_name": "9.0.0",
        "html_url": "https://github.com/ikibalin/cryspy_editor/releases/tag/9.0.0",
    }).encode()
    monkeypatch.setattr(update_check.urllib.request, "urlopen",
                        lambda *argv, **kwargs: FakeResponse(answer))
    d_release = update_check.check_for_update("1.11.0")
    assert d_release["version"] == "9.0.0"
    assert update_check.check_for_update("9.0.0") is None


def test_check_offline_is_silent(monkeypatch):
    def urlopen(*argv, **kwargs):
        raise OSError("no internet")
    monkeypatch.setattr(update_check.urllib.request, "urlopen", urlopen)
    assert update_check.check_for_update("1.0.0") is None


def test_message_has_download_page(monkeypatch):
    d_release = {"version": "9.0.0", "url": ""}
    text = update_check.form_message(d_release, "1.11.0")
    assert update_check.URL_DOWNLOAD_PAGE in text
    assert "pip install --upgrade" in text
    monkeypatch.setattr(update_check.sys, "frozen", True, raising=False)
    text = update_check.form_message(d_release, "1.11.0")
    assert update_check.URL_DOWNLOAD_PAGE in text
    assert "pip install" not in text


def test_default_setting_is_on():
    assert settings.take_settings()["check_for_updates"] is True


@pytest.fixture
def window(qapp, monkeypatch, tmp_path):
    from cryspy_editor.ceditor import CMainWindow
    monkeypatch.chdir(tmp_path)
    main_window = CMainWindow()
    yield main_window
    main_window.close()


def wait_for_check(qapp, window):
    for _ in range(100):
        qapp.processEvents()
        if not window.timer_update_check.isActive():
            return
        time.sleep(0.02)
    raise AssertionError("update check did not finish")


def test_menu_switches_check_off(window):
    assert window.action_check_updates.isChecked()
    window.action_check_updates.setChecked(False)
    assert settings.reload_settings()["check_for_updates"] is False


def test_dialog_at_startup(qapp, window, monkeypatch):
    monkeypatch.delenv("CRYSPY_EDITOR_NO_UPDATE_CHECK")
    monkeypatch.setattr(update_check, "check_for_update",
                        lambda version: {"version": "9.0.0", "url": ""})
    l_shown = []
    monkeypatch.setattr(window, "show_new_version",
                        lambda d_release, **kw: l_shown.append(d_release))
    window.start_update_check()
    wait_for_check(qapp, window)
    assert l_shown == [{"version": "9.0.0", "url": ""}]

    # a skipped version is not shown again
    window.d_setup["skipped_update_version"] = "9.0.0"
    window.start_update_check()
    wait_for_check(qapp, window)
    assert len(l_shown) == 1

    # switched off: no check at all
    window.d_setup["check_for_updates"] = False
    window.d_setup["skipped_update_version"] = ""
    window.start_update_check()
    wait_for_check(qapp, window)
    assert len(l_shown) == 1


def test_dialog_checkbox_switches_check_off(qapp, window, monkeypatch):
    def exec_box(box):
        box.checkBox().setChecked(True)
        for button in box.buttons():
            if button.text() == "Later":
                button.click()
        return 0
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", exec_box)
    window.show_new_version({"version": "9.0.0", "url": ""})
    assert window.action_check_updates.isChecked() is False
    assert settings.reload_settings()["check_for_updates"] is False

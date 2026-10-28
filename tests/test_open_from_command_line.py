"""Phase 1: opening a file from the command line, settings in JSON."""
import json
import os
import subprocess
import sys

import numpy
import pytest

from cryspy_editor import settings
from cryspy_editor.__main__ import parse_arguments

DIR_EXAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "examples")
F_EXAMPLE = os.path.join(DIR_EXAMPLES, "Fe3O4_5T_powder_1d", "main.rcif")


def test_parse_arguments():
    args, l_qt = parse_arguments(["file.rcif", "-platform", "offscreen"])
    assert args.file_name == "file.rcif"
    assert l_qt == ["-platform", "offscreen"]
    args, _ = parse_arguments([])
    assert args.file_name is None


def test_import_main_does_not_start_window():
    # importing must not open a window (it used to call main() on import)
    result = subprocess.run(
        [sys.executable, "-c", "import cryspy_editor.__main__"],
        capture_output=True, timeout=120)
    assert result.returncode == 0


def test_version_option():
    result = subprocess.run(
        [sys.executable, "-m", "cryspy_editor", "--version"],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0
    assert result.stdout.startswith("cryspy-editor")


def test_missing_file_is_reported():
    result = subprocess.run(
        [sys.executable, "-m", "cryspy_editor", "no_such_file.rcif"],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 2
    assert "not found" in result.stderr


def test_settings_saved_as_json(settings_dir):
    d_settings = settings.take_settings()
    d_settings["font_size"] = 12
    settings.add_recent_file("a.rcif")
    settings.add_recent_file("b.rcif")
    settings.add_recent_file("a.rcif")
    assert settings.save_settings()
    with open(settings_dir / "settings.json", encoding="utf-8") as fid:
        d_file = json.load(fid)
    assert d_file["font_size"] == 12
    assert [os.path.basename(f) for f in d_file["recent_files"]] == \
        ["a.rcif", "b.rcif"]
    assert settings.reload_settings()["font_size"] == 12


def test_recent_files_limited():
    for ind in range(15):
        settings.add_recent_file(f"{ind}.rcif")
    l_recent = settings.take_settings()["recent_files"]
    assert len(l_recent) == settings.N_RECENT_FILES
    assert os.path.basename(l_recent[0]) == "14.rcif"


def test_old_settings_are_moved(tmp_path, monkeypatch):
    f_npy = tmp_path / "setup.npy"
    numpy.save(f_npy, {"data_file_name": "/data/x.rcif",
                       "data_dir_name": "/data",
                       "llm_autoload": numpy.bool_(True)})
    f_internal = tmp_path / "setup.internal"
    f_internal.write_text("font_size:15\n", encoding="utf-8")
    monkeypatch.setattr(settings, "F_OLD_SETUP_NPY", str(f_npy))
    monkeypatch.setattr(settings, "F_OLD_SETUP_INTERNAL", str(f_internal))
    d_settings = settings.reload_settings()
    assert d_settings["data_file_name"] == "/data/x.rcif"
    assert d_settings["font_size"] == 15
    assert d_settings["recent_files"] == ["/data/x.rcif"]
    assert settings.save_settings()


def test_window_opens_given_file(qapp, tmp_path, monkeypatch):
    from cryspy_editor.ceditor import CMainWindow
    monkeypatch.chdir(tmp_path)
    window = CMainWindow(F_EXAMPLE)
    try:
        assert window.windowTitle() == "CrysPy Editor: main.rcif"
        assert len(window.rcif_object.items) > 0
        # opening does not change the working directory any more
        assert os.getcwd() == str(tmp_path)
        assert window.cthread.work_dir == os.path.dirname(F_EXAMPLE)
        assert settings.take_settings()["recent_files"][0] == F_EXAMPLE
        assert [a.text() for a in window.menu_recent.actions()] == [F_EXAMPLE]
    finally:
        window.close()


def test_window_without_file_is_empty(qapp):
    from cryspy_editor.ceditor import CMainWindow
    window = CMainWindow()
    try:
        assert len(window.rcif_object.items) == 0
        assert not window.menu_recent.isEnabled()
    finally:
        window.close()


def test_self_test_option():
    # the standalone builds run it in CI to check the bundled program
    result = subprocess.run(
        [sys.executable, "-m", "cryspy_editor", "--self-test"],
        capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "self-test passed" in result.stdout

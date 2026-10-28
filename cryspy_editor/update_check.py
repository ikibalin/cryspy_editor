"""Check at startup whether a newer CrysPy Editor is released on GitHub.

The check runs in a background thread and is silent when there is no
internet or GitHub does not answer. It is switched off by
Options -> "Check for new versions at startup" (setting
"check_for_updates") or by the environment variable
CRYSPY_EDITOR_NO_UPDATE_CHECK (used by tests and self-test).
"""
import json
import os
import re
import sys
import threading
import urllib.request

URL_LATEST_RELEASE = (
    "https://api.github.com/repos/ikibalin/cryspy_editor/releases/latest")
URL_DOWNLOAD_PAGE = "https://ikibalin.github.io/cryspy_editor/"
TIMEOUT = 5.  # seconds

PIP_UPGRADE_COMMAND = "pip install --upgrade cryspy_editor"


def is_check_disabled_by_environment() -> bool:
    return os.environ.get("CRYSPY_EDITOR_NO_UPDATE_CHECK", "") not in ("", "0")


def is_standalone() -> bool:
    """True inside the standalone program made by PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def parse_version(text: str) -> tuple:
    """'1.11.0', 'v1.11.0', '1.11.0+dev3' -> (1, 11, 0); () if no number.

    Only the release part is compared: a development build of 1.11.0 is
    not older than the release 1.11.0.
    """
    match = re.match(r"\s*v?(\d+(?:\.\d+)*)", str(text))
    if match is None:
        return ()
    l_number = [int(hh) for hh in match.group(1).split(".")]
    while len(l_number) > 1 and l_number[-1] == 0:
        l_number.pop()
    return tuple(l_number)


def is_newer(version_latest: str, version_installed: str) -> bool:
    t_latest = parse_version(version_latest)
    t_installed = parse_version(version_installed)
    if t_latest == () or t_installed in ((), (0,)):
        # unknown version (e.g. not installed package): do not disturb
        return False
    return t_latest > t_installed


def fetch_latest_release(timeout: float = TIMEOUT) -> dict:
    """{'version': '1.12.0', 'url': ...} of the latest published release.

    Drafts and pre-releases are not returned by GitHub here. Raises
    OSError or ValueError when GitHub cannot be reached.
    """
    request = urllib.request.Request(
        URL_LATEST_RELEASE,
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "cryspy_editor"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        d_release = json.loads(response.read().decode("utf-8"))
    version = str(d_release.get("tag_name", "")).strip()
    if version == "":
        raise ValueError("no tag_name in the answer of GitHub")
    return {"version": version.lstrip("v"),
            "url": d_release.get("html_url", "")}


def check_for_update(version_installed: str, timeout: float = TIMEOUT):
    """The latest release if it is newer than the installed version, else
    None. None also when GitHub cannot be reached (no internet)."""
    try:
        d_release = fetch_latest_release(timeout)
    except Exception:  # offline, proxy, rate limit, bad answer
        return None
    if is_newer(d_release["version"], version_installed):
        return d_release
    return None


class UpdateChecker:
    """Runs check_for_update in a daemon thread; the result is taken by
    the Qt main thread with take_result() (polled by a timer), so the
    thread never touches Qt objects and never delays closing."""

    def __init__(self, version_installed: str, function=None):
        self.version_installed = version_installed
        self.function = check_for_update if function is None else function
        self.flag_done = False
        self.result = None
        self.thread = None

    def start(self):
        self.thread = threading.Thread(
            target=self._run, name="cryspy_editor update check", daemon=True)
        self.thread.start()

    def _run(self):
        try:
            self.result = self.function(self.version_installed)
        except Exception:
            self.result = None
        self.flag_done = True

    def is_done(self) -> bool:
        return self.flag_done


def form_message(d_release: dict, version_installed: str) -> str:
    """Text of the dialog about a new version (HTML for QMessageBox)."""
    version = d_release["version"]
    url_notes = d_release.get("url", "")
    l_line = [
        f"<b>CrysPy Editor {version}</b> is available "
        f"(you have {version_installed}).",
        "",
    ]
    if is_standalone():
        l_line.append(
            f"Download the new program from the "
            f"<a href='{URL_DOWNLOAD_PAGE}'>download page</a>.")
    else:
        l_line.append(
            f"Update it with<br><code>{PIP_UPGRADE_COMMAND}</code><br>"
            f"or download the standalone program from the "
            f"<a href='{URL_DOWNLOAD_PAGE}'>download page</a>.")
    if url_notes != "":
        l_line.append("")
        l_line.append(f"<a href='{url_notes}'>What is new</a>")
    return "<br>".join(l_line)

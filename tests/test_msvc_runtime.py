"""llama-cpp-python after PyQt5 on Windows: the old msvcp140.dll of PyQt5
crashed llama.dll ('access violation reading 0x0') unless the program loads
the C++ runtime of the system first (__main__.preload_msvc_runtime)."""
import subprocess
import sys

import pytest

AFTER_QT = "import PyQt5.QtCore, llama_cpp; llama_cpp.llama_backend_init()"


def test_preload_does_nothing_elsewhere():
    from cryspy_editor.__main__ import preload_msvc_runtime
    preload_msvc_runtime()  # no error on any system


@pytest.mark.skipif(sys.platform != "win32", reason="DLLs of Windows")
def test_llama_after_pyqt5():
    pytest.importorskip("llama_cpp")
    pytest.importorskip("PyQt5")
    code = "from cryspy_editor.__main__ import preload_msvc_runtime; preload_msvc_runtime(); " + AFTER_QT
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stderr

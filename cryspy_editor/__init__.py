"""
CrysPy Editor
=============

Graphical editor for the CrysPy library.
"""
from importlib.metadata import PackageNotFoundError, version as _version

try:
    __version__ = _version("cryspy_editor")
except PackageNotFoundError:
    __version__ = "0.0.0"
name = "cryspy_editor"

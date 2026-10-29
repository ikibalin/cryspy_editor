# PyInstaller spec of the standalone CrysPy Editor (no Python needed).
#
#   pip install . pyinstaller [llama-cpp-python]
#   pyinstaller packaging/cryspy_editor.spec
#
# Result: dist/CrysPy Editor/ (Windows, Linux) or dist/CrysPy Editor.app (macOS).
# llama-cpp-python is bundled when it is installed; without it the AI
# assistant says that the model backend is missing (Ollama still works).
import os
import sys

from PyInstaller.utils.hooks import collect_all, copy_metadata

DIR_SPEC = os.path.abspath(SPECPATH)
DIR_ROOT = os.path.dirname(DIR_SPEC)
APP_NAME = "CrysPy Editor"

datas, binaries, hiddenimports = [], [], []
# data files (.dat, help pages, icons, examples) and lazily imported modules
# py3Dmol and ipywidgets are imported lazily by cryspy (3D view)
for package in ("cryspy", "cryspy_editor", "pycifstar", "py3Dmol"):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h
# __version__ is read by importlib.metadata
datas += copy_metadata("cryspy") + copy_metadata("cryspy_editor")

try:
    import llama_cpp  # noqa: F401
    d, b, h = collect_all("llama_cpp")
    datas += d + copy_metadata("llama_cpp_python")
    binaries += b
    hiddenimports += h
except ImportError:
    print("llama-cpp-python is not installed: build without local GGUF models")

if sys.platform == "win32":
    icon = os.path.join(DIR_ROOT, "logo_icon.ico")
elif sys.platform == "darwin":
    # square .icns made from the logo (Pillow comes with matplotlib)
    from PIL import Image

    image = Image.open(os.path.join(DIR_ROOT, "cryspy_editor", "f_icon", "logo.png"))
    size = max(image.size)
    square = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    square.paste(image, ((size - image.size[0]) // 2, (size - image.size[1]) // 2))
    icon = os.path.join(workpath, "logo.icns")
    square.resize((1024, 1024)).save(icon)
else:
    icon = None

a = Analysis(
    [os.path.join(DIR_SPEC, "run_cryspy_editor.py")],
    pathex=[DIR_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    runtime_hooks=[os.path.join(DIR_SPEC, "rthook_cryspy_packages.py")],
    excludes=["tkinter", "PySide2", "PySide6", "PyQt6", "IPython", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    console=False,
    icon=icon,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name=APP_NAME,
)

if sys.platform == "darwin":
    from cryspy_editor import __version__

    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=icon,
        bundle_identifier="fr.ill.cryspy-editor",
        version=__version__.split("+")[0],
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleDocumentTypes": [{
                "CFBundleTypeName": "CrysPy rcif file",
                "CFBundleTypeExtensions": ["rcif"],
                "CFBundleTypeRole": "Editor",
            }],
        },
    )

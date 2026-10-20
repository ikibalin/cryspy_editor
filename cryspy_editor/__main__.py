"""Start CrysPy Editor: cryspy-editor [file.rcif] or python -m cryspy_editor [file.rcif]."""
import argparse
import os
import sys

from cryspy_editor import __version__


def parse_arguments(l_argument=None):
    parser = argparse.ArgumentParser(
        prog="cryspy-editor",
        description="Editor of CrysPy (.rcif) files.")
    parser.add_argument(
        "file_name", nargs="?", default=None,
        help="file to open; without it the last used file is opened")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}")
    # Qt options such as -platform are passed to QApplication
    args, l_qt_argument = parser.parse_known_args(l_argument)
    return args, l_qt_argument


def main(l_argument=None):
    """Make main window."""
    if l_argument is None:
        l_argument = sys.argv[1:]
    args, l_qt_argument = parse_arguments(l_argument)
    file_name = args.file_name
    if file_name is not None:
        file_name = os.path.abspath(file_name)
        if not os.path.isfile(file_name):
            print(f"File '{file_name}' is not found.", file=sys.stderr)
            sys.exit(2)

    from PyQt5 import QtGui, QtWidgets
    from cryspy_editor.ceditor import CMainWindow

    try:  # icon in the Windows task bar
        import ctypes
        myappid = 'ikibalin.llb.cryspy.editor.1'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except (ImportError, AttributeError, OSError):
        pass

    app = QtWidgets.QApplication(sys.argv[:1] + l_qt_argument)
    app.setStartDragDistance(100)

    f_icon = os.path.join(os.path.dirname(__file__), "f_icon", "logo.png")
    app.setWindowIcon(QtGui.QIcon(f_icon))

    main_window = CMainWindow(file_name)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

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
    parser.add_argument(
        "--self-test", action="store_true",
        help="check that CrysPy, Qt and the AI backend work, then exit")
    # Qt options such as -platform are passed to QApplication
    args, l_qt_argument = parser.parse_known_args(l_argument)
    return args, l_qt_argument


def self_test() -> int:
    """Check the installation (used for the standalone builds); 0 if fine."""
    import cryspy

    print(f"CrysPy Editor {__version__}, CrysPy {cryspy.__version__}")
    dir_simulation = os.path.join(
        os.path.dirname(cryspy.__file__), "procedure_simulation")
    l_text = []
    for f_name in ("crystal_Ho2Ti2O7.rcif", "diffrn_sc.rcif"):
        with open(os.path.join(dir_simulation, f_name), "r") as fid:
            l_text.append(fid.read())
    obj_global = cryspy.str_to_globaln("global_test\n" + "\n".join(l_text))
    d_out = cryspy.rhochi_no_refinement(obj_global)
    print(f"rhochi_no_refinement: chi_sq = {d_out['chi_sq']:.2f}")
    print(f"help topics: {len(cryspy.help_topics())}")

    from PyQt5 import QtWidgets
    from cryspy_editor.ceditor import CMainWindow
    from cryspy_editor.widgets import assistant

    print(f"llama-cpp-python: {assistant.flag_llama_cpp}")
    if os.environ.get("CRYSPY_EDITOR_REQUIRE_AI") and not assistant.flag_llama_cpp:
        print("self-test failed: llama-cpp-python is not available")
        return 1
    os.environ["CRYSPY_EDITOR_NO_UPDATE_CHECK"] = "1"  # no dialog, no network
    app = QtWidgets.QApplication(sys.argv[:1])
    main_window = CMainWindow()
    main_window.close()
    app.processEvents()
    print("self-test passed")
    return 0


def main(l_argument=None):
    """Make main window."""
    if l_argument is None:
        l_argument = sys.argv[1:]
    args, l_qt_argument = parse_arguments(l_argument)
    if args.self_test:
        sys.exit(self_test())
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

"""Doc string."""
import os
import os.path
import sys

from PyQt5 import QtWidgets

from cryspy_editor.ceditor import CMainWindow
import PyQt5.QtGui as QtGui
# from PyQt5.QtWinExtras import QWinTaskbarButton,QWinTaskbarProgress

def main():
    """Make main window."""

    try: # for windows
        import ctypes
        myappid = 'ikibalin.llb.cryspy.editor.1' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        pass
    
    l_arg = sys.argv
    app = QtWidgets.QApplication(l_arg)
    app.setStartDragDistance(100)

    f_icon = os.path.join(os.path.dirname(__file__), "f_icon", "logo.png")
    q_icon = QtGui.QIcon(f_icon)
    app.setWindowIcon(q_icon)

    main_window = CMainWindow()
    # sys.stdout = main_window
    # sys.stderr = main_window

    # main_window.setWindowIcon(q_icon)
    # main_window.taskbar_button = QWinTaskbarButton()
    # main_window.taskbar_button.setOverlayIcon(q_icon)

    sys.exit(app.exec_())

main()

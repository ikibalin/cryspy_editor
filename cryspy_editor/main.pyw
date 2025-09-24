"""Doc string."""
import os
import os.path
import sys

from PyQt5 import QtWidgets

from cryspy_editor.ceditor import CMainWindow
import PyQt5.QtGui as QtGui
# from PyQt5.QtWinExtras import QWinTaskbarButton,QWinTaskbarProgress


try: # for windows
    import ctypes
    myappid = 'ikibalin.llb.cryspy.editor.1' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:
    pass

if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    app.setStartDragDistance(100)
    f_icon = os.path.join(os.path.dirname(__file__), "f_icon", "logo.png")
    q_icon = QtGui.QIcon(f_icon)
    app.setWindowIcon(q_icon)
    app.setStyle("Windows")


    main_window = CMainWindow()
    main_window.show()


    sys.exit(app.exec_())



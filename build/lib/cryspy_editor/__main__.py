"""Doc string."""
import sys

from cryspy_editor.main_window import main_w

l_argv = sys.argv
flag = True

print("Programm 'cryspy_editor'.\n")
if flag:
    main_w(l_argv)
else:
    pass
print("That's all")

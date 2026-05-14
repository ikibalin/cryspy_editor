
from typing import Callable, NoReturn
from PyQt5 import QtWidgets, QtCore, QtGui
import cryspy_editor.widgets.ui_setting as ui_setting
import matplotlib.pyplot as plt
from cryspy_editor.widgets.colors import L_COLOR, transform_color
from cryspy_editor.widgets.function_table_to_ascii import transform_d_np_table_to_comments, transform_d_np_table_to_inline, transform_d_np_table_to_table, transform_d_np_table_to_expression

from cryspy_editor.widgets.function_ascii_to_table import transform_lines_to_d_np_table
from cryspy_editor.widgets.function_dictionary import get_d_names_inline, get_d_names_table, get_d_digit_number
from cryspy_editor.widgets.function_table_operation import redefine_inline_parameters, xy_to_plot, L_ACTION_NAME
import os
import random
DIR_BASE = os.path.dirname(__file__)

DIR_EXAMPLES = os.path.join(DIR_BASE, "examples")
WORDS = ["generate_hkl sthovl 0.1 1.", "generate_hkl 2Theta 5 140", "cell : ", "H K L ",
         "calc sthovl", "calc 2Theta"]
WORDS.extend(L_ACTION_NAME)

WORDS.extend([f"{_} : " for _ in get_d_names_inline().keys() if len(_) > 2])
WORDS.extend([f"{_} " for _ in get_d_names_table().keys() if len(_) > 2])
WORDS = set(WORDS)

S_COMMENT = ui_setting.get_comment_character()

def take_intro():
    S_INTRO = ""
    f_intro = os.path.join(DIR_BASE, "intro.dat")

    # f_last_build = os.path.join(DIR_BASE, "last_build.dat")
    # if os.path.isfile(f_last_build):
    #     with open(f_last_build, 'r') as fid:
    #         s_time = fid.read().strip()
    # else:
    #     s_time = "Under development"

    if os.path.isfile(f_intro):
        with open(f_intro, 'r') as fid:
            l_content = fid.readlines()
        # l_content.insert(1, f"{S_COMMENT:}                         ({s_time:}) \n")
        S_INTRO = "".join([line.replace("#", S_COMMENT) for line in l_content])
        l_file = os.listdir(DIR_EXAMPLES)
        file = os.path.join(DIR_EXAMPLES, l_file[random.randint(0, len(l_file) - 1)])
        if os.path.isfile(file):
            S_INTRO += "\n\n" + S_COMMENT + " EXAMPLE: " + os.path.basename(file) + "\n\n"
            with open(file, 'r') as fid:
                S_INTRO += fid.read()
    return S_INTRO

class WTextEdit(QtWidgets.QTextEdit):
    """WFunction class."""

    def __init__(self, parent=None):
        super(WTextEdit, self).__init__(parent)

        self.setAcceptRichText(True)
        self.setSizePolicy(
                QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                      QtWidgets.QSizePolicy.Expanding))
        font_size = ui_setting.get_font_size()
        self.setFont(QtGui.QFont("Courier", font_size, QtGui.QFont.Normal))
        self.setAlignment(QtCore.Qt.AlignTop)


        self.completer = QtWidgets.QCompleter(WORDS, self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.completer.activated.connect(self.insertCompletion)

        # self.setStyleSheet("background-color:white;")
    
        S_INTRO = take_intro()
        self.setPlaceholderText(S_INTRO)

    def insertCompletion(self, completion):
        cursor = self.textCursor()
        cursor.movePosition(cursor.StartOfWord, cursor.KeepAnchor)
        cursor.insertText(completion)
        self.setTextCursor(cursor)


    def textUnderCursor(self):
        cursor = self.textCursor()
        cursor.select(cursor.WordUnderCursor)
        return cursor.selectedText()
    
    def show_replace_dialog(self):
        cursor = self.te_table.textCursor()
        s_val = cursor.selectedText().split("\u2029")[0].strip()
        dialog = ReplaceDialog(self.te_table, s_val)
        dialog.exec_()

    def upload_font_size(self):
        current_font = self.font()
        font_size = ui_setting.get_font_size()
        current_font.setPointSize(font_size)
        self.setFont(current_font)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Return and event.modifiers() == QtCore.Qt.ControlModifier:
            S_INTRO = take_intro()
            self.setPlaceholderText(S_INTRO)
            self.convert_to_np_table()
        elif self.completer.popup().isVisible() and event.key() == QtCore.Qt.Key_Tab:
            completion = self.completer.currentCompletion()
            if completion:
                self.insertCompletion(completion)
            return
        else:
            super().keyPressEvent(event)      
        completion_prefix = self.textUnderCursor()
        if len(completion_prefix) < 1:
            self.completer.popup().hide()
            return

        self.completer.setCompletionPrefix(completion_prefix)
        self.completer.popup().setCurrentIndex(self.completer.completionModel().index(0, 0))
        self.completer.complete()

    def wheelEvent(self, e):
        if e is None:
            pass
        elif e.modifiers() == QtCore.Qt.ControlModifier:
            delta = e.angleDelta().y()
            current_font = self.font()
            current_size = current_font.pointSize()
            if delta > 0:
                new_size = current_size + 1
            else:
                new_size = current_size - 1
            if new_size < 5 or new_size > 60:
                return
            current_font.setPointSize(new_size)
            self.setFont(current_font)
            ui_setting.save_font_size(new_size)
            ui_setting.write_to_setup_file()
        else:
            super().wheelEvent(e)

    def convert_to_np_table(self):
        #self.write_to_history()
        s_text = self.toPlainText()
        if s_text == "":
            s_text = self.placeholderText()
        l_content = s_text.split("\n")

        try:
            D_NP_Table = transform_lines_to_d_np_table(l_content)
            # Renew all comments to avoid old comments
            D_NP_Table[" comments"] = []
            redefine_inline_parameters(D_NP_Table)
        except Exception as e:
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setWindowTitle("ASCII-Table")
            msgbox.setText("Error during converting text to table\n" + str(e))
            msgbox.exec()
            return
        
        self.D_NP_TABLE = D_NP_Table

        try:
            l_comment = transform_d_np_table_to_comments(self.D_NP_TABLE)
            l_inline = transform_d_np_table_to_inline(self.D_NP_TABLE)
            l_expression = transform_d_np_table_to_expression(self.D_NP_TABLE)
            l_table = transform_d_np_table_to_table(self.D_NP_TABLE)
        except Exception as e:
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setWindowTitle("ASCII-Table")
            msgbox.setText("Error during converting table to text\n\n" + str(e))
            msgbox.exec()
            return 
        
        self.clear()
        self.setTextBackgroundColor(transform_color(L_COLOR[0]))
        self.setTextColor(transform_color(L_COLOR[-1]))
        
        S_COMMENT = ui_setting.get_comment_character()
        # comments
        q_color = transform_color(L_COLOR[0])
        self.setTextBackgroundColor(q_color)
        for line in l_comment:
            self.append(line)
        self.append("")

        # inline
        if len(l_inline) > 0:
            self.append(S_COMMENT + " PARAMETERS\n")
        bold_format = QtGui.QTextCharFormat()
        
        normal_format = QtGui.QTextCharFormat()
        for line in l_inline:
            l_hh = line.split(":")

            cursor = self.textCursor()
            bold_format.setFontWeight(QtGui.QFont.Bold)
            cursor.insertText(l_hh[0].strip().rjust(15) + " : ", bold_format)
            bold_format.setFontWeight(3)
            cursor.insertText(l_hh[1].strip()+"\n", bold_format)
            

        # expressions
        q_color = transform_color(L_COLOR[0])
        self.setTextBackgroundColor(q_color)
        self.setTextColor(transform_color(L_COLOR[-1]))
        if len(l_expression) > 0:
            self.append(S_COMMENT + " FUNCTIONS\n")
        for line in l_expression:
            cursor = self.textCursor()
            bold_format.setFontWeight(QtGui.QFont.Bold)
            l_hh = line.strip().split() 
            if l_hh[0].lower() in L_ACTION_NAME:
                cursor.insertText(l_hh[0].strip().rjust(15) + " ", bold_format)
                bold_format.setFontWeight(3)
                cursor.insertText(" ".join(l_hh[1:]).strip()+"\n", bold_format)
                continue

            l_hh = line.split("=")
            if len(l_hh) == 2:
                cursor.insertText(l_hh[0].strip().rjust(15) + " = ", bold_format)
                bold_format.setFontWeight(3)
                cursor.insertText(l_hh[1].strip()+"\n", bold_format)

        # table
        if len(l_table) == 0:
            return
        q_color = transform_color(L_COLOR[1])
        self.setTextBackgroundColor(q_color)
        self.append(l_table[0])

        l_table_colors = self.D_NP_TABLE[" table_colors"]
        if len(l_table[1:]) != len(l_table_colors):
            self.D_NP_TABLE[" table_colors"] = [transform_color(L_COLOR[0]) for _ in l_table[1:]]
            l_table_colors = self.D_NP_TABLE[" table_colors"]
        if len(l_table) == 1:
            return 
        for line, q_color in zip(l_table[1:], l_table_colors):
            self.setTextBackgroundColor(q_color)
            self.append(line)
        self.moveCursor(QtGui.QTextCursor.Start)

        self.plot()

    def plot(self):
        d_val = xy_to_plot(self.D_NP_TABLE)
        if d_val["name_x"] == "":
            return
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot(d_val["x"], d_val["y"], "ok")
        ax.set_xlabel(d_val["name_x"])
        ax.set_ylabel(d_val["name_y"])
        fig.show()    



class ReplaceDialog(QtWidgets.QDialog):
    def __init__(self, text_edit, s_replce:str=""):
        super().__init__()
        self.text_edit = text_edit
        self.init_ui(s_replce=s_replce)

    def init_ui(self, s_replce:str=""):
        self.setWindowTitle('Replace Text')
        layout = QtWidgets.QVBoxLayout()

        self.find_label = QtWidgets.QLabel('Find:')
        self.find_input = QtWidgets.QLineEdit()
        self.find_input.setText(s_replce)
        self.replace_label = QtWidgets.QLabel('Replace with:')
        self.replace_input = QtWidgets.QLineEdit()
        self.replace_button = QtWidgets.QPushButton('Replace')

        layout.addWidget(self.find_label)
        layout.addWidget(self.find_input)
        layout.addWidget(self.replace_label)
        layout.addWidget(self.replace_input)
        layout.addWidget(self.replace_button)

        self.setLayout(layout)

        self.replace_button.clicked.connect(self.replace_text)

    def replace_text(self):
        find_text = self.find_input.text()
        replace_text = self.replace_input.text()
        text = self.text_edit.toPlainText()
        new_text = text.replace(find_text, replace_text)
        
        self.text_edit.setTextBackgroundColor(transform_color(L_COLOR[0]))
        self.text_edit.setTextColor(transform_color(L_COLOR[-1]))
        self.text_edit.setPlainText(new_text)
        self.close()

"""WEditCif class."""
import re
from typing import Callable, NoReturn, Optional
from PyQt5 import QtWidgets, QtCore, QtGui
import cryspy
import cryspy_editor.widgets.ui_setting as ui_setting


def normalize_tag(tag: str) -> str:
    return tag.strip().lower().replace(".", "_")


def find_tag_of_token(lines: list, ind_line: int, ind_token: int) -> Optional[str]:
    """CIF tag of the token ind_token of the line ind_line: the first token
    of a line "_tag value", or the column of a loop_ row (one row a line)."""
    tokens = lines[ind_line].split()
    if tokens[0].startswith("_"):
        return tokens[0] if ind_token == 1 and len(tokens) == 2 else None
    l_tag = []
    for line in reversed(lines[:ind_line]):
        line = line.strip()
        if line.startswith("_"):
            l_tag.insert(0, line.split()[0])
        elif line.lower() == "loop_":
            break
        elif l_tag:  # values before the tags: not a loop
            return None
    if len(l_tag) != len(tokens):
        return None
    return l_tag[ind_token]


def switch_value(token: str, choices) -> str:
    """Next allowed value of a text value (Ciso -> Cani -> Ciso), quoted
    when it has spaces."""
    new_value = cryspy.next_value_choice(choices, token)
    if " " in new_value:
        return f"'{new_value:}'"
    return new_value


def switch_value_in_text(text: str, position: int, value_choices: dict):
    """(new_text, start, end, new_token) for a double click at position, or
    None if there is nothing to change there.

    A text value with allowed values (value_choices: CIF tag -> values)
    gets the next allowed value. Refinement is set in the window
    Parameters, so a double click on a number selects it as usual."""
    lines = text.split("\n")
    ind_start_line = 0
    for ind_line, line in enumerate(lines):
        if position <= ind_start_line + len(line):
            break
        ind_start_line += len(line) + 1
    else:
        return None
    pos = position - ind_start_line
    l_span = [m.span() for m in re.finditer(r"\S+", line)]
    for ind_token, (start, end) in enumerate(l_span):
        if start <= pos <= end:
            break
    else:
        return None
    token = line[start:end]
    tag = find_tag_of_token(lines, ind_line, ind_token)
    if tag is None:
        return None
    tag = normalize_tag(tag)
    if not value_choices or tag not in value_choices:
        return None
    new_token = switch_value(token, value_choices[tag])
    start += ind_start_line
    end += ind_start_line
    return text[:start] + new_token + text[end:], start, end, new_token


def take_value_choices(item) -> dict:
    """CIF tag -> allowed values of the text parameters of an ItemN or
    LoopN, from the definition of its class in CrysPy (any class)."""
    return cryspy.take_value_choices(item)


class WEditCif(QtWidgets.QTextEdit):
    """WFunction class."""

    def __init__(self, text: str, rewrite_item: Callable, parent=None, text_placeholder:str="", s_info:str="", value_choices: dict = None):
        super(WEditCif, self).__init__(parent)
        # double click on a value of these tags gives the next allowed value
        self.value_choices = value_choices if value_choices else {}

        self.setAcceptRichText(True)
        self.setSizePolicy(
                QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                      QtWidgets.QSizePolicy.Expanding))
        font_size = ui_setting.get_font_size()
        self.setFont(QtGui.QFont("Courier", font_size, QtGui.QFont.Normal))

        self.setAlignment(QtCore.Qt.AlignTop)
        self.setPlaceholderText(s_info+"\n\n"+text_placeholder)
        # self.setStyleSheet("background-color:white;")
        self.setText(text)
        self.text_changed = False
        self.textChanged.connect(lambda : setattr(self, "text_changed", True))
        self.rewrite_item = rewrite_item

    def mouseDoubleClickEvent(self, event):
        """A double click on a text value with allowed values (e.g.
        chi_type: Ciso, Cani) puts the next allowed value."""
        cursor = self.cursorForPosition(event.pos())
        result = switch_value_in_text(
            self.toPlainText(), cursor.position(), self.value_choices)
        if result is None:
            super().mouseDoubleClickEvent(event)
            return
        _, start, end, new_token = result
        cursor.setPosition(start)
        cursor.setPosition(end, QtGui.QTextCursor.KeepAnchor)
        cursor.insertText(new_token)  # one step of Undo, sets text_changed
        cursor.setPosition(start + len(new_token))
        self.setTextCursor(cursor)
        event.accept()

    def focusOutEvent(self, event):
        """Submit changes just before focusing out."""
        QtWidgets.QTextEdit.focusOutEvent(self, event)
        self.rewrite_item_by_printed_text()

    def rewrite_item_by_printed_text(self):
        if self.text_changed:
            s_text = self.toPlainText()
            self.rewrite_item(s_text)
            self.text_changed = False

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
            current_font.setPointSize(new_size)
            # font = QtGui.QFont("Courier New")
            # font.setPointSize(new_size)
            ui_setting.save_font_size(new_size)
            ui_setting.write_to_setup_file()
            self.setFont(current_font)
            # event.accept()
        else:
            super().wheelEvent(e)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.exec_(event.globalPos())
        event.accept()


        
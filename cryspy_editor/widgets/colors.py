from PyQt5 import QtGui, QtWidgets

L_COLOR = [
    QtGui.QColor(255, 255, 255), 
    QtGui.QColor(163, 206, 220, 170),  
    QtGui.QColor(142, 241, 142, 170),
    QtGui.QColor(230, 118, 118, 170), 
    QtGui.QColor(245, 245, 214, 170),
    QtGui.QColor(220, 220, 240, 170), 
    QtGui.QColor(214, 245, 245, 170),
    QtGui.QColor(245, 208, 175, 170), 
    QtGui.QColor(245, 218, 215, 170),
    QtGui.QColor(0, 0, 0, 255), ]

L_COLOR_TABLE = [
        QtGui.QColor(0, 0, 83, 0),
        QtGui.QColor(0, 0, 83, 10),
]

def is_dark_mode(): 
    palette = QtWidgets.QApplication.palette() 
    bg = palette.window().color() 
    # Dark mode if background is darker than mid‑gray 
    return bg.lightness() < 128

def transform_color(q_color):
    q_color_out = QtGui.QColor(q_color)  # Create a copy
    if is_dark_mode():
        q_color_out.setRed(255 - q_color.red())
        q_color_out.setGreen(255 - q_color.green())
        q_color_out.setBlue(255 - q_color.blue())
    return q_color_out

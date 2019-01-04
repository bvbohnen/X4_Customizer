# Misc functions.

from functools import lru_cache
from PyQt5 import QtWidgets, QtCore, QtGui

# Icon images:
# http://doc.qt.io/qt-5/qstyle.html#StandardPixmap-enum
# https://joekuan.wordpress.com/2015/09/23/list-of-qt-icons/
def Set_Icon(widget, icon_name):
    '''
    Applies a QIcon object matching the given name to the given widget.
    On error, quietly skips the icon application.

    * widget
        - Widget to apply to; should have a setIcon method or
          a setWindowIcon method.
    * icon_name
        - String, name of the icon.
        - Example useful names: 'SP_DirIcon','SP_FileIcon'
    '''
    # Returns if not a supported widget.
    method = getattr(widget, 'setIcon', None)
    if method == None:
        method = getattr(widget, 'setWindowIcon', None)
    if method == None:
        return

    # Start with a code lookup from the enum.
    icon_code = getattr(QtWidgets.QStyle, icon_name)
    # Return if not found.
    if icon_code == None:
        return
    
    # Reference the main application for the current style.
    # Do a delayed import, added when multiprocessing started
    # complaining about a possible import loop.
    from .. import Main_Window
    # Convert from code to an icon for the current style.
    icon = Main_Window.qt_application.style().standardIcon(icon_code)
    # Return if None (assuming that can happen.
    if icon == None:
        return

    # Finally, apply the icon.
    method(icon)
    return


# Cache this, just because.
@lru_cache(maxsize = 32)
def Get_Color_Brush(color):
    '''
    Returns a QBrush set up for the given color, and a solid pattern.
    Color may be a tuple of (r,g,b) or a supported name,
    as found at https://www.december.com/html/spec/colorsvg.html
    '''
    brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
    brush.setColor(QtGui.QColor(color))
    return brush


def Set_Foreground_Color(widget, color):
    '''
    Sets the foreground (text) color of the widget.
    The widget should have a setForeground method, else this
    will return early.
    '''
    if not hasattr(widget, 'setForeground'):
        return
    widget.setForeground(Get_Color_Brush(color))
    return


def Set_Background_Color(widget, color):
    '''
    Sets the background (text) color of the widget.
    The widget should have a setBackground method, else this
    will return early.
    '''
    if not hasattr(widget, 'setBackground'):
        return
    widget.setBackground(Get_Color_Brush(color))
    return

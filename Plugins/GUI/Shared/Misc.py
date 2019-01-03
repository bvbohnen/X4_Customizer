# Misc functions.
from PyQt5 import QtWidgets
# Reference the main application for the current style.
from .. import Main_Window

# Icon images:
# http://doc.qt.io/qt-5/qstyle.html#StandardPixmap-enum
# https://joekuan.wordpress.com/2015/09/23/list-of-qt-icons/
def Set_Icon(widget, icon_name):
    '''
    Applies a QIcon object matching the given name to the given widget.
    On error, quietly skips the icon application.

    * widget
        - Widget to apply to; should have a setIcon method.
    * icon_name
        - String, name of the icon.
        - Example useful names: 'SP_DirIcon','SP_FileIcon'
    '''
    # Returns if not a supported widget.
    if not hasattr(widget, 'setIcon'):
        return

    # Start with a code lookup from the enum.
    icon_code = getattr(QtWidgets.QStyle, icon_name)
    # Return if not found.
    if icon_code == None:
        return

    # Convert from code to an icon for the current style.
    icon = Main_Window.qt_application.style().standardIcon(icon_code)
    # Return if None (assuming that can happen.
    if icon == None:
        return

    # Finally, apply the icon.
    widget.setIcon(icon)
    return
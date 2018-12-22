'''
A limited GUI for the X4 Customizer.
Uses QT5.
To reduce dependency on the massive package for users just using
the old style, do a test for the package and disable the other
imports if it is not available.
No other module should make references into this subpackage,
only to the top level.
'''
try:
    import PyQt5
    _pyqt_found = True
except Exception:
    _pyqt_found = False

    
def Start_GUI():
    '''
    Start up the GUI using PyQt and loading the gui.ui file.
    If the pyqt import failed, this will return early.
    '''
    if not _pyqt_found:
        print('PyQt5 not found; Gui is disabled.')
        return

    from PyQt5 import QtWidgets
    # Create a new Qt gui object.
    qt_app = QtWidgets.QApplication([])

    # Create the custom gui window itself, and set it to be shown.
    # Presumably this will get attached automatically to the 
    #  QApplication object.
    from . import Main_Window
    window = Main_Window.GUI_Main_Window()

    # Launch the QApplication; this will halt execution until the gui exits.
    return_value = qt_app.exec()

    # There is no post-gui cleanup for now, so just return.
    return return_value


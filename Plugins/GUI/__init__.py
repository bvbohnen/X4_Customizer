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
    Start up the GUI using PyQt and loading the .ui files.
    If the pyqt import failed, this will return early.
    '''
    if not _pyqt_found:
        print('PyQt5 not found; Gui is disabled.')
        return
    from .Main_Window import Start_GUI
    return Start_GUI()

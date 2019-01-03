
# TODO: maybe move some functions to here from Widget_Settings.

from pathlib import Path

from PyQt5.uic import loadUiType
from PyQt5 import QtWidgets, QtCore, QtGui

from Framework import Settings
from ..Shared import Tab_Page_Widget

# Load the .ui file into a reuseable base class.
# This will return the designer generated class ("form"), and
# the Qt base class it is based on (QWidget in this case).
# http://pyqt.sourceforge.net/Docs/PyQt5/designer.html
gui_file = Path(__file__).parents[1] / 'x4c_gui_settings_tab.ui'
generated_class, qt_base_class = loadUiType(str(gui_file))


class Settings_Window(Tab_Page_Widget, generated_class):
    '''
    Window used for editing tool settings.
    Intended to be used just once.

    Widget names:
    * hsplitter
    * widget_settings
    * widget_settings_doc

    Attributes:
    * window
      - The parent main window holding this tab.
    '''
    def __init__(self, parent, window):
        super().__init__(parent, window)
                
        # Set up initial documentation for settings.
        self.widget_settings_doc.setPlainText(Settings.__doc__)
        
        # Attach the main window to the settings widget.
        self.widget_settings.window = window
                
        # Init the splitter to 1:1.
        self.hsplitter.setSizes([1000,1000])
        return
    

    def Save(self):
        # Save the gui version of settings.
        self.widget_settings.Save()
        return
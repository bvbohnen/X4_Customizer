'''
Top level of the GUI.

Notes:
- Layout made with Qt designer.
- Widgets organized using custom classes.
    In Designer, promote a widget to the custom name, and give
    the import path as Framework.GUI.<module name>, since relative
    paths don't work out however the ui file is being loaded,
    and this direct import will work since the sys path is setup
    already.
'''
from pathlib import Path

# Needed modules are kinda scattered all over, and get moved around
# between versions.
# The only (rough) documentation is at:
# http://pyqt.sourceforge.net/Docs/PyQt5/modules.html
from PyQt5.QtGui import QFont
from PyQt5.uic import loadUiType
from PyQt5 import QtWidgets, QtCore, QtGui

from Framework import Settings
from Framework import Print
from Framework import Change_Log

from .Session_Memory import Session_Memory
from .Worker_Thread_Handler import Worker_Thread_Handler
from . import Styles
from Framework.Common import home_path

from ..Edit_Table_Window import Edit_Table_Window
from ..Settings_Window import Settings_Window
from ..Script_Window import Script_Window


from ...Transforms.Live_Editor import Live_Editor

# Load the .ui file into a reuseable base class.
# This will return the designer generated class ("form"), and
# the Qt base class it is based on (QWidget in this case).
# http://pyqt.sourceforge.net/Docs/PyQt5/designer.html
gui_file = Path(__file__).parents[1] / 'x4c_gui_layout.ui'
generated_class, qt_base_class = loadUiType(str(gui_file))


class GUI_Main_Window(qt_base_class, generated_class):
    '''
    Custom Gui class object, as a child of the QMainWindow class.

    Attributes:
    * application
      - Link back to the parent QApplication object.
    * current_font
      - QFont object specifying the current primary display font.
      - This may differ from the main window .font().
    * current_style
      - Name of the current QStyle in use.
    * session_memory
      - QSettings object which will handle saving and reloading
        window settings.
    * tabs_dict
      - Dict, keyed by tab name, holding the tab widgets.
      - For convenient lookups from other locations.
    * tab_indices_dict
      - Dict, keyed by tab name, holding the index of the given tab.
      - Mainly for use internally during tab container function calls.
    * worker_thread
      - Worker_Thread_Handler that will be used to run scripts, plugins,
        and other framework functions that might take some time to return.
      - All widgets should share this thread, queueing requests to
        avoid framework collisions.
    '''
    def __init__(self, application):
        # Init the QMainWindow.
        super().__init__()
        self.setupUi(self)

        self.application = application
        self.current_font = None
        self.current_style = None
        #self.session_memory = Session_Memory(self)
        self.tabs_dict = {}
        self.tab_indices_dict = {}
        
        # Set up a QSettings object, giving it the path to where
        # the settings are stored. Set it as an ini file, since otherwise
        # it wants to make a mess in the registry.
        self.session_memory = QtCore.QSettings(
                str(home_path / 'gui_settings.ini'),
                QtCore.QSettings.IniFormat)

        # Set the title with version.
        # -Removed; a little tacky.
        #self.setWindowTitle('X4 Customizer {}'.format(Change_Log.Get_Version()))
        
        
        # Set the Framework to print to the gui.
        # Note: when running a script, the thread will handle
        # intercepting print statements and emit a signal.
        Print.logging_function = self.Print
        
        # Add a threading object.
        self.worker_thread = Worker_Thread_Handler(self)
        # Sends its emitted messages to Print.
        self.worker_thread.send_message.connect(self.Print)
        

        # Set up initial tabs.
        self.Create_Tab(Script_Window    , 'Script')
        self.Create_Tab(Settings_Window  , 'Settings')
        self.Create_Tab(Edit_Table_Window, 'Weapons', table_name = 'weapons')


        # Connect actions to handlers.
        self.action_Quit        .triggered.connect(self.Action_Quit)
        self.action_Change_Font .triggered.connect(self.Action_Change_Font)
        self.action_View_Output .triggered.connect(self.Action_View_Output)
            

        # Set up the styles menu.
        # This is done programatically, not in the gui file.
        self.Init_Styles()
        # Set a default font, prior to loading prior settings.
        self.Init_Font()

        # Restore the settings.
        self.Load_Session_Settings()
        
        # Set the tab widget to the first tab, since the functions above
        #  will cause it to want to switch to the graph tab 
        #  (for whatever reason).
        self.tabWidget.setCurrentIndex(0)
                
        # Load the Live_Editor patches.
        Live_Editor.Load_Patches()

        # Display the GUI upon creation.
        self.show()
        return

        
    def Print(self, line):
        '''
        Prints a line to the output widget.
        '''
        self.widget_output.append(line)
        return


    def Action_View_Output(self):
        '''
        View Output was selected from the menu.
        For now, just toggle the visibility.
        TODO: Maybe add a checkbox to the menu item, though that
        has some complexity for syncing with state restoration.
        TODO: fix bug with output dock that causes it to lose memory of
        sizing when toggled off/on.
        '''
        #checked = self.action_View_Output.isChecked()
        self.widget_output_dock.setVisible(not self.widget_output_dock.isVisible())
        return


    ##########################################################################
    # Tab related actions.

    def Create_Tab(self, widget_class, label, **kwargs):
        '''
        Create a new tab holding a widget_class object, with  the
        given tab label. Any extra kwargs are passed.
        '''
        # Create the content widget.
        # Give no parent yet, else it blobs over the main window.
        window = widget_class(parent = None, window = self, **kwargs)

        # Make the new tab.
        tab_index = self.tabWidget.addTab(window, label)
        
        # Store the widget and index, for use elsewhere.
        self.tabs_dict[label] = window
        self.tab_indices_dict[label] = tab_index
        return


    def Get_Tab_Widgets(self, filter = None):
        '''
        Returns a list of tab page widgets.

        * filter
          - Optional, strings or tuple of strings, names of the
            classes to be returned.
          - Eg. ('Settings_Window', 'Script_Window')
        '''
        # If a filter given, swap it over to actual classes
        # for doing an isinstance check.
        # These should all be imported already to this module.
        if isinstance(filter, str):
            filter = globals()[filter]
        elif isinstance(filter, (tuple, list)):
            filter = tuple([globals()[x] for x in filter])

        ret_list = []
        for label, widget in self.tabs_dict.items():
            # Skip non-matching class types.
            if filter and not isinstance(widget, filter):
                continue
            ret_list.append(widget)
        return ret_list


    ##########################################################################
    # Font related actions.
    # TODO: maybe split off the script edit window font from
    # the others.

    def Init_Font(self):
        '''
        Set up the default font for the various windows.
        This is mainly to pick a monospace font.
        TODO: maybe skip this and use qt default.
        '''
        new_font = QFont()
        new_font.setFamily("Courier")
        # Set the font selection preferences if the above is not found;
        #  aim to select anything monospace.
        new_font.setStyleHint(QFont.Monospace)
        new_font.setFixedPitch(True)
        new_font.setPointSize(10)
        # Update the window fonts.
        self.Update_Font(new_font)
        return

        
    def Action_Change_Font(self):
        '''
        The 'Font' action was selected.
        Launch a font selection window, and update with the resulting
        font selected (if any).
        '''
        # This should return the current_font if a new one is not selected,
        #  along with a second boolean indicating if the font changed.
        new_font, font_changed = QtWidgets.QFontDialog.getFont(
                                            self.current_font, self)
        # Update the font if needed.
        if font_changed:
            self.Update_Font(new_font)
        return


    def Update_Font(self, new_font):
        '''
        Update up the font to use in the various windows.
        '''
        self.current_font = new_font
                
        # Set up a slightly smaller version of the current font.
        small_font = QFont()
        # Unclear on how best to get an initial copy; try passing
        # through strings.
        small_font.fromString(new_font.toString())
        small_font.setPointSize(small_font.pointSize() - 2)

        # Pass the fonts to tag pages.
        for widget in self.Get_Tab_Widgets():
            widget.Update_Font(new_font, small_font)

        # Put a small font on the output window.
        self.widget_output.setFont(small_font)
        return

    
    ##########################################################################
    # Style related actions.

    def Init_Styles(self):
        '''
        Expands the menuStyle submenu with the selection options for
        found available qt styles.
        '''
        # Add submenu items for the style names.
        for name in sorted(Styles.Get_Style_Names()):
            action = self.menuStyle.addAction(name)
            # Annotate the action with the style name, for easy 
            # handling when triggered.
            action.style_name = name

            # Connect up the action to a shared handler.
            # This can use a lambda function to pass args to the called
            # handler function.
            # Note: this requires jumping through hoops to get the current
            # name to pass through, instead of all lambdas using the name
            # on the last loop iteration.
            # https://stackoverflow.com/questions/50298582/why-does-python-asyncio-loop-call-soon-overwrite-data
            # The first term is some qt junk term; after that give the
            # wanted term with a default set to the wanted value.
            action.triggered.connect(
                lambda qtjunk, name = name: self.Action_Change_Style(name))

        # Record the current style name; probably default Windows or similar.
        return

        
    def Action_Change_Style(self, style_name):
        '''
        A 'Style' submenu action was selected.
        '''
        # Update the style if needed.
        if style_name != self.current_style:
            self.Update_Style(style_name)
        return


    def Update_Style(self, style_name):
        '''
        Update up the style to use in the various windows.
        '''
        # Build the style.
        style = Styles.Make_Style(style_name)
        # Catch failures.
        if style == None:
            self.Print('Failed to create style ""'.format(style))
            return

        # Update the app.
        self.application.setStyle(style)
        # Save the name.
        self.current_style = style_name
        return
        
    ##########################################################################
    # Shutdown functions.
    
    def Action_Quit(self):
        '''
        Action to take when the close menu item is selected.
        '''
        # Redirect to .close().
        self.close()
        return


    # Specially named function called when the window is closed using
    # the 'x'.
    def closeEvent(self, event):
        '''
        Action to take when the close ('x') button is pressed.
        '''
        success = self.close()
        # Ignore the event if the close was cancelled.
        if success:
            event.accept()
        else:            
            event.ignore()
        return


    def close(self):
        '''
        Wrapped close() handler; called on 'x' press or by the Quit action.
        Returns True when closing the window, False when closing is cancelled.
        '''
        # Call close on all tab pages.
        # If these return False, cancel the close.
        for widget in self.Get_Tab_Widgets():
            if widget.Close() == False:
                return False

        # Stop any running script.
        self.worker_thread.Close()

        # Save the gui settings themselves.
        self.Save_Session_Settings()

        # Save the Live_Editor changes.
        Live_Editor.Save_Patches()

        super().close()
        return True

    
    ##########################################################################
    # Save/restore gui state        

    def Save_Session_Settings(self):
        '''
        Save gui settings for this run (font, layout, size, etc.).
        '''
        # Convenience renaming.
        settings = self.session_memory

        # These settings objects record all information when an ini
        # was loaded, including stale keys; clear them all out.
        for key in settings.allKeys():
            settings.remove(key)
        
        settings.beginGroup('Main_Window')
        # These functions appear to handle pos, size, and dock widget
        # size, for the main window. They do not capture any
        # internal widget positions (eg. splitters).
        settings.setValue('geometry', self.saveGeometry())
        settings.setValue('state'   , self.saveState())
        settings.setValue('font'    , self.current_font)
        settings.setValue('style'   , self.current_style)
        settings.endGroup()
        
        # Save state from tab pages.
        for label, widget in self.tabs_dict.items():
            settings.beginGroup('Tab_Page_{}'.format(label))
            widget.Save_Session_Settings(settings)
            settings.endGroup()

        # Note: there is a .sync() method that writes the file, but
        # it is apparently handled automatically on shutdown.
        return

    
    def Load_Session_Settings(self):
        '''
        Restore gui settings from a prior run.
        '''
        # Convenience renaming.
        settings = self.session_memory

        # Look up existing settings; change nothing if none found.
        # Note: setting the default for .value() to None causes some
        # default object to be returned, so just use a .contains()
        # check instead.
        # Use a settings group for scalability, in case other windows
        # need to also be saved in the future.
        group = 'Main_Window'
        settings.beginGroup(group)
        for field, method in [
            ('geometry', self.restoreGeometry),
            ('state'   , self.restoreState),
            ('font'    , self.Update_Font),
            ('style'   , self.Update_Style),
            ]:
            if not settings.contains(field):
                continue
            # Just in case the ini format is wrong, skip over problematic
            # setting values.
            try:
                method(settings.value(field))
            except Exception:
                self.Print(('Failed to restore prior setting: "{}:{}"'
                            .format(group, field)))
        settings.endGroup()
        
        # Load state from tab pages.
        for label, widget in self.tabs_dict.items():
            settings.beginGroup('Tab_Page_{}'.format(label))
            widget.Load_Session_Settings(settings)
            settings.endGroup()
            
        return
        
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
from PyQt5.uic import loadUi
from PyQt5 import QtWidgets, QtCore, QtGui

from Framework import Settings
from Framework import Print

from .Gui_Settings import Gui_Settings
from .Script_Actions import Script_Actions
from .Worker_Thread import Worker_Thread
from Framework.Common import home_path

from ...Analyses.Live_Editor import Live_Editor


class GUI_Main_Window(QtWidgets.QMainWindow):
    '''
    Custom Gui class object, as a child of the QMainWindow class.

    Attributes:
    * current_font
      - QFont object specifying the current primary display font.
      - This may differ from the main window .font().
    * gui_settings
      - Gui_Settings object which will handle saving and reloading
        window settings.
    * script_actions
      - Script_Actions object which will handle script saving, reloading,
        and running.
    * worker_thread
      - QThread that will be used to run scripts, plugins, and other
        framework functions that might take some time to return.
      - All widgets should share this thread, waiting for it to
        be free, to avoid framework collisions.
      - Users should set up the function and args to be called,
        and connect to the worker_thread.finished signal to
        capture output, disconnecting when done or otherwise
        being careful not to take action if the thread finishes
        for another user.
    '''
    def __init__(self):
        # Init the QMainWindow.
        super().__init__()

        # Load the .ui file created in Qt Designer into this window.
        gui_file = Path(__file__).parents[1] / 'x4c_gui_layout.ui'
        loadUi(str(gui_file), self)

        self.current_font = None
        self.gui_settings = Gui_Settings(self)
        self.script_actions = Script_Actions(self, self.widget_script)

        # Set the title after the UI loads.
        # TODO: include version number, maybe.
        self.setWindowTitle('X4 Customizer')
        
        # Set the Framework to print to the gui.
        # Note: when running a script, the thread will handle
        # intercepting print statements and emit a signal.
        Print.logging_function = self.Print
        
        # Add a threading object.
        self.worker_thread = Worker_Thread(self)
        # Sends its emitted messages to Print.
        self.worker_thread.send_message.connect(self.Print)

        # Qt widgets are supposed to have links to parents and a function
        # to get their top level window, but in practice those seem
        # to be iffy and do not return to here, so need to fill in
        # links manually.
        # TODO: maybe rename these to 'window' or similar, to have
        # less confusion with the qt's parents.
        self.widget_plugins       .parent = self
        self.widget_script        .parent = self
        self.widget_documentation .parent = self
        self.widget_settings      .parent = self
        self.widget_settings_doc  .parent = self
        self.widget_output        .parent = self

        # Test weapons table viewer.
        self.widget_weapons       .parent = self
        # Let the main widget deal with the rest of the table setup.
        self.widget_weapons.Delayed_Init()
        
        # TODO: organized way to set splitters, moving them to
        # tab handlers or similar.
        self.hsplitter_tab_settings.setSizes([1,1])
        self.hsplitter_tab_script.setSizes([1,1])
        self.vsplitter_tab_script.setSizes([1,1])
               
        # Set up initial documentation for settings.
        self.widget_settings_doc.setPlainText(Settings.__doc__)

        # Actions (defined in Qt designer and connected to menu and toolbar
        #  items) need to be 'connect'ed to their function to execute.
        # Setup the action and method pairs to be looped through.
        # This style is used in favor of heavy copy/pasting of the connect
        #  function, to make it more scalable/readable for new actions.
        action_method_dict = {
            # These actions get bounced to the script handler.
            'action_New'              : self.script_actions.Action_New_Script,
            'action_Open'             : self.script_actions.Action_Open_Script,
            'action_Save'             : self.script_actions.Action_Save_Script,
            'action_Save_As'          : self.script_actions.Action_Save_Script_As,
            'action_Run_Script'       : self.script_actions.Action_Run_Script,

            'action_Quit'             : self.Action_Quit,        
            'action_Change_Font'      : self.Action_Change_Font,
            'action_View_Output'      : self.Action_View_Output,
            }
        for action_str, this_method in action_method_dict.items():
            # Lookup the member.
            this_action = getattr(self, action_str)
            # Connect on the 'triggered' event.
            # Possible events to choose from:
            #  triggered, hovered, toggled, changed.
            # TODO: if setting up per-action events, include the event in
            #  the dict above. Could be useful for view toggles.
            this_action.triggered.connect(this_method)
            
        # Put a nice printout here, before the Gui settings loading
        # prints its own stuff.
        self.Print('Gui started')

        # Set a default font, prior to loading prior settings.
        self.Init_Font()
        
        # Restore the settings.
        self.gui_settings.Restore_Gui_Settings()
        
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

        # Separate widgets into those that will get a full size font.
        # and those with a reduced size font.
        full_font_widgets = [
            self.widget_plugins,
            self.widget_script,
            self.widget_documentation,
            self.widget_settings,
            self.widget_settings_doc,
            self.widget_weapons,
            self.widget_weapons_info,
            ]
        small_font_widgets = [
            self.widget_output,
            ]
        
        # Set up a slightly smaller version of the current font.
        small_font = QFont()
        # Unclear on how best to get an initial copy; try passing
        # through strings.
        small_font.fromString(new_font.toString())
        small_font.setPointSize(small_font.pointSize() - 2)


        # Start with the small font applied to the main window,
        # which will replicate to all sub widgets.
        # -Removed; makes the main window look too different from
        #  normal programs.
        #self.setFont(small_font)

        # Update full size widgets.
        for widget in full_font_widgets:
            widget.setFont(new_font)
        # Update the reduced size widgets.
        for widget in small_font_widgets:
            widget.setFont(small_font)
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
        # Prompt to save the open app.
        # This will prevent closing if "cancel" was selected.
        if not self.script_actions.Check_If_Save_Needed():
            return False

        # Stop any running script.
        if self.worker_thread.isRunning():
            self.worker_thread.quit()

        # Save the gui version of settings.
        self.widget_settings.Save()
        # Save the gui settings themselves.
        self.gui_settings.Save_Gui_Settings()

        # Save the Live_Editor changes.
        Live_Editor.Save_Patches()

        super().close()
        return True




        
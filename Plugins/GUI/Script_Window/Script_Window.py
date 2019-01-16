
from pathlib import Path
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox
from PyQt5.uic import loadUiType
 
from Framework import Settings
from Framework import File_System
from Framework.Common import home_path
from Framework import Main
from Framework import Live_Editor
from Framework import Plugin_Log
from ..Shared import Tab_Page_Widget   


# Load the .ui file into a reuseable base class.
# This will return the designer generated class ("form"), and
# the Qt base class it is based on (QWidget in this case).
# http://pyqt.sourceforge.net/Docs/PyQt5/designer.html
gui_file = Path(__file__).parents[1] / 'x4c_gui_script_tab.ui'
generated_class, qt_base_class = loadUiType(str(gui_file))


class Script_Window(Tab_Page_Widget, generated_class):
    '''
    Window used for editing the customizer input script.
    Intended to be used just once for now, though more can theoretically
    be added for different scripts (if the 'run script' button is moved
    into the tabs).

    Widget names:
    * hsplitter
    * vsplitter
    * widget_documentation
    * widget_plugins
    * widget_script

    Attributes:
    * window
      - The parent main window holding this tab.
    * current_script_path
      - Path for the currently open script.
    * last_dialog_path
      - Path last used in the Load or Save dialog boxes, to be reused.
    '''
    def __init__(self, parent, window):
        super().__init__(parent, window)
        
        self.current_script_path = None
        self.last_dialog_path = home_path / 'Scripts'

        # Hook up to some main window actions.        
        window.action_New        .triggered.connect( self.Action_New_Script    )
        window.action_Open       .triggered.connect( self.Action_Open_Script   )
        window.action_Save       .triggered.connect( self.Action_Save_Script   )
        window.action_Save_As    .triggered.connect( self.Action_Save_Script_As)
        window.action_Run_Script .triggered.connect( self.Action_Run_Script    )
        
        # Set default splitter ratios.
        # Just even splits for now; these mostly only affect a new user.
        self.hsplitter.setSizes([1000,1000])
        self.vsplitter.setSizes([1000,1000])

        # Always start a new script on init.
        # This can be overwritten by prior session settings, but those
        # won't be available on a first run.
        self.Action_New_Script()
        return
       

    def Check_If_Save_Needed(self):
        '''
        Checks if the current script needs to be saved, and possibly opens
        a Save-As request if so.
        This should be called when closing an open and maybe edited script.
        Returns True on success (no save needed or got user response),
        False on failure (user cancelled the action).
        '''
        if self.widget_script.Is_Modified():
            # Prompt for a save yes/no style.
            message_box = QMessageBox()
            message_box.setText('Save modified script?')
            message_box.setStandardButtons(
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            message_box.setDefaultButton(QMessageBox.Save)
            message_box.setWindowTitle('Save?')
            selection_code = message_box.exec_()

            # Need to check the return code against button codes.
            if selection_code == QMessageBox.Save:
                self.Save_Script_As()
            elif selection_code == QMessageBox.Cancel:
                # On cancellation, let the caller know so they can
                # stop whatever action prompted this check.
                return False
        return True


    def Action_New_Script(self):
        '''
        New was selected from the menu.
        Clears out the script widget.
        '''
        # Prompt to save the open app.
        if not self.Check_If_Save_Needed():
            return
        self.widget_script.New_Script()
        self.current_script_path = None
        self.widget_script.Clear_Modified()
        self.window.Print('New script started')
        return

        
    def Action_Open_Script(self):
        '''
        Open was selected from the menu.
        Creates a file selection dialog.
        '''
        # Prompt to save the open app.
        if not self.Check_If_Save_Needed():
            return

        # Create a file selection dialog, using a QFileDialog object.
        file_dialogue = QtWidgets.QFileDialog(self.window)
        # Require selecting an existing file.
        file_dialogue.setFileMode(QtWidgets.QFileDialog.ExistingFile)
            
        # Get the filename/path from the dialogue.
        file_selected, _ = file_dialogue.getOpenFileName(
            directory = str(self.last_dialog_path),
            filter = 'Python script (*.py)')
        # If nothing selected, return early.
        if not file_selected:
            return

        # Convert to a Path.
        file_selected = Path(file_selected)
        # Update the last_dialog_path.
        last_dialog_path = file_selected.parent
                
        # Continue using Load_Project_From_File.
        # TODO: maybe combine this with Load_Project_From_File if it is not
        #  used anywhere else.
        self.Load_Script_File(file_selected)        
        return


    def Load_Script_File(self, file_path):
        '''
        Load in the text from a script file, and sent to the
        script widget.
        '''
        try:
            text = file_path.read_text()
        except Exception:
            self.window.Print('Failed to load script from "{}"'.format(file_path))
            return

        self.widget_script.setPlainText(text)
        self.current_script_path = file_path
        self.widget_script.Clear_Modified()
        self.window.Print('Loaded script from "{}"'.format(file_path))
        # TODO: maybe update window name.
        return


    def Action_Save_Script(self):
        '''
        Save was selected from the menu
        '''
        # Currently the Save button is shared across all tabs.
        # Use an emitted signal, so other tabs will save too.
        # This will be bounced back here to trigger the actual save.
        self.window.Send_Signal('save')
        return


    def Action_Save_Script_As(self):
        '''
        Save-as was selected from the menu
        '''
        self.window.Send_Signal('save_as')
        return


    def Handle_Signal(self, *flags):
        '''
        Respond to signal events.
        '''
        if 'save_as' in flags:
            self.Save_Script_As()
        elif 'save' in flags:
            self.Save_Script()
        return


    def Save_Script(self):
        '''
        Save was selected from the menu, or some other action triggered
        a save request.
        If a file path exists, save to that file directly, else
        bounce over to the Save-As handler.
        Returns True if the script saved successfully or is already
        up to date; returns False is the user cancelled the save.
        '''        
        # Check if the script has a file set.
        if self.current_script_path != None:
            # If a save isn't needed, do nothing.
            if not self.widget_script.Is_Modified():
                return True
            # Save to it.
            save_success = self.Save_Script_To_File(self.current_script_path)
        else:
            # Fall back on the save_as dialogue.
            save_success = self.Save_Script_As()
        return save_success


    def Save_Script_As(self):
        '''
        Save-as was selected from the menu.
        Opens a dialog for selecting the file name and path, and
        then saves the script (if not cancelled).
        Returns True if the script saved succesfully, False if not.
        '''
        # TODO: just use getSaveFileName as a static function, dont
        #  make a dialog object.
        # Create a file selection dialogue, using a QFileDialog object.
        file_dialogue = QtWidgets.QFileDialog(self.window)

        # Allow selection of any file (as oppposed to existing file).
        file_dialogue.setFileMode(QtWidgets.QFileDialog.AnyFile)

        # Get the filename/path from the dialogue.
        #  Note: in qt5 this now returns a tuple of
        #   (path string, type name with extension as a string).
        #  Only keep the full path here.
        file_selected, _ = file_dialogue.getSaveFileName(
            directory = str(self.last_dialog_path),
            filter = 'Python script (*.py)')

        # If the file path is empty, the user cancelled the dialog.
        if not file_selected:
            return False
        
        # Convert to a Path.
        file_selected = Path(file_selected)
        # Update the last_dialog_path.
        last_dialog_path = file_selected.parent

        # Pass the file name on to the general save function.
        save_success = self.Save_Script_To_File(file_selected)
        return save_success

    
    def Save_Script_To_File(self, file_path):
        '''
        Saves the current script.
        Returns True if the script saved succesfully, False if not.
        '''
        # Record the file saved to for later Save actions.
        self.current_script_path = file_path

        # Get the text to save.
        text = self.widget_script.toPlainText()
        # Write it.
        file_path.write_text(text)

        # Clear the modified flag.
        self.widget_script.Clear_Modified()

        self.window.Print('Saved script to "{}"'.format(file_path))
        
        # Return True on succesful save.
        return True
    
    
        
    ##########################################################################
    # Thread handling.
       
    def Script_Prelaunch(self):
        '''
        Code to run just prior to a script being launched.
        Resets the file system, saves live editor patches, etc.
        '''
        # Clear out the file system from any prior run changes.
        File_System.Reset()        
        # Save the Live_Editor patches, since they may get loaded
        #  by a plugin for xml application.
        Live_Editor.Save_Patches()
        self.window.Print('Saved Live Editor patches')
        # Send a signal so Config is updated properly.
        self.window.Send_Signal('script_starting')
        return

    
    def Action_Run_Script(self):
        '''
        Runs the currently loaded script.
        '''
        # Save the script to a file.
        saved = self.Save_Script()
        # If the save was cancelled, skip the run.
        if not saved:
            return

        # Grey out the run action.
        # Do this after saving, since it might return early.
        self.window.action_Run_Script.setEnabled(False)

        # Set up its command, to run a script.
        # The easiest way to do this is to just call Main.Run, and let
        # it handle the dynamic import.
        # Use command line style args for this, for now.
        # It should be safe to always enable argpass, since the top
        # argparser -h isn't useful.
        self.Queue_Thread(
            Main.Run,
            # A single string arg, command line style.
            str(self.current_script_path) + ' -argpass',
            prelaunch_function = self.Script_Prelaunch,
            )
        return
        
    
    def Handle_Thread_Finished(self, return_value):
        '''
        Clean up after a Run Script thread has finished.
        '''
        super().Handle_Thread_Finished()
        # Turn the button back on.
        self.window.action_Run_Script.setEnabled(True)

        # When done, restore Settings back to the gui values, in case
        # the script temporarily modified them.
        #-Removed; signals handle this.
        #self.window.Store_Settings()

        # Close any transform log that might be open, to flush it
        # out and also reset it for a later run.
        Plugin_Log.Close()

        # TODO: detect errors in the script and note them; for now, the
        # thread or framework will tend to print them out.
        self.window.Print('Script run completed')

        # Tell any live edit tables to refresh their current values,
        # since the script may have changed them.
        Live_Editor.Reset_Current_Item_Values()
        #-Removed; signals handle this.
        #self.window.Soft_Refresh()
        
        # Send out some signalling flags.
        self.window.Send_Signal('script_completed',
                                'files_modified',
                                'files_loaded')
        return

    
    def Save_Session_Settings(self, settings):
        '''
        Save aspects of the current sessions state.
        '''
        super().Save_Session_Settings(settings)
        settings.setValue('current_script_path', str(self.current_script_path))
        settings.setValue('last_dialog_path'   , str(self.last_dialog_path))
        return


    def Load_Session_Settings(self, settings):
        '''
        Save aspects of the prior sessions state.
        '''
        super().Load_Session_Settings(settings)
        # Note: need to capture 'None' strings and convert them.
        # Paths need to be cast to a Path if not None.
        stored_value = settings.value('last_dialog_path', None)
        if stored_value not in [None, 'None']:
            self.last_dialog_path = Path(stored_value)
        
        # Try to load the prior script.
        stored_value = settings.value('current_script_path', None)
        if stored_value not in [None, 'None']:
            self.current_script_path = Path(stored_value)
            self.Load_Script_File(self.current_script_path)
        return


    def Close(self):
        '''
        Prompt to save the open app.
        This will prevent closing if "cancel" was selected.
        '''
        super().Close()
        if not self.Check_If_Save_Needed():
            return False
        return True

    
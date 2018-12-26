
from pathlib import Path
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox

from Framework import Settings
from Framework import File_System
from Framework.Common import home_path
from Framework import Main

from ...Transforms.Live_Editor import Live_Editor

class Script_Actions:
    '''
    Support class for saving, loading, and running script files,
    supporting the main gui window.
    
    Attributes:
    * parent
      - The parent QMainWindow.
    * widget_script
      - The widget holding the script.
    * current_script_path
      - Path for the currently open script.
    * last_dialog_path
      - Path last used in the Load or Save dialog boxes, to be reused.
    '''
    def __init__(self, parent, widget_script):
        self.parent = parent
        self.widget_script = widget_script
        self.current_script_path = None
        self.last_dialog_path = home_path / 'Scripts'        
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
                self.Action_Save_Script_As()
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
        self.parent.Print('New script started')
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
        file_dialogue = QtWidgets.QFileDialog(self.parent)
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
            self.widget_script.setPlainText(text)
            self.current_script_path = file_path
            self.widget_script.Clear_Modified()
            self.parent.Print('Loaded script from "{}"'.format(file_path))
        except Exception:
            self.parent.Print('Failed to load script from "{}"'.format(file_path))
        # TODO: maybe update window name.
        return


    # TODO: detect script edits (typing into the text box).
    
    def Action_Save_Script(self):
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
            save_success = self.Save_Script(self.current_script_path)
        else:
            # Fall back on the save_as dialogue.
            save_success = self.Action_Save_Script_As()
        return save_success


    def Action_Save_Script_As(self):
        '''
        Save-as was selected from the menu.
        Opens a dialog for selecting the file name and path, and
        then saves the script (if not cancelled).
        Returns True if the script saved succesfully, False if not.
        '''

        # Create a file selection dialogue, using a QFileDialog object.
        file_dialogue = QtWidgets.QFileDialog(self.parent)

        # Allow selection of any file (as oppposed to existing file).
        file_dialogue.setFileMode(QtWidgets.QFileDialog.AnyFile)

        # Get the filename/path from the dialogue.
        #  Note: in qt5 this now returns a tuple of
        #   (path string, type name with extention as a string).
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
        save_success = self.Save_Script(file_selected)
        return save_success

    
    def Save_Script(self, file_path):
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

        self.parent.Print('Saved script to "{}"'.format(file_path))
        
        # Return True on succesful save.
        return True
    
    
        
    ##########################################################################
    # Thread handling.
    # TODO: maybe break out into a Thread_Handler class, particularly
    # if other thread types will be added.
    
    def Action_Run_Script(self):
        '''
        Runs the currently loaded script.
        '''
        # Do nothing if a script is running.
        if self.parent.worker_thread.isRunning():
            return

        # Save the script to a file.
        saved = self.Action_Save_Script()
        # If the save was cancelled, skip the run.
        if not saved:
            return

        # Reset the Settings, so that it will do path checks again.
        Settings.Reset()
        # Ensure the settings are updated from gui values.
        self.parent.widget_settings.Store_Settings()

        # Clear out the file system from any prior run changes.
        File_System.Reset()
        
        # Save the Live_Editor patches, since they may get loaded
        #  by a plugin for xml application.
        Live_Editor.Save_Patches()
        
        # Set up its command, to run a script.
        # The easiest way to do this is to just call Main.Run, and let
        # it handle the dynamic import.
        # Use command line style args for this, for now.
        # It should be safe to always enable argpass, since the top
        # argparser -h isn't useful.
        self.parent.worker_thread.Set_Function(
            Main.Run,
            # A single string arg, command line style.
            str(self.current_script_path) + ' -argpass'
            )
        # Listen for the 'finished' signal.
        self.parent.worker_thread.finished.connect(self.Handle_Thread_Finished)

        self.parent.worker_thread.start()
        # Grey out the run action.
        self.parent.action_Run_Script.setEnabled(False)

        return


    def Handle_Thread_Finished(self):
        '''
        Clean up after a Run Script thread has finished.
        '''
        self.parent.action_Run_Script.setEnabled(True)
        self.parent.worker_thread.finished.disconnect(self.Handle_Thread_Finished)

        # When done, restore Settings back to the gui values.
        # This may not be strictly necessary.
        self.parent.widget_settings.Store_Settings()

        # TODO: detect errors in the script and note them; for now, the
        # thread or framework will tend to print them out.
        self.parent.Print('Script Run completed')

        # Tell any live edit tables to refresh their current values,
        # since the script may have changed them.
        self.parent.widget_weapons.Soft_Refresh()
        return
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
from collections import defaultdict
import threading

# Needed modules are kinda scattered all over, and get moved around
# between versions.
# The only (rough) documentation is at:
# http://pyqt.sourceforge.net/Docs/PyQt5/modules.html
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.uic import loadUi
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox

from ..Common import Settings
from ..Common import Print
from ..Common import home_path
from ..File_Manager import File_System
from .Thread_Run_Script import Thread_Run_Script



class GUI_Main_Window(QtWidgets.QMainWindow):
    '''
    Custom Gui class object, as a child of the QMainWindow class.

    Attributes:
    * current_script_path
      - Path for the currently open script.
    * last_dialog_path
      - Path last used in the Load or Save dialog boxes, to be reused.
    * current_font
      - QFont object specifying the current primary display font.
      - This may differ from the main window .font().
    * gui_settings
      - QSettings object holding gui customizations (window size,
        position, etc.).
    '''
    def __init__(self):
        # Init the QMainWindow.
        super().__init__()

        self.current_script_path = None
        self.current_font = None
        self.last_dialog_path = home_path / 'Scripts'

        # Load the .ui file created in Qt Designer into this window.
        # This file is located in this dir.
        gui_file = Path(__file__).parent / 'x4c_gui_layout.ui'
        loadUi(gui_file, self)

        # Set the title after the UI loads.
        # TODO: include version number, maybe.
        self.setWindowTitle('X4 Customizer')
        
        # Set the Framework to print to the gui.
        # Note: when running a script, the thread will handle
        # intercepting print statements and emit a signal.
        Print.logging_function = self.Print

        # Add a threading object.
        self.run_script_thread = Thread_Run_Script(self)
        self.run_script_thread.finished.connect(self.Handle_Thread_Finished)
        # Sends its emitted messages to Print.
        self.run_script_thread.send_message.connect(self.Print)

        # Qt widgets are supposed to have links to parents and a function
        # to get their top level window, but in practice those seem
        # to be broken and do not return to here, so need to fill in
        # links manually.
        self.widget_plugins       .parent = self
        self.widget_script        .parent = self
        self.widget_documentation .parent = self
        self.widget_settings      .parent = self
        self.widget_settings_doc  .parent = self
        self.widget_output        .parent = self
        self.run_script_thread    .parent = self
               
        # Set up initial documentation for settings.
        self.widget_settings_doc.setPlainText(Settings.__doc__)

        # Actions (defined in Qt designer and connected to menu and toolbar
        #  items) need to be 'connect'ed to their function to execute.
        # Setup the action and method pairs to be looped through.
        # This style is used in favor of heavy copy/pasting of the connect
        #  function, to make it more scalable/readable for new actions.
        # TODO: maybe break this back up and move it down to sections dedicated
        #  to each code action, with their own inits, though for now this is
        #  pretty simple to leave here.
        action_method_dict = {
            'action_New'              : 'Action_New_Script',
            'action_Open'             : 'Action_Open_Script',
            'action_Save'             : 'Action_Save_Script',
            'action_Save_As'          : 'Action_Save_Script_As',
            'action_Quit'             : 'Action_Quit',
        
            'action_Change_Font'      : 'Action_Change_Font',
            'action_Run_Script'       : 'Action_Run_Script',
            'action_View_Output'      : 'Action_View_Output',
            }
        for action_str, method_str in action_method_dict.items():
            # Lookup the member and method.
            this_action = getattr(self, action_str)
            this_method = getattr(self, method_str)
            # Connect on the 'triggered' event.
            # Possible events to choose from:
            #  triggered, hovered, toggled, changed.
            # TODO: if setting up per-action events, include the event in
            #  the dict above.
            this_action.triggered.connect(this_method)
            
        # Put a nice printout here, before the Gui settings loading
        # prints its own stuff.
        self.Print('Gui started')

        # Set a default font, prior to loading prior settings.
        self.Init_Font()

        
        # Set up a QSettings object, giving it the path to where
        # the settings are stored. Set it as an ini file, since otherwise
        # it wants to make a mess in the registry.
        self.gui_settings = QtCore.QSettings(
                str(home_path / 'gui_settings.ini'),
                QtCore.QSettings.IniFormat)

        # Restore the settings.
        self.Restore_Gui_Settings()


        # Adjust the splitter sizing on the main window.
        # Qtdesigner does not support setting the widget initial size
        #  distribution when using splitters (which allow the user to
        #  drag-adjust widget sizes), so the distributions need to be
        #  done here in init.    
        # These values are given in pixels, with a couple caveats:
        # -If the value is smaller that the widget minimum, it is
        #  replaced with the min.
        # -If the values do not sum up to the splitter widget size,
        #  they are used as ratios to determine the splitting.
        # Just treat these as ratios here.
        # The list order is somewhat clumsy, but might match the
        #  ordering shown by Qtdesigner?
        # -No, it doesn't.
        #  TODO: figure this out reliably; for now just trial/error.
        # The tab/output splitter is [output, tab]
        self.splitter_tab_output.setSizes([3000,1000])




        # Set the tab widget to the first tab, since the functions above
        #  will cause it to want to switch to the graph tab 
        #  (for whatever reason).
        self.tabWidget.setCurrentIndex(0)




        ## Run the close project routine, which resets the window and puts
        ##  it in the same state as startup.
        ## This may also create a blank application for convenience, but
        ##  will disable action buttons to prevent it being used.
        #s.Action_Close_Project()
        #
        ## TODO: need to think a bit on how to load in an application,
        ##  to clean up concepts on what it means to have a closed app,
        ##  to open an app, to call the gui on an existing app, etc.
        ## Refresh the windows with the current application, if one available.
        #s.Refresh()
        
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
        '''
        #checked = self.action_View_Output.isChecked()
        self.widget_output_dock.setVisible(not self.widget_output_dock.isVisible())


    ##########################################################################
    # Font related actions.

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
    # Save/Load related actions.
    
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
        if not self.Check_If_Save_Needed():
            return False

        # Stop any running script.
        if self.run_script_thread.isRunning():
            self.run_script_thread.quit()

        # Save the gui version of settings.
        self.widget_settings.Save()
        # Save the gui settings themselves.
        self.Save_Gui_Settings()

        super().close()
        return True


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
        self.Print('New script started')
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
        # TODO: point this at the Scripts folder by default.
        file_dialogue = QtWidgets.QFileDialog(self)
        # Require selecting an existing file.
        file_dialogue.setFileMode(QtWidgets.QFileDialog.ExistingFile)
            
        # Get the filename/path from the dialogue.
        file_selected, _ = file_dialogue.getOpenFileName(
            directory = str(self.last_dialog_path),
            filter = 'Python script (*.py)')

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
            self.Print('Loaded script from "{}"'.format(file_path))
        except Exception:
            self.Print('Failed to load script from "{}"'.format(file_path))
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
        file_dialogue = QtWidgets.QFileDialog(self)

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

        self.Print('Saved script to "{}"'.format(file_path))
        
        # Return True on succesful save.
        return True

    
        
    ##########################################################################
    # Thread handling.
    
    def Action_Run_Script(self):
        '''
        Runs the currently loaded script.
        '''
        # Do nothing if a script is running.
        if self.run_script_thread.isRunning():
            return

        # Save the script to a file.
        saved = self.Action_Save_Script()
        # If the save was cancelled, skip the run.
        if not saved:
            return

        # Reset the Settings, so that it will do path checks again.
        Settings.Reset()
        # Ensure the settings are updated from gui values.
        self.widget_settings.Store_Settings()

        # Clear out the file system from any prior run changes.
        File_System.Reset()

        #Main.Run(str(self.current_script_path) + ' -argpass')
        self.run_script_thread.start()
        # Grey out the run action.
        self.action_Run_Script.setEnabled(False)

        return


    def Handle_Thread_Finished(self):
        '''
        Clean up after a Run Script thread has finished.
        '''
        # When done, restore Settings back to the gui values.
        # This may not be strictly necessary.
        self.widget_settings.Store_Settings()
        # TODO: detect errors in the script and note them.
        self.Print('Script Run completed')
        self.action_Run_Script.setEnabled(True)
        return


        
        
    ##########################################################################
    # Gui settings save/restore.
    
    
    def Restore_Gui_Settings(self):
        '''
        Restore gui settings from a prior run.
        '''
        # Convenience renaming.
        settings = self.gui_settings

        # Look up existing settings; change nothing if none found.
        # Note: setting the default for .value() to None causes some
        # default object to be returned, so just use a .contains()
        # check instead.
        # Use a settings group for scalability, in case other windows
        # need to also be saved in the future.
        group = 'Main_Window'
        settings.beginGroup(group)
        for field, method in [
            #('size', self.resize),
            #('pos' , self.move),
            ('font', self.Update_Font),
            ('geometry', self.restoreGeometry),
            ('state', self.restoreState),
            ]:
            if settings.contains(field):
                # Just in case the ini format is wrong, skip over problematic
                # setting values.
                try:
                    method(settings.value(field))
                except Exception:
                    self.Print(('Failed to restore prior setting: "{}:{}"'
                               .format(group, field)))
        settings.endGroup()
        
        # Iterate over all widgets, finding splitters.
        for splitter in self.findChildren(QtWidgets.QSplitter):
            name = splitter.objectName()
            settings.beginGroup(name)
            if settings.contains('state'):
                try:
                    splitter.restoreState(settings.value(field))
                except Exception:
                    self.Print(('Failed to restore prior setting: "{}:{}"'
                               .format(splitter,field)))
            settings.endGroup()


        # Custom values.
        # Note: need to capture 'None' strings and conver them.
        # Paths need to be cast to a Path if not None.
        self.last_dialog_path = settings.value('last_dialog_path', None)
        if self.last_dialog_path not in [None, 'None']:
            self.last_dialog_path = Path(self.last_dialog_path)
        else:
            self.last_dialog_path = None

        # Try to load the prior script.
        self.current_script_path = settings.value('current_script_path', None)
        if self.current_script_path not in [None, 'None']:
            self.current_script_path = Path(self.current_script_path)
            self.Load_Script_File(self.current_script_path)
        else:
            self.current_script_path = None
            self.Action_New_Script()

        return
        

    def Save_Gui_Settings(self):
        '''
        Save gui settings for this run (font, layout, size, etc.).
        '''
        # Convenience renaming.
        settings = self.gui_settings
        # These settings objects record all information when an ini
        # was loaded, including stale keys; clear them all out.
        for key in settings.allKeys():
            settings.remove(key)
        
        settings.beginGroup('Main_Window')        
        # These functions appear to handle pos, size, and dock widget
        # size, for the main window. They do not capture any
        # internal widget positions (eg. splitters).
        settings.setValue('geometry', self.saveGeometry())
        settings.setValue('state', self.saveState())
        settings.setValue('font', self.current_font)
        settings.endGroup()

        # Iterate over all widgets, finding splitters.
        for splitter in self.findChildren(QtWidgets.QSplitter):
            name = splitter.objectName()
            settings.beginGroup(name)
            settings.setValue('state', splitter.saveState())
            settings.endGroup()

        # Custom values.
        settings.setValue('current_script_path', str(self.current_script_path))
        settings.setValue('last_dialog_path'   , str(self.last_dialog_path))

        # Note: there is a .sync() method that writes the file, but
        # it is apparently handled automatically on shutdown.
        return

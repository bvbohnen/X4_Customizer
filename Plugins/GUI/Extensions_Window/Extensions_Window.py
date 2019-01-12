
from pathlib import Path

from PyQt5.uic import loadUiType
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QStandardItemModel, QStandardItem

from Framework import Settings
from ..Shared import Tab_Page_Widget
from Framework import File_System, File_Manager
from ...Utilities import Check_Extension
from ..Shared.Misc import Set_Icon, Set_Foreground_Color, Set_Background_Color

gui_file = Path(__file__).parents[1] / 'x4c_gui_extensions_tab.ui'
generated_class, qt_base_class = loadUiType(str(gui_file))


class Extensions_Window(Tab_Page_Widget, generated_class):
    '''
    Window used for viewing found extensions, enabling or disabling
    them, and checking for errors.
    Intended to be used just once.

    Widget names:
    * w_button_enable_all
    * w_button_disable_all
    * w_button_reload
    * w_button_test_all
    * w_button_test_selected
    * w_button_retest_errors
    * w_hide_1
    * w_hide_2
    * w_hide_3
    * w_text_details
    * w_listView
    
    Attributes:
    * window
      - The parent main window holding this tab.
    * list_model
      - QStandardModel to run the w_list_extensions.
    * selected_item
      - QStandardModelItem that is currently selected.
    * extension_item_dict
      - Dict, keyed by extension id, holding the QStandardModelItem
        representing it.
    '''
    # Set this tab as unique; disallow multiple to avoid them fighting
    # over what gets enabled/disabled.
    unique_tab = True
    
    # Signal from the Test_Thread to the Test_Result_Handler.
    # The thread will be in a qt thread domain, the handler in this
    # domain, so use a signal for this.
    # Messages are just those recorded by the Check_Extension log
    # lines, joined together, following the ext_id of the test.
    test_result = QtCore.pyqtSignal(str, str)

    def __init__(self, parent, window):
        super().__init__(parent, window)
        self.selected_item = None
        self.extension_item_dict = {}

        # Don't print args for threads; some lists are passed around.
        self.print_thread_args = False
                        
        # Set up initial, blank models.
        self.list_model  = QStandardItemModel(self)
        self.w_listView.setModel(self.list_model)
        
        # Catch selection changes in the view.
        self.w_listView.selectionModel().selectionChanged.connect(
            self.Handle_selectionChanged)
        # Catch double clicks, to toggle checkboxes more easily.
        self.w_listView.doubleClicked.connect(
            self.Handle_doubleClicked)

        # Catch changes to item check boxes.
        self.list_model.itemChanged.connect(
            self.Handle_itemChanged)
        
        # Hide the invisible buttons, but set them to still take space.
        # These are used to center and shrink the active buttons.
        # See comments in File_Viewer_Window on this.
        for widget in [self.w_hide_1, self.w_hide_2, self.w_hide_3]:
            widget.setVisible(False)
            sizepolicy = widget.sizePolicy()
            sizepolicy.setRetainSizeWhenHidden(True)
            widget.setSizePolicy(sizepolicy)

        # Init the splitter to 1:1:1:1.
        self.hsplitter.setSizes([1000,1000,1000,1000])

        # Enable/disable buttons will share a function.
        self.w_button_enable_all .clicked.connect(
            lambda checked, state = True: self.Set_All_Enable_States(state))
        self.w_button_disable_all.clicked.connect(
            lambda checked, state = False: self.Set_All_Enable_States(state))

        # Reload is a simple reloader to find any new extensions.
        self.w_button_reload .clicked.connect(self.Refresh)

        # Test buttons will share a function.
        self.w_button_test_all .clicked.connect(
            lambda checked, mode = 'all'     : self.Run_Tests(mode))
        self.w_button_test_selected .clicked.connect(
            lambda checked, mode = 'selected': self.Run_Tests(mode))
        self.w_button_retest_errors .clicked.connect(
            lambda checked, mode = 'errors'  : self.Run_Tests(mode))

        # Connect the local signal.
        self.test_result.connect(self.Handle_Test_Result)
        return
        
    
    def Handle_Signal(self, *flags):
        '''
        Respond to signal events.
        '''
        if 'save' in flags or 'save_as' in flags:
            self.Save()
        if 'file_system_reset' in flags:
            self.Refresh()
        return
    

    def Save(self):
        # Update the user content.xml with enabled/disables as needed.
        # TODO
        return

    
    def Refresh(self):
        '''
        Get the current set of found extensions by the file system,
        and fill in their list.
        '''
        # Save any current enables/disabled.
        self.Save()
        
        # Disable the buttons while working.
        self.w_button_test_all     .setEnabled(False)
        self.w_button_test_selected.setEnabled(False)
        self.w_button_retest_errors.setEnabled(False)
        
        # Queue up the thread to access the file system.
        # TODO: set this to return disabled extensions as well.
        # TODO: queue a local function which will gather these
        # names as well as details.
        self.Queue_Thread(File_Manager.Extension_Finder.Find_Extensions,
                          short_run = True,
                          callback_function = self._Refresh_pt2)
        return


    def _Refresh_pt2(self, extension_summary_list):
        '''
        Catch the File_Manager.Extension_Finder returned list.
        '''
        # Enable the buttons.
        self.w_button_test_all     .setEnabled(True)
        self.w_button_test_selected.setEnabled(True)
        self.w_button_retest_errors.setEnabled(True)
        
        # Reset the current list.
        self.list_model.clear()
        self.extension_item_dict.clear()
        # Clear the display.
        self.w_text_details.setText('')

        # Fill in the extensions list.
        # Sort by display name.
        for ext_summary in sorted(extension_summary_list, 
                                  key = lambda x: x.display_name):

            # Set up a list item.
            item = QStandardItem(ext_summary.display_name)

            # Annotate with the ext_summary for easy reference.
            item.ext_summary = ext_summary
            # Annotate as well with a list of checker log lines.
            item.check_result_log_text = None
            # Flag with no test result.
            item.test_success = None

            # Set up a checkbox for enable/disable.
            item.setCheckable(True)
            # Init it based on enabled state.
            self.Set_Item_Checked(item, ext_summary.enabled)

            # Color the item.
            self.Color_Item(item)

            # Set as readonly, to avoid double clicks bringing up an
            # edit prompt.
            item.setEditable(False)

            # Add to the list.
            self.list_model.appendRow(item)

            # Record to the dict.
            self.extension_item_dict[ext_summary.ext_id] = item

        return

    
    def Handle_selectionChanged(self, qitemselection = None):
        '''
        A different item was clicked on.
        '''
        # This takes a bothersome object that needs indexes
        # extracted, that then need to be converted to items,
        # instead of just giving the item like qtreewidget.
        new_item = self.list_model.itemFromIndex(qitemselection.indexes()[0])
        self.Change_Item(new_item)
        return


    def Handle_itemChanged(self, item):
        '''
        An item's checkbox was clicked, or it has an icon changed.
        Just want to catch the former case.
        '''
        self.Color_Item(item)
        # Update the display if this is the current item.
        if self.selected_item and item is self.selected_item:
            self.Update_Details()
        return


    def Change_Item(self, new_item):
        '''
        Change the selected item.
        '''
        # Note: it appears when the tree refreshes this event
        # triggers with None as the selection, so catch that case.
        if new_item == None:
            return

        # Record the item and update the details display.
        self.selected_item = new_item
        self.Update_Details()
        return


    def Update_Details(self):
        '''
        Update the detail text for the currently selected item.
        '''
        # Skip if called before any item was selected.
        if self.selected_item == None:
            return
        item = self.selected_item

        # Fill in the detail text.
        detail_lines = [
            'ID         : {}'.format(item.ext_summary.ext_id),
            'Name       : {}'.format(item.ext_summary.display_name),
            'Author     : {}'.format(item.ext_summary.Get_Attribute('author')),
            'Enabled    : {}'.format(self.Item_Is_Enabled(item)),
            'Description:',
            '',
            '{}'.format(item.ext_summary.Get_Attribute('description')),
            '',
            'Test result: {}'.format(
                'Success' if item.test_success == True
                else 'Failed' if item.test_success == False
                else '?'),
            ]

        # Add in any error log messages, if there are some.
        if item.check_result_log_text:
            detail_lines += [
            '',
            'Errors:' if item.check_result_log_text else '',
            '',
            item.check_result_log_text,
            ]

        # TODO: set up source readers and get file virtual paths.
        # TODO: append any check results with error messages.

        self.w_text_details.setText('\n'.join(detail_lines))
        return


    def Set_Item_Checked(self, item, state = True):
        '''
        Sets the check box state on an item.
        Checked to enable, unchecked to disable.
        '''
        if state == True:
            # (Sheesh it took forever to find where these flags
            #  are imported from.)
            item.setCheckState(QtCore.Qt.Checked)
        else:
            item.setCheckState(QtCore.Qt.Unchecked)

        # Update the display if this is the current item.
        if self.selected_item and item is self.selected_item:
            self.Update_Details()
            
        # Color the item.
        self.Color_Item(item)
        return


    def Handle_doubleClicked(self, index):
        '''
        An item was double-clicked; toggle its checkbox.
        '''
        item = self.list_model.itemFromIndex(index)
        self.Set_Item_Checked(item, not self.Item_Is_Enabled(item))
        return


    def Item_Is_Enabled(self, item):
        '''
        Returns True if the item is enabled (checkbox checked)
        else False.
        '''
        return bool(item.checkState())


    def Set_All_Enable_States(self, state = True):
        '''
        Set all extensions enabled or disabled, based on state.
        '''
        for item in self.extension_item_dict.values():
            self.Set_Item_Checked(item, state)
        return


    def Color_Items(self):
        '''
        Apply coloring to all items.
        '''
        for item in self.extension_item_dict.values():
            self.Color_Item(item)
        return


    def Color_Item(self, item):
        '''
        Apply coloring to the selected item.
        '''
        enabled = self.Item_Is_Enabled(item)
        success = item.test_success

        # Just color the text, not the background.
        if success == True:
            color = 'green'
        elif success == False:
            color = 'red'
        elif not enabled:
            color = 'gray'
        else:
            color = 'black'
        Set_Foreground_Color(item, color)
        
        # Can also indicate status by icons.
        if success == True:
            icon = 'SP_DialogApplyButton'
        elif success == False:
            icon = 'SP_DialogCancelButton'
        else:
            # Empty icon.
            #icon = None
            icon = 'SP_DialogCloseButton'

        # Note: this seems to annoyingly trigger itemChanged, which in
        # turn wants to recolor this. A bit of an unfortunate hack will
        # be used to bypass this problem (because dumb qt).
        self.list_model.itemChanged.disconnect(self.Handle_itemChanged)
        Set_Icon(item, icon)
        self.list_model.itemChanged.connect(self.Handle_itemChanged)
        return


    def Run_Tests(self, mode):
        '''
        Run loading tests on enabled extensions, filtering based on mode.

        * mode
          - String; 'all' to test all enabled extensions, 'selected'
            to test the currently selected extension (if enabled),
            'errors' to test enabled extensions that did not pass their
            prior test (or test all if there was no prior test).
        '''
        # Disable the buttons while working.
        self.w_button_test_all     .setEnabled(False)
        self.w_button_test_selected.setEnabled(False)
        self.w_button_retest_errors.setEnabled(False)

        # Clear prior test results for all disabled extensions.
        for ext_id, item in self.extension_item_dict.items():
            if not self.Item_Is_Enabled(item):
                item.check_result_log_text = None
                item.test_success = None

        # Pick out the extension ids being tested.
        if mode == 'selected':
            item = self.selected_item
            # Ignore if not enabled.
            if not self.Item_Is_Enabled(item):
                return
            extension_id_list = [item.ext_summary.ext_id]

        # Handle 'all' and 'errors' in a loop.
        else:
            extension_id_list = []

            # Find the checked items (enabled).
            for ext_id, item in self.extension_item_dict.items():
                if not self.Item_Is_Enabled(item):
                    continue

                # If looking only for extensions with errors or untested,
                # skip those that were flagged as successful.
                if mode == 'errors' and item.test_success:
                    continue

                # Record it.
                extension_id_list.append(ext_id)
                

        # Queue up the test as a thread, since it resets the file system.
        self.Queue_Thread(  self.Test_Thread,
                            extension_id_list,
                            # Need to save out the current extension enable state
                            # just before the thread kicks off.
                            prelaunch_function = self.Save,
                            callback_function = self._Run_Tests_pt2)
        return
    

    def Test_Thread(self, extension_id_list):
        '''
        Threaded tester. This will block access by other tabs to
        the file system while running.
        Emits 'test_result' signals as extension tests complete.
        '''
        # Reset the file system completely.
        # TODO: do this only if the extensions enabled are changed.
        # TODO: can alternately set up the file system to track all
        #  extensions, locally skipping those disabled or ignored,
        #  and just change that behavior during test loads, such that
        #  prior state is preserved (though a reset may be needed if
        #  actual enabled extensions are changed).
        File_System.Reset()

        # Temporary overrides of Settings so that all enabled
        #  extensions are loaded.
        # Include the current output extension in the check.
        old_ignore_extensions       = Settings.ignore_extensions
        old_ignore_output_extension = Settings.ignore_output_extension
        Settings.ignore_extensions       = False
        Settings.ignore_output_extension = False
    
        # Run the tests, collecting the logged messages.
        #ext_log_lines_dict = {}
        for ext_id in extension_id_list:
            log_lines = Check_Extension(ext_id, return_log_messages = True)
            #ext_log_lines_dict[ext_id] = log_lines

            # Make the gui more responsive during testing by
            # using a signal emitted to a function that catches results
            # and updates state as each extension finishes.
            self.test_result.emit(ext_id, '\n'.join(log_lines))


        # Restore the Settings.
        Settings.ignore_extensions       = old_ignore_extensions
        Settings.ignore_output_extension = old_ignore_output_extension

        # Reset the file system again, so it can restore old extension
        # finding logic.
        File_System.Reset()

        return #ext_log_lines_dict


    def Handle_Test_Result(self, ext_id, log_text):
        '''
        Function to catch emitted test_result signals.
        '''
        item = self.extension_item_dict[ext_id]

        # Record the lines to the extension for display.
        item.check_result_log_text = log_text

        # If there are any lines, then the extension failed its test,
        # else is passed.
        # Update the test result state.
        item.test_success = len(log_text) == 0
            
        # Color the item.
        self.Color_Item(item)
        
        # Update the current displayed extension if this item was the
        # one on display.
        if item is self.selected_item:
            self.Update_Details()
        return


    def _Run_Tests_pt2(self, ext_log_lines_dict):
        '''
        Wrap up after testing.
        '''
        # Enable the buttons.
        self.w_button_test_all     .setEnabled(True)
        self.w_button_test_selected.setEnabled(True)
        self.w_button_retest_errors.setEnabled(True)

        return
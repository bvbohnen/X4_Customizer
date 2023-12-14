
from Framework.Documentation import Doc_Category_Default
_doc_category = Doc_Category_Default('GUI')

from pathlib import Path
from lxml import etree as ET

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
    * w_button_use_defaults
    * w_button_undo_changes
    * w_button_reload
    * w_button_test_all
    * w_button_test_selected
    * w_button_retest_errors
    * w_hide_1
    * w_hide_2
    * w_hide_3
    * w_text_details
    * w_model_view
    * w_checkbox_word_wrap
    
    Attributes:
    * window
      - The parent main window holding this tab.
    * list_model
      - QStandardModel to run the w_model_view.
    * selected_item
      - QStandardModelItem that is currently selected.
    * extension_item_dict
      - Dict, keyed by extension name (lowercase folder), holding the
        QStandardModelItem representing it.
    * modified
      - Bool, True if an extention enable/disable state was changed
        since the last save.
    * original_enabled_states
      - Dict, keyed by extension name, holding the enabled state when
        first loading this tab.
      - This will only get set once, and then is left static on
        an subsequent reloads to avoid it getting overwritten with
        local changes to the content.xml file.
      - This is None until the first extension loading.
    '''
    # Set this tab as unique; disallow multiple to avoid them fighting
    # over what gets enabled/disabled.
    unique_tab = True
    
    # Signal from the Test_Thread to the Test_Result_Handler.
    # The thread will be in a qt thread domain, the handler in this
    # domain, so use a signal for this.
    # Messages are just those recorded by the Check_Extension log
    # lines, joined together, following the extension_name of the test.
    test_result = QtCore.pyqtSignal(str, str)

    def __init__(self, parent, window):
        super().__init__(parent, window)
        self.selected_item = None
        self.extension_item_dict = {}
        self.modified = False
        # Start this at None to indicate it hasn't been filled yet.
        self.original_enabled_states = None

        # Don't print args for threads; some lists are passed around.
        self.print_thread_args = False
                        
        # Set up initial, blank models.
        self.list_model  = QStandardItemModel(self)
        self.w_model_view.setModel(self.list_model)

        # Catch selection changes in the view.
        self.w_model_view.selectionModel().selectionChanged.connect(
            self.Handle_selectionChanged)
        # Catch double clicks, to toggle checkboxes more easily.
        self.w_model_view.doubleClicked.connect(
            self.Handle_doubleClicked)

        # Catch changes to item check boxes.
        self.list_model.itemChanged.connect(
            self.Handle_itemChanged)
        
        # Hide the invisible buttons, but set them to still take space.
        # These are used to center and shrink the active buttons.
        # See comments in File_Viewer_Window on this.
        # TODO: consider switching to spacers to handle this.
        for widget in [self.w_hide_1, self.w_hide_2, self.w_hide_3]:
            widget.setVisible(False)
            sizepolicy = widget.sizePolicy()
            sizepolicy.setRetainSizeWhenHidden(True)
            widget.setSizePolicy(sizepolicy)

        # Init the splitter to 1:1:1:1.
        self.hsplitter.setSizes([1000,1000,1000,1000])

        # Enable/disable buttons will share a function.
        self.w_button_enable_all .clicked.connect(
            lambda checked, mode = 'enable_all': self.Action_Change_Enable_States(mode))
        self.w_button_disable_all.clicked.connect(
            lambda checked, mode = 'disable_all': self.Action_Change_Enable_States(mode))
        self.w_button_use_defaults.clicked.connect(
            lambda checked, mode = 'use_defaults': self.Action_Change_Enable_States(mode))
        self.w_button_undo_changes.clicked.connect(
            lambda checked, mode = 'undo_changes': self.Action_Change_Enable_States(mode))
        

        # Reload to find any new extensions.
        self.w_button_reload .clicked.connect(self.Handle_Reload)

        # Test buttons will share a function.
        self.w_button_test_all .clicked.connect(
            lambda checked, mode = 'all'     : self.Run_Tests(mode))
        self.w_button_test_selected .clicked.connect(
            lambda checked, mode = 'selected': self.Run_Tests(mode))
        self.w_button_retest_errors .clicked.connect(
            lambda checked, mode = 'errors'  : self.Run_Tests(mode))

        # Catch changes to the word wrap checkbox.
        # Note: this starts checked while the text starts wrapped.
        self.w_checkbox_word_wrap.stateChanged.connect(
            self.Handle_Word_Wrap_Change)

        # Connect the local thread signal.
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
        '''
        Save current settings to the user content.xml.
        Note: extensions with ID overlap will only support the first
        one's state being saved (per x4 limitations).
        '''
        # Skip saving if there were no modifications.
        # This will also catch cases where extensions failed to load.
        if not self.modified:
            return
        self.modified = False
        '''
        Example format:
        <content>
          <extension id="test_mod" enabled="true"></extension>
          <extension id="hide_press_button_popups" enabled="false"></extension>
          <extension id="RebalancedShieldsAndMore" enabled="false"></extension>
        </content>
        '''
        # Create the content root element.
        content_root = ET.Element('content')
        # Record ids found, so that only the first extension gets added.
        ids_found = set()

        # Search through current extensions.
        # Do this in folder order, to match x4 behavior with id conflicts.
        for extension_name, item in sorted(self.extension_item_dict.items(),
                                           key = lambda kv: kv[0]):

            # Do this error check before checking if the enabled state
            # has changed, since any non-first extension of an ID will
            # have its content.xml element apply to the first extension
            # of that ID.
            # Note: this may not be a perfect behavior match to the game,
            # as it didn't seem worth thinking through thoroughly.
            ext_id = item.ext_summary.ext_id
            if ext_id in ids_found:
                self.window.Print(('Warning: Cannot save non-default enabled'
                                  ' state for "{}" due to ID "{}" conflict.'
                                  ).format(extension_name, ext_id))
            ids_found.add(ext_id)

            # Want to compare the current enable/disable status against the
            # extension's default. Can skip when they match.
            enabled = self.Item_Is_Enabled(item)
            if enabled == item.ext_summary.default_enabled:
                continue

            # Add the element for this extension.
            ext_node = ET.Element('extension', attrib = {
                'id' : ext_id,
                'enabled' : 'true' if enabled else 'false',
                })
            content_root.append(ext_node)

        # Write it out; this overwrites the user content.xml if it exists.
        content_xml_path = Settings.Get_User_Content_XML_Path()
        with open(content_xml_path, 'wb') as file:
            ET.ElementTree(content_root).write(
                file, 
                encoding = 'utf-8',
                xml_declaration = True,
                pretty_print = True)

        self.window.Print('Saved user content.xml enabled extensions.')
        return


    def Handle_Word_Wrap_Change(self, state):
        '''
        Handle changes to the checkbox state.
        '''
        # State is 2 for a checked box, 0 for unchecked.
        if state:
            # Standard is to wrap by widget width.
            self.w_text_details.setLineWrapMode(QtWidgets.QTextEdit.WidgetWidth)
        else:
            # Disable wrapping.
            self.w_text_details.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        return


    def Handle_Reload(self):
        '''
        The Reload button was clicked.
        Saves current enable statuses, then does a fresh search
        for extensions.
        '''
        self.Save()
        self.Refresh()
        return

    
    def Refresh(self):
        '''
        Get the current set of found extensions by the file system,
        and fill in their list.
        '''        
        # Disable the buttons while working.
        self.w_button_test_all     .setEnabled(False)
        self.w_button_test_selected.setEnabled(False)
        self.w_button_retest_errors.setEnabled(False)
        
        # Queue up the thread to access the file system.
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

        # If this is the first run, fill in the original_enabled_states.
        first_run = self.original_enabled_states == None
        if first_run:
            self.original_enabled_states = {}

        # Fill in the extensions list.
        # Sort by display name.
        # TODO: maybe optionally categorize by author.
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

            # Record the enabled state at startup, if this is the
            # first loading.
            if first_run:
                self.original_enabled_states[
                    ext_summary.extension_name] = ext_summary.enabled

            # Set up a checkbox for enable/disable.
            item.setCheckable(True)
            # Init it based on enabled state.
            self.Set_Item_Checked(item, ext_summary.enabled)

            # Color the item.
            self.Color_Item(item)

            # Add an item for the author name, to aid in sorting.            
            author_item = QStandardItem(ext_summary.Get_Attribute('author'))
            # Give this a reference to the main item, to be used
            # when it is selected (eg. double clicking the author name
            # to enable an extension).
            author_item.main_item = item
            
            # Set as readonly, to avoid double clicks bringing up an
            # edit prompt.
            item.setEditable(False)
            author_item.setEditable(False)

            # Add to the list.
            self.list_model.appendRow([item, author_item])

            # Record to the dict.
            self.extension_item_dict[ext_summary.extension_name] = item
            
        # Header names.
        # Pack into items so they can be centered.
        label_items = [QStandardItem(label) for label in ['Name','Author']]
        for index, label_item in enumerate(label_items):
            label_item.setTextAlignment(QtCore.Qt.AlignHCenter)
            self.list_model.setHorizontalHeaderItem(index, label_item)
        
        # Make sure the columns are wide enough.
        self.w_model_view.resizeColumnToContents(0)
        self.w_model_view.resizeColumnToContents(1)
            
        return

    
    def Handle_selectionChanged(self, qitemselection = None):
        '''
        A different item was clicked on.
        '''
        # This takes a bothersome object that needs indexes
        #  extracted, that then need to be converted to items,
        #  instead of just giving the item like qtreewidget.
        # Note: use index [0] for the main item even if author was clicked.
        # Note: from experimentation, selectionChanged bugs up if control
        #  is held when a currently selected item is clicked on, which
        #  will result in empty coordinates.
        #  To work around this, wrap the lookup in try/except.
        try:
            new_item = self.list_model.itemFromIndex(qitemselection.indexes()[0])
        except Exception:
            return
        self.Change_Item(new_item)
        return
    

    def Handle_doubleClicked(self, index):
        '''
        An item was double-clicked; toggle its checkbox.
        '''
        item = self.list_model.itemFromIndex(index)
        # Convert author items over to their main item.
        if hasattr(item, 'main_item'):
            item = item.main_item
        self.Set_Item_Checked(item, not self.Item_Is_Enabled(item))
        # Flag as modified to save changes.
        self.modified = True
        return


    def Handle_itemChanged(self, item):
        '''
        An item's checkbox was clicked, or it has an icon changed.
        Just want to catch the former case.
        '''
        # Convert author to main item.
        if hasattr(item, 'main_item'):
            item = item.main_item
        # Color it.
        self.Color_Item(item)
        # Update the display if this is the current item.
        if self.selected_item and item is self.selected_item:
            self.Update_Details()
        # Flag as modified to save changes.
        self.modified = True
        return


    def Change_Item(self, new_item):
        '''
        Change the selected item.
        '''
        # Note: it appears when the tree refreshes this event
        # triggers with None as the selection, so catch that case.
        if new_item == None:
            return
        # Skip if somehow the author item makes it to here.
        if hasattr(new_item, 'main_item'):
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

        # Give the version in x4 terms (int, adding decimal before last
        # two digits) and original (which ~40% of mods give in a wrong
        # format).
        version = item.ext_summary.Get_Attribute('version')
        try:
            # Note: in game, it seems to ignore letters, but don't
            #  spend the effort doing that here. TODO: maybe touch this up.
            # Go string->float->int, to deal with mistaken decimals.
            game_version = '{:.2f}'.format(int(float(version)) / 100)
        except Exception:
            game_version = '?'
        # If there is something odd about the version, add the original
        # string in parentheses.
        if game_version == '?' or '.' in version:
            game_version += ' ({})'.format(version)

        # Fill in the detail text.
        detail_lines = [
            # Grab the original folder, not the .folder attribute, to
            # get original case.
            'Folder           : {}'.format(item.ext_summary.content_xml_path.parent.name),
            'Name             : {}'.format(item.ext_summary.display_name),
            'Author           : {}'.format(item.ext_summary.Get_Attribute('author')),
            'ID               : {}'.format(item.ext_summary.ext_id),
            'Version          : {}'.format( game_version ),
            'Date             : {}'.format(item.ext_summary.Get_Attribute('date')),
            'Removable        : {}'.format(not item.ext_summary.Get_Bool_Attribute('save', True)),
            'Enabled          : {}'.format(self.Item_Is_Enabled(item)),
            'Default Enabled  : {}'.format(item.ext_summary.default_enabled),
            ]
        
        detail_lines += [
            'Test result      : {}'.format(
                'Success' if item.test_success == True
                else 'Failed' if item.test_success == False
                else '?'),
            ]

        description = item.ext_summary.Get_Attribute('description')
        if description:
            detail_lines += ['', description]

        def Get_Extension_For_ID(ext_id):
            '''
            Returns the first extension item found matching a given ext ID.
            Uses alphabetical extension_name ordering.
            '''
            for name, item in sorted(self.extension_item_dict.items(),
                                           key = lambda kv: kv[0]):
                if item.ext_summary.ext_id == ext_id:
                    return item
            return None

        def Format_Dependency_List(dep_list):
            '''
            Apply formatting to dependencies, looking up their mod
            display names from ids.
            '''
            ret_list = []
            for ext_id in dep_list:
                # Dependencies might be missing, so only fill in names
                # when found.
                item = Get_Extension_For_ID(ext_id)
                if not item:
                    dep_name = '?'
                else:
                    dep_name = item.ext_summary.display_name
                    # Swap to the original case id.
                    ext_id = item.ext_summary.ext_id
                ret_list.append('{} (id: {})'.format(dep_name, ext_id))
            return ret_list

        if item.ext_summary.soft_dependencies:
            detail_lines += [
            '',
            # TODO: list dependencies using extension display name, not id.
            'Optional dependencies :',
            # Indent with a couple spaces.
            '  ' + '\n  '.join(Format_Dependency_List(
                                item.ext_summary.soft_dependencies)),
            ]
            
        if item.ext_summary.hard_dependencies:
            detail_lines += [
            '',
            'Required dependencies :',
            # Indent with a couple spaces.
            '  ' + '\n  '.join(Format_Dependency_List(
                                item.ext_summary.hard_dependencies)),
            ]

        # Add in any error log messages, if there are some.
        if item.check_result_log_text:
            detail_lines += [
            '',
            'Test Log:' if item.check_result_log_text else '',
            '',
            # TODO: think about formatting this.
            # Can just use empty lines between messages so that they
            # are separated between word wrapped blocks.
            # (This may not be as useful if word wrap is turned off.)
            '\n\n'.join(item.check_result_log_text.splitlines()),
            ]

        # TODO: set up source readers and get file virtual paths.
        # TODO: append any check results with error messages.

        # Preserve approximate scrollbar position around the
        # text change. If the position goes out of range, setValue
        # should lock it in range.
        scroll_pos = self.w_text_details.verticalScrollBar().value()
        self.w_text_details.setText('\n'.join(detail_lines))
        self.w_text_details.verticalScrollBar().setValue(scroll_pos)

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
    

    def Item_Is_Enabled(self, item):
        '''
        Returns True if the item is enabled (checkbox checked) else False.
        If the item is None, returns False.
        '''
        if item == None:
            return False
        return bool(item.checkState())


    def Action_Change_Enable_States(self, mode):
        '''
        Set the enable/disable states on all extensions, based on mode.
        
        * mode
          - String, one of ['enable_all', 'disable_all', 
            'use_defaults', 'undo_changes']
        '''
        # These all are considered to modify the extensions.
        self.modified = True

        if mode == 'enable_all':
            # Turn all extensions on.
            for item in self.extension_item_dict.values():
                self.Set_Item_Checked(item, True)

        elif mode == 'disable_all':
            # Turn all extensions off.
            for item in self.extension_item_dict.values():
                self.Set_Item_Checked(item, False)

        elif mode == 'use_defaults':
            # Set all extensions to their content.xml default state.
            for item in self.extension_item_dict.values():
                self.Set_Item_Checked(item, item.ext_summary.default_enabled)

        elif mode == 'undo_changes':
            # Try to remove changes made during this gui session.
            for name, item in self.extension_item_dict.items():
                # Use the recorded flag at startup, or skip if there
                # is no record (eg. the extension was added after startup
                # and recognized through a refresh).
                enabled = self.original_enabled_states.get(name, None)
                if enabled == None:
                    continue
                self.Set_Item_Checked(item, enabled)
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
        for extension_name, item in self.extension_item_dict.items():
            if not self.Item_Is_Enabled(item):
                item.check_result_log_text = None
                item.test_success = None

        # Pick out the extension names being tested.
        extension_name_list = []
        if mode == 'selected':
            item = self.selected_item
            # Ignore if no item selected, or item is not enabled.
            # (This will end up passing through an empty test list,
            #  which is fine since it cleans up the button states and such.)
            if item != None and self.Item_Is_Enabled(item):
                extension_name_list.append(item.ext_summary.extension_name)

        # Handle 'all' and 'errors' in a loop.
        else:
            # Find the checked items (enabled).
            for extension_name, item in self.extension_item_dict.items():
                if not self.Item_Is_Enabled(item):
                    continue

                # If looking only for extensions with errors or untested,
                # skip those that were flagged as successful.
                if mode == 'errors' and item.test_success:
                    continue

                # Record it.
                extension_name_list.append(extension_name)
                

        # Queue up the test as a thread, since it resets the file system.
        self.Queue_Thread(  self.Test_Thread,
                            extension_name_list,
                            # Need to save out the current extension enable state
                            # just before the thread kicks off.
                            prelaunch_function = self.Save,
                            callback_function = self._Run_Tests_pt2)
        return
    

    def Test_Thread(self, extension_name_list):
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
        for extension_name in extension_name_list:
            log_lines = Check_Extension(extension_name, 
                                        return_log_messages = True)

            # Make the gui more responsive during testing by
            # using a signal emitted to a function that catches results
            # and updates state as each extension finishes.
            self.test_result.emit(extension_name, '\n'.join(log_lines))


        # Restore the Settings.
        Settings.ignore_extensions       = old_ignore_extensions
        Settings.ignore_output_extension = old_ignore_output_extension

        # Reset the file system again, so it can restore old extension
        # finding logic.
        File_System.Reset()

        return #ext_log_lines_dict


    def Handle_Test_Result(self, extension_name, log_text):
        '''
        Function to catch emitted test_result signals.
        '''
        item = self.extension_item_dict[extension_name]

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
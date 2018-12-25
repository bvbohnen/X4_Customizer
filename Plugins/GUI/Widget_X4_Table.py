'''
Widget(s) for viewing generated tables holding x4 data.
The initial test version of this will be just for weapons, with
some hooks for later generalization.
'''

from itertools import chain
from PyQt5 import QtWidgets

from ..Analyses import Print_Weapon_Stats
from ..Analyses.Live_Editor import Live_Editor
from Framework import Settings
from Framework import File_System

class Widget_X4_Table_Tree(QtWidgets.QTreeWidget):
    '''
    Tree view of the table entries, by name and possibly categorized.
    Clicking a plugin will signal a separate documentation
    window to display info (field names and data values).

    Attributes:
    * table_group
      - Edit_Table_Group object, holding 1 or more tables to display.
      - The first row holds column headers; the first column holds the
        preferred display name of the entry.
    * widget_item_info
      - QGroupBox widget that will display the item info.
      - Should be set up by the parent after initial init.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.currentItemChanged.connect(self.Handle_currentItemChanged)
        self.table_group = None
        return


    def Delayed_Init(self):
        '''
        Hooks up some widgets and actions after the gui has
        initialized fully, and all widgets are available.
        '''
        parent = self.parent
        # Note: this should all be cleaned up when setting up
        # a template window to be added to generated tabs.
        self.widget_item_info = parent.widget_weapons_info

        # It is a little tricky to hide the placeholder; it will
        # normally stop taking space when invisible.
        parent.widget_Hideme.setVisible(False)
        # Note: cannot edit the sizepolicy directly; need to pull it
        # out, modify it, and set it back to update properly.
        sizepolicy = parent.widget_Hideme.sizePolicy()
        sizepolicy.setRetainSizeWhenHidden(True)
        parent.widget_Hideme.setSizePolicy(sizepolicy)

        # Trigger button for loading the table.
        parent.widget_Table_Update.clicked.connect(self.Action_Make_Table_Group)
        
        # Force the initial splitter position, because qt designer is
        # dumb as a rock about splitters.
        # Give extra space to the right side, since it has 5 columns.
        # TODO: do this for other splitters, though they behave slightly
        # better so far.
        parent.hsplitter_weapons.setSizes([1,4])
        return

        
    # TODO: make some of this thread stuff generic, since it is
    # shared with script launching.
    def Action_Make_Table_Group(self):
        '''
        Update button was presssed; clear loaded files and rerun
        the plugin to gather the table group and set up the tree.
        '''
        # Do nothing if a thread is running.
        if self.parent.worker_thread.isRunning():
            return
        
        # Reset the Settings, so that it will do path checks again.
        Settings.Reset()
        # Ensure the settings are updated from gui values.
        self.parent.widget_settings.Store_Settings()

        # Clear out the file system from any prior run changes.
        # TODO: consider somehow setting up multiple file systems,
        # and using a temporary one for this.
        # TODO: consider having the game files hold three copies
        # of their xml: vanilla, patched with other extensions,
        # patched with all extensions; then it would be easier
        # to switch table sources; though perhaps having 3 file
        # systems would work just as well.
        File_System.Reset()


        # Tweak Settings based on radio buttons.
        # TODO: consider restoring settings back to originals, though
        # it shouldn't matter since anything that uses the settings
        # should be restoring them from gui selections anyway.
        # If vanilla only, ignore extensions.
        if self.parent.widget_Table_Vanilla_button.isChecked():
            Settings.ignore_extensions = True
        # If wanting the customizer extension to be included.
        elif self.parent.widget_Table_Customized_button.isChecked():
            Settings.ignore_extensions = False
            Settings.ignore_output_extension = False
        else:
            Settings.ignore_extensions = False
            Settings.ignore_output_extension = True

        
        #self.parent.worker_thread.Set_Function(
        #    Print_Weapon_Stats,
        #    return_tables = True)
        self.parent.worker_thread.Set_Function(
            Live_Editor.Get_Table_Group,
            'weapons')
        # Listen for the 'finished' signal.
        self.parent.worker_thread.finished.connect(self.Handle_Thread_Finished)

        # Disable the button while working.
        self.parent.widget_Table_Update.setEnabled(False)

        # Start the thread.
        self.parent.worker_thread.Start()

        return


    def Handle_Thread_Finished(self):
        '''
        Update widgets up after the plugin thread has finished.
        '''
        # Stop listening.
        self.parent.worker_thread.finished.disconnect(self.Handle_Thread_Finished)
        self.parent.widget_Table_Update.setEnabled(True)
        
        # Load in the table group from the thread results.
        self.table_group = self.parent.worker_thread.return_value
        # If something went wrong, None was returned; just stop here
        # and let whatever exception message get printed.
        if self.table_group == None:
            return

        # Clear out old table items.
        # Note: existing items cannot easily be reused, since their
        # tree structure might change (eg. it's not always a flat list).
        # Tree widgets make this easy.
        self.clear()

        # Set up the tree view.
        # Each table will form a separate top tree node.
        # Further categorization is possible within each table; TODO.
        for edit_table in self.table_group.Get_Tables():
            # Set up the header.
            header = QtWidgets.QTreeWidgetItem()
            # Attach the widget item to the parent tree.
            self.addTopLevelItem(header)            
            # Set the name in column 0.
            header.setText(0, edit_table.name)
            # If the label is clicked, it should get ignored elsewhere
            # due to not having extra annotations.

            # Construct the 2d table of edit_items.
            item_table = edit_table.Get_Table()
            # First row is column headers.
            column_headers = item_table[0]
            # Work through the rows, skipping the first.
            for index_m1, row in enumerate(item_table[1:]):
                
                # Make a new leaf item.
                item = QtWidgets.QTreeWidgetItem()
                # Attach the widget item to the parent.
                header.addChild(item)

                # Display using the first column item, generally
                # expected to be the display name.
                item.setText(0, row[0].Get_Value('current'))
            
                # For convenience, annotate the item with its table index.
                # This is real index (including the column headers row).
                item.table_index = index_m1 +1
                # Also annotate with the originating item table
                # and edit_table (in case one or the other is useful later).
                item.edit_table  = edit_table
                item.item_table  = item_table


        # Display info on the first item by default.
        # -Removed, needs update.
        #self.widget_item_info.Update(self.table[0], self.table[1])
            
        # Expand by default. TODO: maybe collapse by default.
        self.expandAll()
        return


    def Handle_currentItemChanged(self, new_item = None):
        '''
        A different item was clicked on.
        '''
        # Ignore if it doesn't have a table index (eg. could be a
        # category header).
        if not hasattr(new_item, 'table_index'):
            return

        # Pull out two lists: column headers and item data.
        fields    = new_item.item_table[0]
        items     = new_item.item_table[new_item.table_index]

        # Set the display widget to update.
        self.widget_item_info.Update(fields, items)
        return


class Widget_Edit_Item(QtWidgets.QLineEdit):
    '''
    Custom widget to handle items, trigging updates on a text change
    if the item was editable.
    '''
    def __init__(self, version, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.version = version
        self.item = None
        if version == 'edited':
            self.editingFinished.connect(self.Handle_editingFinished)


    def Set_Item(self, item):
        '''
        Change the Edit_Item or Display_Item (or None) attached
        to this widget. Updates text display and readonly state.
        Links to the item if this is the edited widget.
        '''        
        # Look up the item's value for this key, which will
        # match version names. This may return None for the
        # edited value if no edits are available. It may return
        # None for other versions if the field is unused by
        # the object for this row.
        # Note: the item itself may be None, in which case just
        # leave this blank. (This could come up if, eg. a patch
        # added an xml attribute that the vanilla version lacks.)
        if item == None:
            item_value = None
        else:
            item_value = item.Get_Value(self.version)
                
        if item_value != None:
            self.setText(item_value)
        else:
            self.setText('')

        if self.version == 'edited':
            # The edited widget will set a placeholder with the patched value,
            # and then may fill its text if there is any edited value in the
            # item.
            # -Removed; this doesn't quite work out; the edited field will
            # default to the patched value instead for easier display updates.
            #if item == None:
            #    patched_value = None
            #else:
            #    patched_value = item.Get_Value('patched')
            #self.setPlaceholderText(patched_value)

            # Set as editable if there is an item and it is not read only.
            if item != None and item.read_only == False:
                self.setReadOnly(False)
            else:
                self.setReadOnly(True)
                
            # Handle item/widget linking for the edited widget.
            # Disconnect old item, to be safe.
            if self.item != None:
                self.item.Set_Widget(None)

            # Two way link.
            self.item = item
            if item != None:
                item.Set_Widget(self)
        return


    def Handle_editingFinished(self):
        '''
        Handle cases when the user clicks out of a box.
        Note: this will trigger even if the widget is readonly and
        not actually clickable, for whatever reason.
        '''
        # Ignore if read only.
        if self.isReadOnly():
            return
        # TODO: Check if the text has actually been modified.
        # For now, just always update.
        # Send the text to the item.
        if self.item != None:
            # This will handle clearing and refreshing dependents.
            self.item.Set_Edited_Value(self.text())
        return
    

class Widget_X4_Table_Item_Info(QtWidgets.QGroupBox):
    '''
    Viewer for a selected table entry's attribute names with edit_items
    or display_items. This will have 5 columns: names, and values for
    vanilla, patched, edited, and current. Only the edited column
    will be interractive.

    Attributes:
    * widgets_dict
      - Dict of lists of widgets, intended for reuse.
      - Keys are ['fields','vanilla','patched','edited','current']
      - Fields:  QLabels with attribute name text.
      - Edited:  QLineEdit boxes, generally allowing user input
                 when associated with items that aren't read_only.
      - Vanilla, patched, current: QLineEdit read_only boxes displaying
                 static information.
      - Each list will be the same length, and will grow to the maximum
        amount needed at any display update.
      - The first widget in each list is a label.
      - Unused list entires are set invisible/innactive.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add column heading QLabels to start each list.
        self.widgets_dict = {
            'fields'  : [QtWidgets.QLabel('Fields')],
            'vanilla' : [QtWidgets.QLabel('Vanilla')],
            'patched' : [QtWidgets.QLabel('Patched')],
            'edited'  : [QtWidgets.QLabel('Edited' )],
            'current' : [QtWidgets.QLabel('Current')],
            }

        # Set up a new layout, grid style for multiple columns.
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        # Add the column labels.
        for key, widget_list in self.widgets_dict.items():
            self.Add_Layout_Widget(widget_list[0], 0, key)                
        return


    # Keys for the widget lists, in display order.
    widget_keys = ['fields','vanilla','patched','edited','current']
    def Add_Layout_Widget(self, widget, row, key):
        '''
        Adds a widget to the layout, selecting the column based
        on the key.
        '''
        column = self.widget_keys.index(key)
        self.layout().addWidget(widget, row, column)
        return


    def Update(self, fields, items):
        '''
        Update the display to a new item.

        * fields
          - List of names of the fields being displayed.
        * items
          - List of matching Edit_Items or Display_Items or None entries.
        '''
        '''
        Note: it appears that deleting widgets is a big headache, so updating
        the item display when the number of fields changes cannot be done
        by wiping and recreating row widgets.
        For a cleaner, though slightly more complicated, solution, this
        code will create rows as needed to capture all fields, then
        will hide excess rows leftover from prior displays, and finally
        will update the row widgets with the latest update info.
        '''

        # Start with row expansion, as needed.
        # Don't count the widget headers.
        while len(fields) > len(self.widgets_dict['fields'])-1:

            # Set up a new layout row with 5 columns.
            row = len(self.widgets_dict['fields'])

            # Loop over the lists to append to.
            for key, widget_list in self.widgets_dict.items():

                # Create a widget based on field name.
                if key == 'fields':
                    widget = QtWidgets.QLabel()
                else:
                    # TODO: maybe only use Widget_Edit_Item for the
                    #  edited column.
                    widget = Widget_Edit_Item(version = key)
                    widget.setReadOnly(True)

                # Record to the list and to the layout.
                widget_list.append(widget)
                self.Add_Layout_Widget(widget, row, key)


        # Hide any excess from the last update.
        # For now, this is easiest to do by hiding all widgets,
        # then displaying them again as they are filled in.
        for widget_list in self.widgets_dict.values():
            # Don't hide the column labels.
            for widget in widget_list[1:]:
                widget.setVisible(False)


        # Can now fill in the display info.
        for index, (field, item) in enumerate(zip(fields, items)):

            # Loop over the widget columns.
            for key, widget_list in self.widgets_dict.items():

                # Pick out the widget being updated.
                widget = widget_list[index +1]
                # Flip it to visible.
                widget.setVisible(True)

                # The fields widget gets field text directly.
                if key == 'fields':
                    widget.setText(field)
                    continue
                
                else:
                    # Others are handled through their class method.
                    widget.Set_Item(item)
                                           
        return

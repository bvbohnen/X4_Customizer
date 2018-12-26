'''
Widget(s) for viewing generated tables holding x4 data.
The initial test version of this will be just for weapons, with
some hooks for later generalization.
'''

from itertools import chain
from PyQt5 import QtWidgets, QtGui

from ..Analyses import Print_Weapon_Stats
from ..Transforms.Live_Editor import Live_Editor
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
    * last_selected_item_text
      - Text name of the last selected item.
      - Unlike the built-in QTreeWidget version, this will only hold
        active items, not table headers.
    * last_selected_item
      - The last selected item itself, associated with last_selected_item_text.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.currentItemChanged.connect(self.Handle_currentItemChanged)
        self.table_group = None
        self.last_selected_item_text = None
        self.last_selected_item = None
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
        # -Removed; want to keep the file system intact; game files
        #  have been updated to maintin the vanilla/patched/current xmls.
        #File_System.Reset()

        #-Removed; dont need buttons to select file version anymore.
        ## Tweak Settings based on radio buttons.
        ## TODO: consider restoring settings back to originals, though
        ## it shouldn't matter since anything that uses the settings
        ## should be restoring them from gui selections anyway.
        ## If vanilla only, ignore extensions.
        #if self.parent.widget_Table_Vanilla_button.isChecked():
        #    Settings.ignore_extensions = True
        ## If wanting the customizer extension to be included.
        #elif self.parent.widget_Table_Customized_button.isChecked():
        #    Settings.ignore_extensions = False
        #    Settings.ignore_output_extension = False
        #else:
        #    Settings.ignore_extensions = False
        #    Settings.ignore_output_extension = True

        # Reset the live editor table group that is be re-requested.
        # This will fill in new items that may get created by the
        # user script.
        self.parent.worker_thread.Set_Function(
            Live_Editor.Get_Table_Group,
            'weapons', 
            rebuild = True)
        # Listen for the 'finished' signal.
        self.parent.worker_thread.finished.connect(self.Handle_Thread_Finished)

        # Disable the button while working.
        self.parent.widget_Table_Update.setEnabled(False)

        # Start the thread.
        self.parent.worker_thread.start()

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
            self.parent.Print('Get_Table_Group failed.')
            return

        # Clear out old table items.
        # Note: existing items cannot easily be reused, since their
        # tree structure might change (eg. it's not always a flat list).
        # Tree widgets make this easy.
        self.clear()

        # Set up the tree view.
        # Each table will form a separate top tree node.
        # Further categorization is possible within each table; TODO.
        # Record the active items made into a dict, keyed by text label.
        item_dict = {}
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

                item_dict[item.text(0)] = item
            
                # For convenience, annotate the item with its table index.
                # This is real index (including the column headers row).
                item.table_index = index_m1 +1
                # Also annotate with the originating item table
                # and edit_table (in case one or the other is useful later).
                item.edit_table  = edit_table
                item.item_table  = item_table


        # Try to find the item matching the last selected item's text.
        if self.last_selected_item_text in item_dict:
            item = item_dict[self.last_selected_item_text]
            # Select it (highlights the line).
            self.setCurrentItem(item, True)
            # Set it for display.
            self.Handle_currentItemChanged(item)

        # Do a soft refresh, so that the current values of items
        # will update, and redraws the table.
        # TODO: maybe only be needed for reselecting an item (eg. nest
        # in the above 'if' statement) if script runs already call
        # the soft refresh reliably to handle current value changes.
        self.Soft_Refresh()

        # Display info on the first item by default.
        # -Removed, needs update.
        #self.widget_item_info.Update(self.table[0], self.table[1])
            
        # Expand by default if there is only one table.
        if len(self.table_group.Get_Tables()) == 1:
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

        # Record the text of this item, for possible restoration
        # across sessions or other useful lookups.
        self.last_selected_item_text = new_item.text(0)
        self.last_selected_item = new_item

        # Pull out two lists: column headers and item data.
        fields    = new_item.item_table[0]
        items     = new_item.item_table[new_item.table_index]

        # Set the display widget to update.
        self.widget_item_info.Update(fields, items)
        return


    def Soft_Refresh(self):
        '''
        Does a partial refresh of the table, resetting the 'current'
        values of items and redrawing the table.
        '''
        # TODO: offer a light refresh option, maybe, that only updates
        # item values (though may miss added items from plugins since
        # when the tables were built).
        Live_Editor.Reset_Current_Item_Values()
        # Send the selected item off for re-display, if there is
        # a selection.
        if self.last_selected_item != None:
            self.Handle_currentItemChanged(self.last_selected_item)
        return


'''
Notes on font/stylesheet headaches:

    - It seems that this widget only inherits font when created
      if it has a non-empty style sheet applied; later setFont calls
      to the parent don't reach the children.

    - Conditional styles (QLineEdit[readonly = "1"]{...}) do not seem
      to work; maybe examples are out of date.
      Or maybe this is nonfunctional for dynamic changes, and only
      works at init (though examples imply it working at runtime).
      Docs suggest removing and reapplying the stylesheet on
      a Qt property change.
      However, these still mess up the fonts even when not working as wanted.

    - Can maybe try psuedo states for ":read-only", though highlighting
      edited boxes won't work out so well.

    - Readonly items seem to somewhat preserve their starting font.
    - Modified items do not, even when also just changing background color.

    - Initial 'styleSheet()' is a blank string.
    - Setting a blank style sheet doesn't cause problems.

    - When just using the modified highlight, the very first
      setStyleSheet did not change the font, but removing the
      style (setStyleSheet('')) did.
      Packing the empty sheet in "QLineEdit{}" did not matter.

    - Maybe some fluff stylesheet term can help, acting as a placeholder
      so that an empty string is never used?
      - Didn't help.

    - Maybe ensure style properties are never removed.
      - Didn't help.

    - Spam clicking on cells also causes other oddities, like readonly
      cells with no item getting highlighted as modified somehow.

    - Maybe set styles to have two alternate versions, which both
      set the same fields?
      - Didn't help.

    - Supposition: whenever a widget has a stylesheet set that is not
      blank, some internal piping gets broken and the widget can no
      longer inherit font properly on later calls.
      Hard to see how this could be intentional, so consider a qt bug.  

    - Maybe look into palletes? or setBackgroundRole or similar?
      https://wiki.qt.io/How_to_Change_the_Background_Color_of_QWidget
      Success!  finally...
'''

class Widget_Edit_Item(QtWidgets.QLineEdit):
    '''
    Custom widget to handle items, trigging updates on a text change
    if the item was editable.

    Attributes:
    * version
      - String, version of the item value this widget displays.
    * item
      - Display_Item or Edit_Item attached to this widget.
      - Currently only 'edited' version widgets will have an item linked.
    * stylesheet
      - String, the current style sheet text.
    '''
    # Some static style terms.
    # This is a little too dark: 'background: lightGray;'
    #style_read_only = 'background: lightGray;'
    # These adjustments are surprisingly swingy; 250 is barely
    # darkened, 240 is super darkened. 247 seems okay.
    #style_read_only     = 'background: rgb(247, 247, 247);'
    #style_modified      = 'border-width: 1px; border-style: solid; border-color: red;'
    #style_modified  = 'background: lightBlue;'
    
    # Switching to use palletes; stylesheets are too bugged up in qt.
    pallete_standard = QtGui.QPalette()
    pallete_readonly = QtGui.QPalette()
    pallete_modified = QtGui.QPalette()
    pallete_mod_read = QtGui.QPalette()

    pallete_standard.setColor(QtGui.QPalette.Base, QtGui.QColor('white'))
    pallete_standard.setColor(QtGui.QPalette.Text, QtGui.QColor('black'))

    pallete_readonly.setColor(QtGui.QPalette.Base, QtGui.QColor(247, 247, 247))
    pallete_readonly.setColor(QtGui.QPalette.Text, QtGui.QColor('black'))

    pallete_modified.setColor(QtGui.QPalette.Base, QtGui.QColor('white'))
    pallete_modified.setColor(QtGui.QPalette.Text, QtGui.QColor('red'))
    
    pallete_mod_read.setColor(QtGui.QPalette.Base, QtGui.QColor(247, 247, 247))
    pallete_mod_read.setColor(QtGui.QPalette.Text, QtGui.QColor('red'))


    def __init__(self, parent, version, **kwargs):
        super().__init__(parent, **kwargs)
        self.version = version
        self.item = None
        #self.stylesheet = ''
        self.modified = False
        self.readonly = False
        self.pallete  = None

        if version == 'edited':
            self.editingFinished.connect(self.Handle_editingFinished)

        # For coloring modified text, need to hook into two places,
        #  textChanged for setText events, and something else for
        #  when the user edits the text (for some reason that is not
        #  captured by textChanged, though its documentation says/implies
        #  that it should be).
        self.textChanged.connect(self.Color_Modified_Items)
        self.editingFinished.connect(self.Color_Modified_Items)

        # Ran into issues dynamically changine the style sheet, since
        # apparently the font changes are applied to the style sheet
        # and get overwritten.
        # Instead, try out a more complex style sheet with conditional
        # properties for some display options, and only edit those
        # conditional bits.
        #old_sheet = self.styleSheet()
        #style_sheet = """
        #QLineEdit[readonly = "1"]{
        #    background-color: rgb(247, 247, 247);
        #}
        #QLineEdit[modified = "1"]{
        #    border-width: 1px; border-style: solid; border-color: red;
        #}
        #"""
        #self.setProperty('readonly','1')
        #self.setProperty('modified','0')
        #self.setStyleSheet(style_sheet)
        #old_sheet = self.styleSheet()
        

        self.setAutoFillBackground(True)        
        # Default to readonly, after style is set up.
        self.setReadOnly(True)
         
        return


    #def Add_Style(self, style_text):
    #    '''
    #    Add the given text to the style sheet, if not present already.
    #    Text should end in a ';' always.
    #    '''
    #    if style_text not in self.stylesheet:
    #        self.stylesheet += style_text
    #    #self.setStyleSheet(self.stylesheet)
    #    return
    #
    #
    #def Remove_Style(self, style_text):
    #    '''
    #    Remove the given text from the style sheet.
    #    '''
    #    if style_text in self.stylesheet:
    #        self.stylesheet = self.stylesheet.replace(style_text,'')
    #    #self.setStyleSheet(self.stylesheet)
    #    return
    

    def Update_pallete(self):
        '''
        Based on the read-only and modified state, sets a pallete
        for this widget.
        '''
        if self.readonly == False and self.modified == False:
            pallete = self.pallete_standard
        if self.readonly == False and self.modified == True:
            pallete = self.pallete_modified
        if self.readonly == True  and self.modified == False:
            pallete = self.pallete_readonly
        if self.readonly == True  and self.modified == True:
            pallete = self.pallete_mod_read

        # Note: the pallete attribute in the documentation doesn't
        # seem to be accessible easily, so store a local copy.
        if self.pallete != pallete:
            self.pallete = pallete
            self.setPalette(pallete)
        return


    def setReadOnly(self, readonly = True):
        '''
        Set or disable the 'read only' state on this box.
        This may also attempt to grey out read only boxes for visual
        clarity.
        '''
        super().setReadOnly(readonly)
        # TODO: how to dim the widget?
        # Using setEnabled(not readonly) will do the job, but it makes
        # the text unselectable (so it can't copy/paste or drag over to
        # the editable boxes), and greys a bit too much.
        # -Look into using a style sheet.
        if readonly:
            #self.Add_Style(self.style_read_only)
            #self.setProperty('readonly','1')
            self.readonly = True
        else:
            #self.Remove_Style(self.style_read_only)
            #self.setProperty('readonly','0')
            self.readonly = False
            
        #self.ensurePolished()
        self.Update_pallete()
        # TODO: highlight text in some way for modified fields.
        return


    def Set_Item(self, item):
        '''
        Change the Edit_Item or Display_Item (or None) attached
        to this widget. Updates text display and readonly state.
        Links to the item if this is the 'edited' widget.
        '''
        # Handle linking to edited versions first, before updating
        # text, so that modified text coloring will work correctly.
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

            # Two way link.
            self.item = item
            if item != None:
                item.Set_Widget(self)
        
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


    def setText(self, text):
        '''
        Wrapper on setText that will call Color_Modified_Items, because
        the textChanged doesn't follow its documentation and catch
        such calls on its own.
        '''
        super().setText(text)
        self.Color_Modified_Items()
        return


    def Color_Modified_Items(self):
        '''
        This should be called whenever the text changes.
        Will color the box and/or text if the linked item is in a modified
        state.
        '''
        # In case this is called without an item attached, return
        # early with no highlight.
        if not getattr(self, 'item', None):
            self.modified = False
            #self.Remove_Style(self.style_modified)

        # Note: readonly items can still be modified in the case of display
        # values that source from modified values, so only check the
        # modified state.
        elif self.item.Is_Modified():
            #self.Add_Style(self.style_modified)
            #self.setProperty('modified','1')
            self.modified = True
        else:
            #self.Remove_Style(self.style_modified)
            #self.setProperty('modified','0')
            self.modified = False
            
        #self.ensurePolished()
        self.Update_pallete()
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
            'patched' : [QtWidgets.QLabel('Diff Patched')],
            'edited'  : [QtWidgets.QLabel('Edited' )],
            'current' : [QtWidgets.QLabel('Post Script')],
            }

        # Set up a new layout, grid style for multiple columns.
        layout = QtWidgets.QGridLayout(self)
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

        # Prevent vertical stretching; looks bad before a table
        # is loaded and the headers are stretched.
        # -Removed; this failed to shrink the items. Need to use the backup
        # approach of hiding them.
        #widget.sizePolicy().setVerticalPolicy(QtWidgets.QSizePolicy.Minimum)
        #widget.sizePolicy().setVerticalStretch(QtWidgets.QSizePolicy.Minimum)
        #widget.sizePolicy().setHorizontalPolicy(QtWidgets.QSizePolicy.Minimum)
        #widget.sizePolicy().setHorizontalStretch(QtWidgets.QSizePolicy.Minimum)

        # Start out hidden.
        widget.setVisible(False)
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
                    widget = QtWidgets.QLabel(self)
                else:
                    # TODO: maybe only use Widget_Edit_Item for the
                    #  edited column.
                    # Give these the parent right away, to maybe help
                    # with a problem where some don't inherit font.
                    widget = Widget_Edit_Item(self, version = key)

                # Record to the list and to the layout.
                widget_list.append(widget)
                self.Add_Layout_Widget(widget, row, key)


        # Hide any excess from the last update.
        # For now, this is easiest to do by hiding all widgets,
        # then displaying them again as they are filled in.
        for widget_list in self.widgets_dict.values():
            for widget in widget_list:
                widget.setVisible(False)


        # If there are any items being displayed, unhide the column headers.
        if fields:
            for widget_list in self.widgets_dict.values():
                widget_list[0].setVisible(True)

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

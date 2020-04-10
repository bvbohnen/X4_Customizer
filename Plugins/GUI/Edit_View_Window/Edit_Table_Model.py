
from PyQt5 import QtWidgets, QtCore, QtGui
#from .Edit_Item import Widget_Edit_Item
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush
from .Q_Item_Group import Q_Item_Group

class Edit_Table_Model(QStandardItemModel):
    '''
    Model container for an Edit_Tree_View, to interract with
    a table view widget.
    This will have two variations:
    1) Single object display, columns as versions, rows as items.
    2) Multi object display, columns as  items and versions, rows as objects.

    Attributes:
    * qt_view
      - Table view in qt showing this model.
    * column_visibility_dict
      - Dict, keyed by widget_dict key, holding a Bool: True to display
        the column, False to hide it.
    * current_object_view
      - The Object_View currently displayed.
    * current_edit_table
      - The Edit_Table currently displayed, or None if not in group_mode.
    * button_group
      - QButtonGroup holding the mode buttons; used to create
        a single changed signal.
    '''
    # Keys for the widget lists, in display order.
    widget_keys = ['fields','vanilla','patched','edited','current']

    column_keys    = ['vanilla','patched','edited','current']
    column_headers = ['Vanilla','Diff.Patched','Edited','PostScript']

    def __init__(self, window, qt_view):
        super().__init__(window)
        self.window = window
        self.current_object_view = None
        self.current_edit_table = None
        self.qt_view = qt_view
        
        # Set the column default headers.
        self.setHorizontalHeaderLabels(self.column_headers)
        # Set the columns to stretch to fit the space.
        self.qt_view.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch )
        # Allow drag/dropping.
        self.qt_view.setAcceptDrops(True)
        
        # Display all columns by default.
        # This provides some dummy terms for when the window
        # initializes these one at a time (which then do an
        # update call that needs all of them filled in).
        self.column_visibility_dict = {x:True for x in self.column_keys}

        self.itemChanged.connect(self.Handle_itemChanged)

        # Handle radio button changes.
        # Join these buttons into a group, so one signal can be caught.
        self.button_group = QtWidgets.QButtonGroup()
        self.button_group.addButton(self.window.button_view_object)
        self.button_group.addButton(self.window.button_view_table)
        self.button_group.addButton(self.window.button_view_table_flip)
        # Always do a full redraw.
        self.button_group.buttonClicked.connect(self.Redraw)
        return
    

    def Action_Checkbox_Changed(self, state, column):
        '''
        Hide or show columns based on checkbox state.
        Note: state is 0 for unchecked, 2 for checked, with 1 reserved
        for intermediate on tristate boxes (not used here).
        '''
        # Update the visility tracking dict.
        self.column_visibility_dict[column] = bool(state)
        # Pass to another function to handle showing/hiding columns.
        self.Update_Column_Visibilities()
        return

    
    def Is_In_Group_Mode(self):
        '''
        Returns True if the display is set for group mode.
        '''
        if(self.window.button_view_table.isChecked() 
        or self.window.button_view_table_flip.isChecked()):
            return True
        return False


    def Is_Flipped_Orientation(self):
        '''
        Returns True if the display is set to flip the table.
        '''
        return self.window.button_view_table_flip.isChecked()


    def Update_Column_Visibilities(self):
        '''
        Updates the visibility state of widgets in each column
        based on checkbox state.
        '''
        if not self.Is_In_Group_Mode():
            # Standard mode has 4 columns, by version.
            for index, column_name in enumerate(self.column_keys):
                # If this column checkbox is checked, unhide, else hide.
                self.qt_view.setColumnHidden(
                    index, not self.column_visibility_dict[column_name])
        else:
            # Group mode will show all columns, for now.
            for col in range(self.columnCount()):
                self.qt_view.setColumnHidden(col, False)

        # Row/col widths and space changed, so resize.
        self.Resize_Cells()
        return
    

    def Handle_itemChanged(self, item):
        '''
        This is called when an item's data is changed, either at creation
        (should ignore) or by user editing (should catch).
        
        '''
        # Ignore during the object draw process.
        if self.current_object_view == None:
            return
        
        # Skip generic items.
        # These can show up when there are missing references, with
        #  the table auto inserting dummy items into those cells.
        if not hasattr(item, 'q_item_group'):
            return

        # Pass this off to the item group, which will udpate this
        # item and any others attached to the same Edit_Item.
        item.q_item_group.Value_Changed(item)
        return


    def Update(self, object_view, skip_if_same = True):
        '''
        Update the display to a new item.

        * object_view
          - The Object_View that will supply labels and items to display.
        * skip_if_same
          - Bool, skip the Update if the object_view is the same as
            the prior one.
        '''
        # Handle the standard, single-object view.
        if not self.Is_In_Group_Mode():
            
            # If the object_view hasn't changed, and the group_mode hasn't
            # changed, then this can probably skip the Update.
            # Note: another skip is present below for group view.
            if(skip_if_same 
            and object_view is self.current_object_view
            and self.current_edit_table == None):
                return

            # Clear any old edit table.
            self.current_edit_table = None

            # Set this to None while drawing, to prevent spurious redraws.
            self.current_object_view = None

            # Release prior q items safely.
            self.Release_Items()
        

            # Gather the dict, keyed by version, holding item lists.
            version_items_list_dict = object_view.Get_Display_Version_Items_Dict()

            # From this, get the labels and descriptions for each row.
            # Some rows may be partially None, so avoid those when picking
            #  sampled items.
            labels       = []
            descriptions = []
            for item_row in zip(*version_items_list_dict.values()):
                for item in item_row:
                    if item != None:
                        break
                labels      .append(item.display_name)
                descriptions.append(item.description)
            row_count = len(labels)
        
            # Resize to the right number of rows.
            # Could also clear(), but that would require regenerating rows
            # and also destroys the column headers.
            # TODO: figure out why this resets the scroll bar to the top,
            # or a way to preserve the bar.
            self.setRowCount(row_count)
            self.setColumnCount(len(self.column_headers))

            # Set the column headers, in case a group view changed them.
            self.setHorizontalHeaderLabels(self.column_headers)
            # Set the columns to stretch to fit the space.
            self.qt_view.horizontalHeader().setSectionResizeMode(
                QtWidgets.QHeaderView.Stretch )
        
            # Apply the labels.
            label_list = []
            for row in range(row_count):
                label_item = QStandardItem(labels[row])
                label_item.setToolTip(descriptions[row])
                self.setVerticalHeaderItem(row, label_item)
                label_list.append(label_item)
               

            # Can now fill in the display info.
            for row in range(row_count):
                # Note the q_item_group for use below.
                q_item_group = None
                for col, version in enumerate(self.column_keys):
              
                    # Grab the right item for the column.
                    # Top level object items will always match across versions,
                    # but references can mismatch.
                    item = version_items_list_dict[version][row]

                    # If there is no underlying item, such as when a reference
                    # is missing, can leave the spot blank.
                    # TODO: maybe disable these cells?
                    if item == None:
                        continue

                    # If the item has no q_item_group, make one.
                    if not item.q_item_group:
                        item.q_item_group = Q_Item_Group(item)

                    # Get a new QStandardItem from the group.
                    q_item_group = item.q_item_group
                    q_item = q_item_group.New_Q_Item(version)
                    self.setItem(row, col, q_item)

                # Set the label color for the group.
                # TODO: localize this more to this table in some way.
                foreground, background = q_item_group.Get_Label_Color()
                label_list[row].setForeground(foreground)
                label_list[row].setBackground(background)
                

        # Handle a group view.
        else:
            # Instead of the object, want to look up the Edit_Tree_View
            # that the object was pulled from.
            edit_tree = self.window.tree_model.edit_tree

            # From this, can generate an edit_table_view, which has
            # several subtables, to one of which this object belongs.
            edit_table_group = edit_tree.Convert_To_Table_Group()

            # Find the table with this object.
            edit_table = edit_table_group.Get_Table_With_Object(object_view)


            # Possibly skip the update.
            if self.current_edit_table != None:            
                # If the table is the same, can skip early, just updating the
                # selected object.
                if skip_if_same and edit_table is self.current_edit_table:
                    self.current_object_view = object_view
                    return

            # Update the table ref.
            self.current_edit_table = edit_table

            # Set object to None while drawing, to prevent spurious redraws.
            self.current_object_view = None

            # Release prior q items safely.
            self.Release_Items()


            # The table contains a row with column labels, and then
            # rows with the items (one object per row).
            # Here, each item can be broken into 4 subcolumns, one
            # per version of the item.
            # TODO: think about labelling.

            # For this initial version, just display edited values.
            version = 'edited'
            # This is a list of lists style table.
            # Note: avoid editing this, since it was cached.
            orig_table = edit_table.Get_Table(version = version)


            # Copy and flip the table, based on setting.
            # The copy will get cells popped off when picking out
            # labels, so copying makes it safe to edit.
            orig_row_count = len(orig_table)
            orig_col_count = len(orig_table[0])

            # Set the new dims.
            if self.Is_Flipped_Orientation():
                new_row_count = orig_col_count
                new_col_count = orig_row_count
            else:
                new_row_count = orig_row_count
                new_col_count = orig_col_count

            # Size the new table.
            table = [[None]*new_col_count for x in range(new_row_count)]

            # Copy indices.
            for row in range(orig_row_count):
                for col in range(orig_col_count):
                    if self.Is_Flipped_Orientation():
                        table[col][row] = orig_table[row][col]
                    else:
                        table[row][col] = orig_table[row][col]


            # Pick out horizontal and vertical headers, pulling them
            # out of the table if found.
            # Fill blank lines where headers are missing.
            horizontal_headers = []
            vertical_headers   = []

            # Check row 0 for labels or None.
            # Note: if this is not a label row, it may still have
            # a label in the first entry from column labels, so
            # this check will verify all row cells.
            if all(isinstance(x,str) or x == None for x in table[0]):
                # Move the headers out of the table.
                horizontal_headers = table.pop(0)

            # Check col 0 for labels.
            # Since any horizontal labels have been removed, this can
            # safely sample the first column of the first row.
            if isinstance(table[0][0], str):
                # Do a pass to move the column entries over.
                for row_items in table:
                    vertical_headers.append(row_items.pop(0))

            # Check the size of the final table, with only items.
            num_rows = len(table)
            num_cols = len(table[0])

            # If headers were found on both axes, pop off the first
            # element, which was the top left unused cell.
            if vertical_headers and horizontal_headers:
                vertical_headers  .pop(0)
                horizontal_headers.pop(0)
                # Verify sizing.
                assert len(vertical_headers)   == num_rows
                assert len(horizontal_headers) == num_cols
                
            # Fill in header defaults; these will be used to overwrite
            # old labels in the table.
            # TODO: change defaults to use the first row/col data, typically
            # a name, after string conversion. (Will not update it the
            # text ref is changed, but that's okay.)
            if not vertical_headers:
                if horizontal_headers and horizontal_headers[0] == 'Name':
                    vertical_headers = [x[0].Get_Value('current')
                                        for x in table]
                else:
                    vertical_headers = ['']*num_rows
            if not horizontal_headers:
                if vertical_headers and vertical_headers[0] == 'Name':
                    horizontal_headers = [x.Get_Value('current')
                                        for x in table[0]]
                else:
                    horizontal_headers = ['']*num_cols
                

            # Resize this model.
            self.setRowCount   (num_rows)
            self.setColumnCount(num_cols)
            
            # Horizontal headers should be printed vertically for this; need to
            # use modify the QHeaderView's panter to set this up.
            # Example (don't use this; it looks way overbloated):
            # https://stackoverflow.com/questions/30633020/changing-text-direction-in-qtableview-header
            
            # Apply the headers.
            # Pack into new QStandardItems, to lay groundwork for
            # coloring later, and also to clear coloring from
            # the object view.
            # TODO: extract tooltips from cells, and also apply coloring,
            # probably after the cell items are set up.
            #horizontal_headers = [QStandardItem(x) for x in horizontal_headers]
            #vertical_headers   = [QStandardItem(x) for x in vertical_headers]

            for index, name in enumerate(horizontal_headers):
                self.setHorizontalHeaderItem(index, QStandardItem(name))
            for index, name in enumerate(vertical_headers):
                self.setVerticalHeaderItem(index, QStandardItem(name))

            
            # Set the columns to be user adjustable, and also to be
            # controllable by local resize commands.
            self.qt_view.horizontalHeader().setSectionResizeMode(
                QtWidgets.QHeaderView.Interactive )


            # Loop over the table to set up items.
            for row, row_items in enumerate(table):
                for col, item in enumerate(row_items):

                    # If there is no underlying item, such as when a reference
                    # is missing, can leave the spot blank.
                    # TODO: maybe disable these cells?
                    if item == None:
                        continue

                    # If the item has no q_item_group, make one.
                    if not item.q_item_group:
                        item.q_item_group = Q_Item_Group(item)

                    # Get a new QStandardItem from the group.
                    q_item_group = item.q_item_group
                    q_item = q_item_group.New_Q_Item(version)
                    # Place it in the table.
                    self.setItem(row, col, q_item)
                    

        # For some reason the column visibilities get messed up by
        # the model when items are changed (not even in a consistent
        # way), so fix them here.
        self.Update_Column_Visibilities()
        
        # Record the object view, which also turns on change detection.
        self.current_object_view = object_view
        
        # Expand rows based on their contents, particularly to make
        # descriptions readable.
        # Side note: this appears to bug up on the first display, not
        # giving enough room, until an item is not-edited or the
        # object is changed. Completely unclear why qt does this.
        self.Resize_Cells()

        return

    
    def Redraw(self):
        '''
        Redraw this model from the current_object_view.  To be used
        when object references are changed, so that cells can be
        swapped to their new items.
        Skips if called on a window that hasn't drawn anything yet.
        '''
        if self.current_object_view != None:
            self.Update(self.current_object_view, skip_if_same = False)
        return


    def Resize_Cells(self):
        '''
        Resizes the table rows and columns to their contents.
        For use when descriptions or other large text blocks are changed,
        but can be called somewhat blindly on changes.
        '''
        # In group mode, try to limit how wide columns can be, else
        # tags or descriptions tend to blow out their width excessively.
        if self.Is_In_Group_Mode():
            # Set a maximum.
            # Values seems to be points; assuming 12 pt font is 12 wide,
            # and names go up to ~40 characters, can go up that far,
            # but it feels overkill. Limit to 25 for now, revisit later.
            # TODO: revisit this if finding a way to get the text to
            # wrap without word spaces; currently it just puts ellipses
            # and the cell cannot be selected to pop out and view/copy
            # its text if it is readonly.
            self.qt_view.horizontalHeader().setMaximumSectionSize(25*12)
            self.qt_view.resizeColumnsToContents()
        else:
            # -1 sets this back to default.
            self.qt_view.horizontalHeader().setMaximumSectionSize(-1)
            # Don't call resizeColumnsToContents, else with 2+ columns
            # it will shrink them down instead of stretching to fit
            # the screen.

        # Resize rows after columns, to capture word wrapped cells.
        self.qt_view.resizeRowsToContents()
        return


    def Release_Items(self):
        '''
        Prepare this model for deletion by detaching all items produced
        by a Q_Item_Group, such that they can reused by other tabs.
        Items will be replaced with generic QStandardItems, to
        preserve scroll bar position.
        '''
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                # Sample the item and see if it has an attached
                # q_item_group.
                item = self.item(row, col)

                # Skip if the spot was blank.
                # TODO: it is unclear on why sometimes the table seems
                # to insert dummy items into unused slots, and other
                # times returns None.
                if item == None:
                    continue
                # Skip generic items.
                if not hasattr(item, 'q_item_group'):
                    continue

                # Remove the item.
                item = self.takeItem(row, col)
                # Replace it with a placeholder dummy.
                self.setItem(row, col, QStandardItem())
        return
    

    def mimeData(self, qmodelindex):
        '''
        Customize the dragged item to copy its text.
        '''
        item = self.itemFromIndex(qmodelindex[0])
        text = item.text()
        # Run whatever standard constructor for the mimedata.
        mimedata = super().mimeData(qmodelindex)
        # The default mimedata doesn't fill its text field, so
        # fill it here.
        mimedata.setText(text)
        return mimedata


    def dropMimeData(self, mimedata, dropaction, row, col, item_index):
        '''
        Handle drops of mimedata. This is expected to just copy
        text and accept the drop.
        '''
        # Note: the row/col seem to always to -1,-1, and the
        # "parent" in documentation is a QModelIndex for the item.
        # Note: dropaction is just a constant, like '1'; ignore
        # for now.
        item = self.itemFromIndex(item_index)
        if item != None:
            # Copy over the text set by mimeData.
            text = mimedata.text()
            # This should cause the item to signal that its value
            # changed, will appropriate following model updates.
            item.setText(text)
            return True
        return False


from PyQt5 import QtWidgets, QtCore, QtGui
#from .Edit_Item import Widget_Edit_Item
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush
from .Q_Item_Group import Q_Item_Group

class Edit_Table_Model(QStandardItemModel):
    '''
    Model container for an Edit_Tree_View, to interract with
    a table view widget.

    Attributes:
    * qt_view
      - Table view in qt showing this model.
    * column_visibility_dict
      - Dict, keyed by widget_dict key, holding a Bool: True to display
        the column, False to hide it.
    * current_object_view
      - The Object_View currently displayed.
    '''
    # Keys for the widget lists, in display order.
    widget_keys = ['fields','vanilla','patched','edited','current']

    column_keys    = ['vanilla','patched','edited','current']
    column_headers = ['Vanilla','Diff.Patched','Edited','PostScript']

    def __init__(self, window, qt_view):
        super().__init__(window)
        self.window = window
        self.current_object_view = None
        self.qt_view = qt_view
        
        # Set the column headers.
        self.setHorizontalHeaderLabels(self.column_headers)
        # Allow drag/dropping.
        self.qt_view.setAcceptDrops(True)
        
        # Set the columns to resize.
        # This is an annoying chain of lookups, in keeping with
        # model/views being overcomplicated.
        self.qt_view.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch )

        # Display all columns by default.
        # This provides some dummy terms for when the window
        # initializes these one at a time (which then do an
        # update call that needs all of them filled in).
        self.column_visibility_dict = {x:True for x in self.column_keys}

        self.itemChanged.connect(self.Handle_itemChanged)
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


    def Update_Column_Visibilities(self):
        '''
        Updates the visibility state of widgets in each column
        based on checkbox state.
        '''
        for index, column_name in enumerate(self.column_keys):
            # If this column checkbox is checked, unhide, else hide.
            self.qt_view.setColumnHidden(
                index, not self.column_visibility_dict[column_name])
        return
    
    
    def Handle_Widget_Redraw_Request(self):
        '''
        Redraw the window when a widget requests it.
        For use when item references change.
        '''
        # This has a desire to trigger during its own draw process
        # when setting widget text; to suppress, don't redraw when
        # current_object_view is None, and make sure it is None
        # during drawing.
        if self.current_object_view != None:
            self.Update(self.current_object_view)
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


    def Update(self, object_view):
        '''
        Update the display to a new item.

        * object_view
          - The Object_View that will supply labels and items to display.
        '''
        # Set this to None while drawing, to prevent spurious redraws.
        self.current_object_view = None
        
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
        

        # The model will currently have 'ownership' of prior items,
        # and will delete them when resized or new items attached.
        # To prevent deletion, so that the Q_Item_Group isn't left
        # throwing "underlying C/C++ object has been deleted" errors,
        # use the 'take' methods to remove items from this model
        # without deleting them.
        self.Release_Items()

        # Resize to the right number of rows.
        # Could also clear(), but that would require regenerating rows
        # and also destroys the column headers.
        # TODO: delink existing q_items from edit_items as needed;
        #  this will probably be done during q_item setup.
        self.setRowCount(row_count)
        
        # Apply the labels.
        # TODO: maybe reuse existing items, but it probably isn't
        # worth it.
        for row in range(row_count):
            label_item = QStandardItem(labels[row])
            label_item.setToolTip(descriptions[row])
            self.setVerticalHeaderItem(row, label_item)
               

        # Can now fill in the display info.
        for row in range(row_count):
            for col, version in enumerate(self.column_keys):
              
                # Grab the right item for the column.
                # Top level object items will always match across versions,
                # but references can mismatch.
                item = version_items_list_dict[version][row]

                # If there is no underlying item, such as when a reference
                # is missing, can leave the spot blank.
                if item == None:
                    continue

                # If the item has no q_item_group, make one.
                if not item.q_item_group:
                    item.q_item_group = Q_Item_Group(item)

                # Get a new QStandardItem from the group.
                q_item = item.q_item_group.New_Q_Item(version)
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
        # object is changed. Completely unclear why, except maybe
        # qt bugginess.
        self.Resize_Rows()

        return

    
    def Redraw(self):
        '''
        Redraw this model from the current_object_view.  To be used
        when object references are changed, so that cells can be
        swapped to their new items.
        Skips if called on a window that hasn't drawn anything yet.
        '''
        if self.current_object_view != None:
            self.Update(self.current_object_view)
        return


    def Resize_Rows(self):
        '''
        Resizes the table rows to their contents.
        For use when descriptions or other large text blocks are changed,
        but can be called somewhat blindly on changes.
        '''
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
            for col in range(len(self.column_keys)):
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

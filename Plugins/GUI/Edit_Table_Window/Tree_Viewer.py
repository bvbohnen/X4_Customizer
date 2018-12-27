
from PyQt5 import QtWidgets

from ...Transforms.Live_Editor import Live_Editor
from Framework import Settings
from Framework import File_System


class Widget_X4_Table_Tree(QtWidgets.QTreeWidget):
    '''
    Tree view of the table entries, by name and possibly categorized.
    Clicking a plugin will signal a separate documentation
    window to display info (field names and data values).
    TODO: move some of this logic up to the tab page widget.

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
        self.widget_item_info = None
        return


    def Set_Table_Group(self, table_group):
        '''
        Updates the display of the tree to show the table_group
        contents.
        '''
        # Load in the table group from the thread results.
        self.table_group = table_group

        # If something went wrong, None was returned; just stop here
        # and let whatever exception message get printed.
        if self.table_group == None:
            self.window.Print('Get_Table_Group failed.')
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
        # -Removed; this is handled by whoever calls for the refresh.
        #Live_Editor.Reset_Current_Item_Values()

        # Send the selected item off for re-display, if there is
        # a selection.
        if self.last_selected_item != None:
            self.Handle_currentItemChanged(self.last_selected_item)
        return


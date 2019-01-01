
from collections import OrderedDict
from PyQt5 import QtWidgets


class Widget_X4_Table_Tree(QtWidgets.QTreeWidget):
    '''
    Tree view of the table entries, by name and possibly categorized.
    Clicking a plugin will signal a separate documentation
    window to display info (field names and data values).
    TODO: move some of this logic up to the tab page widget.

    Attributes:
    * widget_item_info
      - QGroupBox widget that will display the item info.
      - Should be set up by the parent after initial init.
    * last_selected_item_label
      - Text name of the last selected item.
      - Unlike the built-in QTreeWidget version, this will only hold
        active items, not table headers.
    * last_selected_item
      - The last selected item itself, associated with last_selected_item_label.
    * item_dict
      - Dict, keyed by label, of QTreeWidgetItem leaf nodes.
      - Used to get an item from last_selected_item_label.
      - Note: this could be unsafe if a label is used more than once,
        so avoid using it for anything critical; currently it is just
        used to restore item selection after a tree rebuild.
      - TODO: maybe set this to track through nested nodes, by joining
        labels together.
    * branch_dict
      - Dict, keyed by label, holding QTreeWidgetItem branch nodes.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.currentItemChanged.connect(self.Handle_currentItemChanged)
        self.last_selected_item_label = None
        self.last_selected_item = None
        self.widget_item_info = None
        self.item_dict = {}
        self.branch_dict = {}
        return


    def Set_Tree_View(self, edit_tree_view):
        '''
        Updates the display of the tree to show the edit_tree_view
        contents.
        '''
        # If something went wrong, None was returned; just stop here
        # and let whatever exception message get printed.
        if edit_tree_view == None:
            self.window.Print('Get_Table_Group failed.')
            return

        # Record the expansion state of items.
        # The goal is that all labels currently expanded will get
        # automatically reexpanded after a refresh.
        expanded_labels = [label for label, item in self.branch_dict.items() 
                           if item.isExpanded()]


        # Clear out old table items.
        # Note: existing items cannot easily be reused, since their
        # tree structure might change (eg. it's not always a flat list).
        # Tree widgets make this easy.
        self.clear()

        # Set up the tree view.
        self.item_dict.clear()
        self.branch_dict.clear()
        # Call the recursive tree builder, starting with self as
        # the root tree node.
        self._Fill_Tree_Node(self, edit_tree_view.Get_Tree())        

        # Try to find the item matching the last selected item's text,
        # and restore its selection.
        if self.last_selected_item_label in self.item_dict:
            # Look up the item.
            item = self.item_dict[self.last_selected_item_label]
            # Select it (highlights the line).
            self.setCurrentItem(item, True)
            # Set it for display.
            self.Handle_currentItemChanged(item)

        # Do a soft refresh, so that the current values of items
        # will update, and redraws the table.
        # TODO: may only be needed for reselecting an item (eg. nest
        # in the above 'if' statement) if script runs already call
        # the soft refresh reliably to handle current value changes.
        self.Soft_Refresh()
        
        # Reexpand nodes based on label matching.
        for label, item in self.branch_dict.items():
            if label in expanded_labels:
                item.setExpanded(True)
                
        # TODO: save expansion state across sessions.

        return


    def _Fill_Tree_Node(self, parent_widget, edit_tree_node):
        '''
        Recursive function to fill in the gui item children for the given
        tree view node (an OrderedDict).
        '''
        # Loop over the edit_tree_node children.
        for label, next_edit_node in edit_tree_node.items():
            
            # Make a new gui item.
            widget = QtWidgets.QTreeWidgetItem()

            # Set the label in column 0.
            widget.setText(0, label)

            # Attach the widget item to the parent tree.
            # If the parent is the top level tree, it uses a different
            # method for hookup.
            if isinstance(parent_widget, QtWidgets.QTreeWidget):
                parent_widget.addTopLevelItem(widget)
            else:
                parent_widget.addChild(widget)


            # If this is a category (a dict), recursively fill in its children.
            if isinstance(next_edit_node, OrderedDict):
                # Note that it is a label, for easy skipping when clicked.
                widget.is_label = True
                
                # Record the item by name for later lookup.
                self.branch_dict[label] = widget

                # Note: if the label is clicked, it should get ignored
                #  elsewhere due to not having extra annotations.
                # Recursive call to fill in its children.
                self._Fill_Tree_Node(widget, next_edit_node)

            # Otherwise, treat as a leaf item holding an Object_View.
            else:
                widget.is_label = False

                # Record the item by name for later lookup.
                self.item_dict[label] = widget

                # Apply annotations for convenience.
                widget.object_view = next_edit_node
        return


    def Handle_currentItemChanged(self, new_item = None):
        '''
        A different item was clicked on.
        '''
        # Note: it appears when the tree refreshes this event
        # triggers with None as the selection, so catch that case.
        if new_item == None:
            return
        # Ignore clicks on labels.
        if new_item.is_label:
            return

        # Record it for refresh restoration.
        self.last_selected_item = new_item
        # Pass the object_view to the display widget.
        self.widget_item_info.Update(new_item.object_view)
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


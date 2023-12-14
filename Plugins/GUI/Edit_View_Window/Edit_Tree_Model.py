
from Framework.Documentation import Doc_Category_Default
_doc_category = Doc_Category_Default('GUI')

from collections import OrderedDict
from PyQt5 import QtWidgets
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QItemSelectionModel


class Edit_Tree_Model(QStandardItemModel):
    '''
    Model container for an Edit_Tree_View, to interract with
    a tree view widget.

    Attributes:
    * edit_tree
      - Edit_Tree_View object being wrapped.
    * qt_view
      - Tree view in qt showing this model.

    TODO: remove/update as needed.
    * last_selected_item_label
      - Text name of the last selected item.
      - Unlike the built-in QTreeWidget version, this will only hold
        active items, not table headers.
    * item_dict
      - Dict, keyed by label, of QTreeWidgetItem leaf nodes.
      - Note: this could be unsafe if a label is used more than once.
      - TODO: label reuse was encountered with mines; need to
        change out to an item list or similar, or use more unique names.
    * branch_dict
      - Dict, keyed by label, holding QTreeWidgetItem branch nodes.
    '''
    def __init__(self, window, qt_view):
        super().__init__(window)
        self.last_selected_item_label = None
        self.edit_tree = None
        self.qt_view = qt_view
        self.window = window
        self.item_dict   = {}
        self.branch_dict = {}
        return
    

    def Set_Edit_Tree_View(self, edit_tree):
        '''
        Updates the display of the tree to show the edit_tree_view
        contents.
        '''
        # If something went wrong, None was returned; just stop here
        # and let whatever exception message get printed.
        if edit_tree == None:
            self.window.Print('Get_Table_Group failed.')
            return
        self.edit_tree = edit_tree
        
        # Record the expansion state of items.
        # The goal is that all labels currently expanded will get
        # automatically reexpanded after a refresh.
        # This is somewhat annoying since it has to go through the
        #  qt_view with index translation.
        expanded_labels = [label for label, item in self.branch_dict.items() 
                           if self.qt_view.isExpanded(self.indexFromItem(item))]


        # Clear out old table items.
        self.clear()
        self.item_dict  .clear()
        self.branch_dict.clear()
        

        # Call the recursive tree builder, starting with self as
        # the root tree node.
        self._Fill_Tree_Node(self, edit_tree.Get_Tree())        

        # Try to find the item matching the last selected non-branch item's
        #  text, and restore its selection.
        if self.last_selected_item_label in self.item_dict:
            # Look up the item.
            item = self.item_dict[self.last_selected_item_label]
            # Select it (highlights the line).
            self.qt_view.selectionModel().setCurrentIndex(
                self.indexFromItem(item), QItemSelectionModel.SelectCurrent)
            #self.setCurrentItem(item, True)
            # Set it for display.
            self.Change_Item(item)

        else:
            # TODO: clear the display.
            pass

        # Reexpand nodes based on label matching.
        for label, item in self.branch_dict.items():
            if label in expanded_labels:
                self.qt_view.setExpanded(self.indexFromItem(item), True)
                
        # TODO: save expansion state across sessions.

        return


    def _Fill_Tree_Node(self, parent_item, edit_tree_node):
        '''
        Recursive function to fill in the model item children for the given
        tree view node (a list of tuples of (label, sublist or object)).
        '''
        
        #self.appendRow(QStandardItem(edit_tree.name))

        # Loop over the edit_tree_node children.
        for label, next_edit_node in edit_tree_node:
            
            # Make a new gui item.
            item = QStandardItem(label)
            item.setEditable(False)
            item.label = label

            # Attach the item to the parent.
            parent_item.appendRow(item)

            # If this is a category (a dict), recursively fill in its children.
            if isinstance(next_edit_node, list):
                # Note that it is a label, for easy skipping when clicked.
                #item.is_label = True
                
                # Record the item by name for later lookup.
                self.branch_dict[label] = item

                # Note: if the label is clicked, it should get ignored
                #  elsewhere due to not having extra annotations.
                # Recursive call to fill in its children.
                self._Fill_Tree_Node(item, next_edit_node)

            # Otherwise, treat as a leaf item holding an Object_View.
            else:
                #item.is_label = False

                # Record the item by name for later lookup.
                self.item_dict[label] = item

                # Apply annotations for convenience.
                item.object_view = next_edit_node
                pass
        return


    def Handle_selectionChanged(self, qitemselection = None):
        '''
        A different item was clicked on.
        '''
        # This takes a bothersome object that needs indexes
        # extracted, that then need to be converted to items,
        # instead of just giving the item like qtreewidget.
        new_item = self.itemFromIndex(qitemselection.indexes()[0])
        self.Change_Item(new_item)


    def Change_Item(self, new_item):
        '''
        Change the selected item.
        '''
        # Note: it appears when the tree refreshes this event
        # triggers with None as the selection, so catch that case.
        if new_item == None:
            return
        # Ignore clicks on labels.
        if not hasattr(new_item, 'object_view'):
            return

        # Record it for refresh restoration.
        self.last_selected_item_label = new_item.label
        # Pass the object_view to the display widget.
        self.window.table_model.Update(new_item.object_view)
        return


    def Soft_Refresh(self):
        '''
        Does a partial refresh of the table, resetting the 'current'
        values of items and redrawing the table.
        '''
        # Send the selected item off for re-display, if there is
        # a selection.
        if self.last_selected_item != None:
            self.Handle_itemChanged(self.last_selected_item)
        return


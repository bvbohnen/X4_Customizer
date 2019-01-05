
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush
from .VFS_Item import VFS_Item
from ..Shared.Misc import Set_Icon

class VFS_List_Model(QStandardItemModel):
    '''
    Model to represent a list layout of a folder in the VFS.

    Attributes:
    * qt_view
      - Table view in qt showing this model.
    * vfs_item
      - The VFS_Item currently displayed.
    * menu
      - QMenu that will pop up on context menu requests.
    * selected_item
      - The currently selected item for a context menu.
    '''
    def __init__(self, window, qt_view):
        super().__init__(window)
        self.window = window
        self.vfs_item = None
        self.qt_view = qt_view
        self.selected_item = None
        
        self.qt_view .setModel(self)
        
        self.menu = QtWidgets.QMenu(self.qt_view)
        open_action = self.menu.addAction('Open in viewer')
        # TODO: pass the name of the event, once there are multiple.
        open_action.triggered.connect(self.Handle_contextMenuEvent)

        # Items double clicked.
        self.qt_view.doubleClicked.connect(self.Handle_doubleClicked)
        
        # Catch some viewer signals.
        self.qt_view.customContextMenuRequested.connect(
            self.Handle_contextMenuRequested)
        self.qt_view.selectionModel().selectionChanged.connect(
            self.Handle_selectionChanged)
        
        # TODO: allow folders to be double clicked to go down a level.
        return
    

    def Update(self, vfs_item):
        '''
        Update the display to a new vfs folder item.

        * vfs_item
          - The VFS_Item holding child folders and file names.
        '''
        # Set this to None while drawing, to prevent spurious redraws.
        self.vfs_item = None

        # Clear out old stuff.
        self.clear()
        
        # Get the parent item, to enable going back up.
        parent_q_item = vfs_item.Get_Parent_Q_Item()
        if parent_q_item != None:
            Set_Icon(parent_q_item, 'SP_FileDialogToParent')
            self.appendRow(parent_q_item)
            # Annotate it.
            parent_q_item.is_parent = True

        # Add all children items, building them uniquely.
        for q_item in vfs_item.Get_Child_Q_Items(
            include_folders = True, include_files = True):
            self.appendRow(q_item)
            # Annotate it.
            q_item.is_parent = False

        # Record the vfs_item, which also turns on change detection.
        self.current_vfs_item = vfs_item
        # Update the path label in the window.
        self.window.widget_label_path.setText(vfs_item.virtual_path)
        return

    
    def Handle_contextMenuRequested(self, qpoint):
        '''
        Handle table context menu requests.
        '''
        # Convert to an index in the view; this index is for the model.
        # Note: this may not be needed if it can be gathered from
        # whatever is passed by the action event trigger.
        index = self.qt_view.indexAt(qpoint)
        item = self.itemFromIndex(index)

        # If no item was clicked on, ignore.
        if item == None:
            return

        # If the item is a folder, don't open the menu (for now).
        if item.vfs_item.is_folder:
            return
        
        # Feed this the mouse position to place the menu.
        # Record the item to carry it to the next event.
        self.selected_item = item
        self.menu.popup(QtGui.QCursor.pos())
        return

    
    def Handle_selectionChanged(self, qitemselection = None):
        '''
        A different item was clicked on.
        '''
        # Look up the actual item selected.
        new_item = self.itemFromIndex(qitemselection.indexes()[0])
        self.Change_Item(new_item)
        return
    

    def Change_Item(self, new_item):
        '''
        Change the selected item.
        '''
        # Note: it appears when the tree refreshes this event
        # triggers with None as the selection, so catch that case.
        if new_item == None:
            return

        # Record it for refresh restoration. TODO
        #self.last_selected_item_label = new_item.text()

        # Update the detail widgets.
        # -Removed, leave this as 'Details', its info is elsewhere and
        #  the virtual_path doesn't fit anyway.
        #self.window.widget_label_details.setText(new_item.vfs_item.virtual_path)
        self.window.widget_text_details.setPlainText(new_item.vfs_item.Get_Summary())
        return


    def Handle_contextMenuEvent(self, event):
        '''
        Handle the file view context menu action.
        '''
        item = self.selected_item
        # Create a new tab for the viewer.
        # TODO: clean up this window.window thing.
        self.window.window.Create_Tab(
            class_name = 'File_Viewer_Window', 
            label = item.vfs_item.name,
            virtual_path = item.vfs_item.virtual_path)
        return
        

    def Handle_doubleClicked(self, index):
        '''
        Handle double click on an item.
        This should always have a valid item index.
        '''
        item = self.itemFromIndex(index)

        # Open folders.
        if item.vfs_item.is_folder:

            # This could have gone down a level or up a level.
            if item.is_parent:
                # For going up, just in case the parent folder is collapsed,
                # expand the new vfs_item.
                # -Removed; need to think about this more, since it
                # should only happen if the user collapsed the parent
                # folder manually, which perhaps should be left unchanged.
                pass
            else:
                # Make sure the current node is expanded.
                # Eg. if current showing folder 'a', and child folder
                # 'b' was selected, want 'a' to be expanded in the tree
                # so that 'b' is visible.
                self.window.tree_model.Open_Folder(self.current_vfs_item)
                                
            # Open it locally; do this last, since it
            # overwrites current_vfs_item.
            self.Update(item.vfs_item)

        return
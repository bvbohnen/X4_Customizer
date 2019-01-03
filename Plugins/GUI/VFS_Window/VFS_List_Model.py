
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush
from .VFS_Item import VFS_Item

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
        
        self.menu = QtWidgets.QMenu(self.qt_view)
        open_action = self.menu.addAction('Open in viewer')
        # TODO: pass the name of the event, once there are multiple.
        open_action.triggered.connect(self.Handle_contextMenuEvent)
        
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

        # TODO: option to go up one level.

        # Add all children items, building them uniquely.
        for q_item in vfs_item.Get_Child_Q_Items(
            include_folders = True, include_files = True):
            self.appendRow(q_item)                   

        # Record the vfs_item, which also turns on change detection.
        self.current_vfs_item = vfs_item

        return

    
    def Handle_contextMenuRequested(self, qpoint):
        '''
        Handle table context menu requests.
        '''
        # Convert to an index in the view; this index is for the model.
        # Note: this may not be needed if it can be gathered from
        # whatever is passed by the action event trigger.
        index = self.qt_view.indexAt(qpoint)
        self.selected_item = self.itemFromIndex(index)

        # If the item is a folder, don't open the menu (for now).
        if self.selected_item.vfs_item.is_folder:
            return
        
        # Feed this the mouse position to place the menu.
        self.menu.popup(QtGui.QCursor.pos())
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
        

from pathlib import Path
from collections import defaultdict

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush

from .VFS_Item import VFS_Item
from ..Shared.Misc import Set_Icon
from Framework import File_System, XML_Diff, Print, Settings

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
    * action_extensions
      - Dict, keyed by QAction object, with a tuple of lists of associated
        file type extensions the action applies to ([0]) or blacklists ([1]).
      - Extensions are given with preceeding '.', and '.*' applies to all.
    '''
    def __init__(self, window, qt_view):
        super().__init__(window)
        self.window = window
        self.vfs_item = None
        self.qt_view = qt_view
        self.selected_item = None
        
        self.qt_view .setModel(self)
        
        # Set up the context menu.
        self.menu = QtWidgets.QMenu(self.qt_view)
        self.action_extensions = {}
        # TODO: how to filter events based on object selected?
        context_events = {
            'view'        : ('Open in viewer'        , ['.xml'], []),
            'save_current': ('Save to file'          , ['.*']  , ['.xml']),
            'save_vanilla': ('Save to file (vanilla)', ['.xml'], []),
            'save_patched': ('Save to file (patched)', ['.xml'], []),
            }
        for event_name, (text, extensions, blacklist) in context_events.items():

            action = self.menu.addAction(text)
            # Pass the name of the event to the handler.
            action.triggered.connect(
                lambda x, y = event_name: self.Handle_contextMenuEvent(x, y))

            # Record this action to be active for associated file types.
            self.action_extensions[action] = (extensions, blacklist)

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

        # Get the file type of the item.
        ext = Path(item.vfs_item.name).suffix

        # Set only associated actions as visible.
        for action, (extensions, blacklist) in self.action_extensions.items():
            if (ext not in blacklist) and ('.*' in extensions or ext in extensions):
                action.setVisible(True)
            else:
                action.setVisible(False)
        
        # Feed this the mouse position to place the menu.
        # Record the item to carry it to the next event.
        self.selected_item = item
        self.menu.popup(QtGui.QCursor.pos())
        return

    # TODO: maybe support multi-select
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


    def Handle_contextMenuEvent(self, event, event_name):
        '''
        Handle the file view context menu action.
        '''
        # Note: "event" input is "False" in a quick check.
        item = self.selected_item

        if event_name == 'view':
            # Create a new tab for the viewer.
            # TODO: clean up this window.window thing.
            self.window.window.Create_Tab(
                class_name = 'File_Viewer_Window', 
                label = item.vfs_item.name,
                virtual_path = item.vfs_item.virtual_path)

        elif event_name in ['save_current', 'save_vanilla', 'save_patched']:

            # Load the file.
            # TODO: wait on this until after save prompt.
            game_file = File_System.Load_File(
                          item.vfs_item.virtual_path,
                          error_if_not_found = False)

            # Error check.
            if game_file == None:
                self.window.Print(('Error loading file for path "{}"'
                                  ).format(self.virtual_path))
                return

            # Grab the binary.
            version = event_name.replace('save_','')    
            binary = game_file.Get_Binary(version = version, no_diff = True)
            
            # Pick the output directory default.
            if not self.window.last_dialog_path:
                directory = Settings.path_to_x4_folder
            else:
                directory = self.window.last_dialog_path

            # Create a file selection dialogue, using a QFileDialog object.
            file_dialogue = QtWidgets.QFileDialog(self.window)

            # Allow selection of any file (as oppposed to existing file).
            file_dialogue.setFileMode(QtWidgets.QFileDialog.AnyFile)

            # Get the filename/path from the dialogue.
            #  Note: in qt5 this now returns a tuple of
            #   (path string, type name with extension as a string).
            #  Only keep the full path here.
            virtual_path = Path(item.vfs_item.virtual_path)
            extension = virtual_path.suffix
            file_name = virtual_path.name
            file_selected, _ = file_dialogue.getSaveFileName(
                # TODO: maybe extact with full path as an option.
                directory = str(directory / file_name) )

            # If the file path is empty, the user cancelled the dialog.
            if not file_selected:
                return False
        
            # Convert to a Path.
            file_selected = Path(file_selected)
            # Update the last_dialog_path.
            self.window.last_dialog_path = file_selected.parent

            # Make the directory if needed.
            file_selected.parent.mkdir(parents = True, exist_ok = True)

            # Write out the file.
            file_selected.write_bytes(binary)

            # Nice success message.
            self.window.Print('Saved {} ({}) to {})'.format(
                item.vfs_item.virtual_path,
                version,
                file_selected.as_posix(),
                ))
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
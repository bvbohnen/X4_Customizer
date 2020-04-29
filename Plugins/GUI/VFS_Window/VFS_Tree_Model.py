
from collections import OrderedDict
from time import time
from Framework import Settings
from PyQt5 import QtWidgets
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QItemSelectionModel

from .VFS_Item import VFS_Item

class VFS_Tree_Model(QStandardItemModel):
    '''
    Model to represent a tree layout of the VFS.

    Attributes:
    * path_item_dict
      - Dict, keyed by virtual_path, holding all VFS_Items, including
        directories, with a top node at ''.
    * path_q_item_dict
      - As above, but holding the generated QTreeWidgetItems.
    * q_expanded_vfs_items
      - List of VFS_Items which have had their q_item children expanded.
    * qt_view
      - Tree view in qt showing this model.
    * last_selected_virtual_path
      - The virtual_path of the last selected item.

    TODO: remove/update as needed.
    * item_dict
      - Dict, keyed by label, of QTreeWidgetItem leaf nodes.
      - Note: this could be unsafe if a label is used more than once.
    * branch_dict
      - Dict, keyed by label, holding QTreeWidgetItem branch nodes.
    '''
    def __init__(self, window, qt_view):
        super().__init__(window)
        self.path_item_dict = None
        self.path_q_item_dict = {}
        self.q_expanded_vfs_items = []
        self.last_selected_virtual_path = None
        self.qt_view = qt_view
        self.window = window
        #self.item_dict   = {}
        #self.branch_dict = {}
        
        self.qt_view .setModel(self)
        
        # Catch some viewer signals.
        self.qt_view.selectionModel().selectionChanged.connect(
            self.Handle_selectionChanged)
        self.qt_view.expanded.connect(
            self.Handle_expanded)

        return
        

    def Gen_Child_Q_Items(self, vfs_or_q_item):
        '''
        For a given vfs_item or q_item, tell it to generated its q_item
        children, and record the generated nodes.  Does nothing if the
        vfs_item has already been expanded.  (Used to delay child q item
        generation, to avoid startup slowdown.)

        Returns any new child q_items.
        '''
        # Check if given a q or vfs item.
        if isinstance(vfs_or_q_item, VFS_Item):
            vfs_item = vfs_or_q_item
            q_item = None
        else:
            vfs_item = vfs_or_q_item.vfs_item
            q_item = vfs_or_q_item

        # Skip if already expanded.
        if vfs_item in self.q_expanded_vfs_items:
            return []
        self.q_expanded_vfs_items.append(vfs_item)

        # Expand one level. This will automatically add the children
        # to the given q_item as a subrow. Folders only.
        # This will hand down the q_item for children to attach to, if any.
        child_q_items = vfs_item.Get_Child_Q_Items(
            include_folders = True,
            base_q_item = q_item
            )

        # Record the children.
        for child in child_q_items:
            self.path_q_item_dict[child.vfs_item.virtual_path] = child
        return child_q_items
    

    def Set_File_Listing(self, virtual_paths, file_info_dict):
        '''
        Fill in the tree with the given file system contents.

        * virtual_paths
          - List of strings, virtual paths to be included.
        * file_info_dict
          - Dict of dicts, info on loaded files.
        '''        
        # TODO: time this and improve if a problem; this has some
        # issue locking up the gui for a few seconds.

        ## Record the expansion state of items.
        ## The goal is that all labels currently expanded will get
        ## automatically reexpanded after a refresh.
        ## This is somewhat annoying since it has to go through the
        ##  qt_view with index translation.
        #expanded_labels = [label for label, item in self.branch_dict.items() 
        #                   if self.qt_view.isExpanded(self.indexFromItem(item))]


        # Clear out old table items.
        self.clear()
        #self.item_dict  .clear()
        #self.branch_dict.clear()        

        # Convert to vfs items.
        self.Convert_Paths_To_VFS_Items(virtual_paths, file_info_dict)
        
        # Clear old q_item tracking stuff.
        self.path_q_item_dict.clear()
        self.q_expanded_vfs_items.clear()

        # Grab the top node.
        top_vfs_item = self.path_item_dict['']

        # Note: the top node is root.  It could either be set to have
        # a q_item, the top level for the menu which needs to be expanded
        # to see anything interesting, or it could be skipped entirely
        # and just its children placed in the menu directly.
        # The latter looks nicer most of the time, but have one major
        # drawback: files in the top folder (eg. html) cannot be viewed
        # since root cannot be selected.

        # Since the vfs should prioritize showing all files, the root will
        # be included and auto expanded.
        top_q_item = top_vfs_item.Get_Q_Item()
        self.path_q_item_dict[top_vfs_item.virtual_path] = top_q_item
        self.appendRow(top_q_item)

        # Ensure its children are generated, so it's expandable.
        self.Gen_Child_Q_Items(top_q_item)

        # Force it to be expanded.
        # TODO: there was one instance of opening the vfs tab and
        # root not being expanded after a script run and some other
        # tabs being opened. Maybe try to reproduce and fix.
        self.qt_view.setExpanded(self.indexFromItem(top_q_item), True)


        # -Removed in favor of having a root q_item.
        ## Convert its children to Q items and add them.
        #q_items = self.Gen_Child_Q_Items(top_vfs_item)
        ##q_items = top_item.Get_Child_Q_Items(
        ##        include_folders = True, 
        ##        recursive = True
        ##    )
        #for q_item in q_items:
        #    self.appendRow(q_item)
        #
        ## The above is sufficient for top level folders, but doesn't
        ## fill in subchild q_items, so no folder will be expandable.
        ## Fix that by also generating the first level children for
        ## all of the q_items.
        #for q_item in q_items:
        #    # Don't do anything with their nested children; they will
        #    # be looked up in path_q_item_dict and processed when 
        #    # expanded in the gui.
        #    self.Gen_Child_Q_Items(q_item)
            

        # -Removed in favor of more selective approach.
        ## Record all q_items present, at any level.
        ## This is kinda messy, since apparently qt doesn't have any
        ## function for iterating over children.
        #search_items = q_items
        #while search_items:
        #    q_item = search_items.pop()
        #    # Record this item.
        #    self.path_q_item_dict[q_item.vfs_item.virtual_path] = q_item
        #    # Queue all children; in column 0.
        #    for row in range(q_item.rowCount()):
        #        child = q_item.child(row,0)
        #        search_items.append(child)


        ## Try to find the item matching the last selected non-branch item's
        ##  text, and restore its selection.
        #if self.last_selected_item_label in self.item_dict:
        #    # Look up the item.
        #    item = self.item_dict[self.last_selected_item_label]
        #    # Select it (highlights the line).
        #    self.qt_view.selectionModel().setCurrentIndex(
        #        self.indexFromItem(item), QItemSelectionModel.SelectCurrent)
        #    #self.setCurrentItem(item, True)
        #    # Set it for display.
        #    self.Change_Item(item)
        #
        #else:
        #    # TODO: clear the display.
        #    pass
        #
        ## Reexpand nodes based on label matching.
        #for label, item in self.branch_dict.items():
        #    if label in expanded_labels:
        #        self.qt_view.setExpanded(self.indexFromItem(item), True)
        #        
        ## TODO: save expansion state across sessions.

        # TODO: tell the list view to open the top level, maybe.
        return

    # TODO: speed this up somehow; kinda slow.
    def Convert_Paths_To_VFS_Items(self, virtual_paths, file_info_dict):
        '''
        Generate VFS_Items for the given virtual_paths.
        Returns a dict, keyed by virtual_path (partials for folders),
        holding the items. There will be more entries in this dict
        than there are original file virtual_paths due to the extra
        for directories.
        The top level node will have an empty path string.
        '''
        if Settings.profile:
            start = time()

        path_item_dict = {}
        def Record_Parents(vfs_item):
            '''
            Recursive function to record parent folders for a given
            item, adding this item to its parent.
            '''
            # If this vfs_item is root, return early.
            if vfs_item.virtual_path == '':
                return
            # Look up the parent folders to reach this file.
            parent_path = vfs_item.parent_path

            # If it is not yet seen, record it as a folder.
            if parent_path not in path_item_dict:

                # Create the item.
                parent = VFS_Item(
                    virtual_path = parent_path,
                    is_folder = True,
                    shared_file_info_dict = file_info_dict,
                    window = self.window,
                    )

                # Record it, and its parents recursively.
                path_item_dict[parent_path] = parent
                Record_Parents(parent)

            # Add this item to its parent.
            path_item_dict[parent_path].Add_Item(vfs_item)
            return


        # Note: this can take excessive time if the full file
        #  system contents are given; maybe look into it again
        #  if that is ever wanted, but for now rely on the input
        #  paths having been filtered down to text items or maybe some
        #  select binary.
        # Update: removing the VFS_Item creation for files sped this
        #  up a lot, and the file type filter even more so.

        for virtual_path in virtual_paths:

            *parent, name = virtual_path.rsplit('/',1)
            if parent:
                parent_path = parent[0]
            else:
                parent_path = ''

            # Set up the first parent.
            # TODO: this has some code repetition with the Record_Parents
            # function; a rewrite can clean it up a bit.
            if parent_path not in path_item_dict:

                # Create the item.
                parent = VFS_Item(
                    virtual_path = parent_path,
                    is_folder = True,
                    shared_file_info_dict = file_info_dict,
                    window = self.window,
                    )
                
                # Record it, and its parents recursively.
                path_item_dict[parent_path] = parent
                Record_Parents(parent)
                
            # Add this virtual_path to its parent.
            path_item_dict[parent_path].file_paths.append(virtual_path)

            ## Create its item.
            ## TODO: skip file item creation, and just record them
            ## as lists of names, to save tree building time (these
            ## won't display anyway, if placed in the list view instead).
            #vfs_item = VFS_Item(
            #    virtual_path = virtual_path,
            #    is_folder = False )
            #path_item_dict[virtual_path] = vfs_item

            # Fill in its parents.
            #Record_Parents(vfs_item)

        self.path_item_dict = path_item_dict

        if Settings.profile:
            self.window.Print('VFS Tree build time: {:.3f} s'.format(
                time() - start
                ))
        return


    #def _Categorize_Virtual_Paths(self, virtual_paths):
    #    '''
    #    Transform a list of virtual paths into a dict of dicts of ...
    #    of dicts or virtual_paths. Each key is a folder name. Files at
    #    a level are collected into the '@files' key, using their
    #    full virtual_path.
    #    '''
    #    top_dict = OrderedDict()
    #    top_dict['@files'] = []
    #
    #    for path in sorted(virtual_paths):
    #
    #        # Break up the pieces; this is safe even if there is
    #        # no '/' present.
    #        *folders, file_name = path.split('/')
    #
    #        # Step through the folders, filling out the dict structure
    #        # and getting the final dict.
    #        this_dict = top_dict
    #        for folder in sorted(folders):
    #
    #            # Build another level if needed.
    #            if folder not in this_dict:
    #                # Give all levels an empty list of files initially.
    #                this_dict[folder] = OrderedDict()
    #                this_dict[folder]['@files'] = []
    #
    #            # Move one level deeper for the next loop iteration.
    #            this_dict = this_dict[folder]
    #
    #        # With no folders present, put the file here.
    #        if not folders:
    #            # Add the file.
    #            this_dict['@files'].append(path)
    #
    #    # Everything should be organized now.
    #    return top_dict
    #


    def Handle_selectionChanged(self, qitemselection = None):
        '''
        A different item was clicked on. Change to it.
        '''
        # This takes a bothersome object that needs indexes
        # extracted, that then need to be converted to items,
        # instead of just giving the item like qtreewidget.
        new_item = self.itemFromIndex(qitemselection.indexes()[0])
        self.Change_Item(new_item)
        return
    

    def Handle_expanded(self, qmodelindex = None):
        '''
        An item was expanded. Generate grandchildren.
        '''
        q_item = self.itemFromIndex(qmodelindex)

        # TODO: clean up redundancy with Open_Folder.
        # This q_item should have had its children generated previously,
        # but make sure the children's children are generated.
        for row in range(q_item.rowCount()):
            self.Gen_Child_Q_Items(q_item.child(row,0))
        return


    def Change_Item(self, q_item):
        '''
        Change the selected item.
        '''
        # Note: it appears when the tree refreshes this event
        # triggers with None as the selection, so catch that case.
        if q_item == None:
            return

        # Record it for refresh restoration.
        self.last_selected_virtual_path = q_item.vfs_item.virtual_path
        # Pass the object_view to the display widget.
        self.window.list_model.Update(q_item.vfs_item)
        return


    def Soft_Refresh(self):
        '''
        Does a partial refresh of the table, resetting the 'current'
        values of items and redrawing the table.
        '''
        # Recolor all items.
        for item in self.path_q_item_dict.values():
            item.vfs_item.Color_Q_Item(item)

        # Send the selected item off for re-display, if there is
        # a selection, and it is still valid for the file suffix.
        if self.last_selected_virtual_path != None:
            # Item may or may not still exist.
            item = self.path_q_item_dict.get(self.last_selected_virtual_path)
            # If not, clear the path, else change item.
            if item == None:
                self.last_selected_virtual_path = None
            else:
                self.Change_Item(item)
                
        # TODO: refresh the list view on suffix change, or just in general.

        # TODO: recolor existing items, once coloring support
        # is added to them.
        return


    def Open_Folder(self, vfs_item):
        '''
        Expand down to the selected vfs_item matching q_item.
        Called from the list view when changing levels.
        If this requests opening root, it will be ignored.
        '''
        # Ignore root.
        if not vfs_item.virtual_path:
            return
        q_item = self.path_q_item_dict[vfs_item.virtual_path]

        # This q_item should have had its children generated previously,
        # but make sure the children's children are generated.
        for row in range(q_item.rowCount()):
            self.Gen_Child_Q_Items(q_item.child(row,0))

        self.qt_view.setExpanded(self.indexFromItem(q_item), True)

        # TODO: maybe select it too, though for now skip such
        # selection since the tree may be intentionally viewing something
        # other than what is in the list view.
        return

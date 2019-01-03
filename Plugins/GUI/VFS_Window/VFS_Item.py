
from itertools import chain
from collections import OrderedDict
from PyQt5 import QtWidgets
from PyQt5.QtGui import QStandardItemModel, QStandardItem

from ..Shared.Misc import Set_Icon
from Framework import File_System

class VFS_Item:
    '''
    Represents a VFS folder or file.
    To be a little lighter weight, nested files will sometimes be tracked
    by name, while only nested folders are consistently tracked as VFS_Items.

    Attributes:
    * virtual_path
      - String, path to this folder.
    * parent_path
      - String, virtual_path of the parent folder.
    * name
      - String, name of this folder or file.
    * folders
      - List of VFS_Item objects that are folders under this one.
      - Empty if this is a file.
    * files
      - List of VFS_Item objects that are files under this one.
      - Empty if this is a file.
    * file_paths
      - List of strings, virtual_paths of files that are at this folder level.
      - Empty if this is a file.
    * is_folder
      - Bool, True if this is a folder, else it is a file.
    '''
    def __init__(
            self,
            virtual_path,
            is_folder
        ):
        self.virtual_path = virtual_path
        self.is_folder = is_folder

        # Split on the last '/', though it may not be present.
        *parent, self.name = virtual_path.rsplit('/',1)
        if parent:
            self.parent_path = parent[0]
        else:
            self.parent_path = ''

        # To reduce weight, only make these lists for folders.
        if is_folder:
            self.folders = []
            self.files = []
            self.file_paths = []
        return
    
    def Add_Item(self, vfs_item):
        '''
        Record the child item under this folder.
        It will be added to folders or files based on its is_folder flag.
        '''
        if vfs_item.is_folder:
            self.folders.append(vfs_item)
        else:
            self.files.append(vfs_item)

    def Get_Folders(self):
        '''
        Returns all child folders.
        '''
        return self.folders
    
    def Get_Files(self):
        '''
        Returns all child files.
        '''
        return self.files

    def Build_Files(self):
        '''
        From file_paths, construct VFS_Items and fill in the files list.
        This should be called only when needed, since there is some
        delay on the creation that is significant if all folders do
        it at once.
        Does nothing if files are already present.
        '''
        if self.files:
            return
        for virtual_path in self.file_paths:
            self.files.append(VFS_Item(virtual_path, is_folder = False))
        return

    def Get_Game_File(self):
        '''
        If this is a file, returns the Game_File object for it,
        or None if there is a loading error.
        '''
        if self.is_folder:
            return
        return File_System.Load_File(self.virtual_path)

    def Get_Q_Item(
            self, 
            include_folders = False, 
            include_files = False,
            recursive = False
        ):
        '''
        Returns a QStandardItem representing this item, annotated with
        'vfs_item' to link back here.

        * include_folders
          - Bool, if True and this is a folder, all child folders
            will have items included as row children of this item,
            recursively, and passing the include_files flag along.
          - Folders will be sorted and placed before sorted files.
        * include_files
          - Bool, as above but for files.
          - If both include_folders and include_files are True, then
            the entire tree below this point will be included.
        * recursive
          - Bool, if True then recursively include child folder chidren.
        '''
        q_item = QStandardItem(self.name)
        q_item.vfs_item = self

        # Give it a nice icon.
        if self.is_folder:
            Set_Icon(q_item, 'SP_DirIcon')
        else:
            Set_Icon(q_item, 'SP_FileIcon')

        # Add any children q items.
        for child_q_item in self.Get_Child_Q_Items(
                    include_folders = include_folders,
                    include_files = include_files,
                    recursive = recursive):
            q_item.appendRow(child_q_item)

        return q_item


    def Get_Child_Q_Items(
            self, 
            include_folders = False, 
            include_files = False,
            recursive = False
            ):
        '''
        Returns a list of QStandardItems for each of its children.
        If neither flag is set, returns an emtpy list.

        * include_folders
          - Bool, include child folders.
        * include_files
          - Bool, include child files.
        * recursive
          - Bool, if True then recursively include child folder chidren.
        '''
        if not self.is_folder:
            return []

        ret_list = []
        if include_folders:
            for subitem in sorted(self.folders, key = lambda x : x.name):
                ret_list.append( subitem.Get_Q_Item(
                    # Don't have it include its children if this
                    # is not a recursive request.
                    include_folders = include_folders and recursive,
                    include_files = include_files and recursive,
                    recursive = recursive))

        if include_files:
            # Make sure files are built.
            self.Build_Files()
            for subitem in sorted(self.files, key = lambda x : x.name):
                ret_list.append( subitem.Get_Q_Item())

        return ret_list
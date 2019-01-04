
from itertools import chain
from collections import OrderedDict
from PyQt5 import QtWidgets
from PyQt5.QtGui import QStandardItemModel, QStandardItem

from ..Shared.Misc import Set_Icon, Set_Foreground_Color
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
    * parent
      - VFS_Item representing the parent folder.
      - None for the top level.
    * name
      - String, name of this folder or file.
      - At the top level, this is just 'root'.
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
        self.parent = None

        # Split on the last '/', though it may not be present.
        *parent, self.name = virtual_path.rsplit('/',1)
        if parent:
            self.parent_path = parent[0]
        else:
            self.parent_path = ''

        if not self.name:
            self.name = 'root'

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
        vfs_item.parent = self
        return


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
            self.Add_Item(VFS_Item(virtual_path, is_folder = False))
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

        # Color it based on file status.
        if not self.is_folder:
            # Special color if both patched and modified.
            if self.Is_Patched_Modified():
                color = 'darkviolet'
            elif self.Is_Modified():
                color = 'crimson'
            elif self.Is_Patched():
                color = 'blue'
            elif self.Is_Loaded():
                color = 'black'
            else:
                color = 'gray'
            Set_Foreground_Color(q_item, color)

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

            for subitem in sorted(
                self.files, 
                # Sort these such that modified/patched/etc. show up first.
                # Want it to be somewhat exclusively categorized, eg. all
                #  modified files are grouped together and sorted by name
                #  and not based on which are patched.
                # Flip the flags so that a 'True' sorts first.
                key = lambda x : (  not x.Is_Patched_Modified(),
                                    not x.Is_Modified(), 
                                    not x.Is_Patched(), 
                                    not x.Is_Loaded(), 
                                    x.name)
                ):
                ret_list.append( subitem.Get_Q_Item())

        return ret_list


    def Get_Parent_Q_Item(self):
        '''
        Returns a QStandardItem for this item's parent.
        It will have no file/folder children.
        If there is no parent, returns None.
        '''
        if self.parent == None:
            return
        return self.parent.Get_Q_Item()


    def Is_Loaded(self):
        '''
        For files, returns True if the File_System has a copy of
        the file loaded, else False.
        '''
        if self.is_folder:
            return False
        if File_System.File_Is_Loaded(self.virtual_path):
            return True
        return False


    def Is_Patched(self):
        '''
        For files, returns True if the file is partly or wholly
        by an extension. This ignores customizer modifications.
        '''
        if self.Is_Loaded():
            if self.Get_Game_File().Is_Patched():
                return True
        return False


    def Is_Modified(self):
        '''
        For files, returns True if the file has been modified by
        the customizer script.
        '''
        if self.Is_Loaded():
            if self.Get_Game_File().Is_Modified():
                return True
        return False
        

    def Is_Patched_Modified(self):
        '''
        For files, teturns True if the file has been modified
        by the customizer script and was original sourced from
        an extension.
        '''
        return self.Is_Modified() and self.Is_Patched()


    def Get_Summary(self):
        '''
        Returns a text block with a summary of this item's details.
        '''
        lines =['name      : {}'.format(self.name)]
        if self.is_folder:
            lines += [
                'dirs      : {}'.format(len(self.folders)),
                'files     : {}'.format(len(self.files)),
                ]
        else:
            lines += [
                'loaded    : {}'.format(self.Is_Loaded()),
                'patched   : {}'.format(self.Is_Patched()),
                'modified  : {}'.format(self.Is_Modified()),
                ]
            if self.Is_Patched():
                lines.append(
                'extensions:')
                game_file = self.Get_Game_File()
                for extension_name in game_file.Get_Source_Names():
                    lines.append('  '+extension_name)

        return '\n'.join(lines)
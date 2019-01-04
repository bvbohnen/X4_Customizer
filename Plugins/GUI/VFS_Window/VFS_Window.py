
from collections import defaultdict
from pathlib import Path
from PyQt5.uic import loadUiType

from PyQt5 import QtWidgets
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QItemSelectionModel

from ..Shared import Tab_Page_Widget
from Framework import File_System
from .VFS_Tree_Model import VFS_Tree_Model
from .VFS_List_Model import VFS_List_Model

gui_file = Path(__file__).parents[1] / 'x4c_gui_vfs_tab.ui'
generated_class, qt_base_class = loadUiType(str(gui_file))


class VFS_Window(Tab_Page_Widget, generated_class):
    '''
    Window used for displaying the virtual file system.

    Widget names:
    * widget_treeView
    * widget_listView
    * splitter
    * vsplitter
    * hsplitter
    * widget_refresh_button - TODO
    * widget_label_path
    * widget_label_details
    * widget_text_details

    Attributes:
    * window
      - The parent main window holding this tab.
    * tree_model
      - VFS_Tree_Model controlling the widget_treeView.
      - Will display directories.
    * list_model
      - QStandardItemModel controlling the widget_listView.
      - Will display files in a directory.
    '''
    def __init__(self, parent, window):
        super().__init__(parent, window)

        # Set up initial, blank models.
        self.tree_model = VFS_Tree_Model(self, self.widget_treeView)
        self.list_model = VFS_List_Model(self, self.widget_listView)
                       
        # Trigger button for loading the table.
        #self.widget_refresh_button.clicked.connect(self.Action_Make_Table_Group)
                
        # Force the initial splitter position.
        self.hsplitter.setSizes([1000,3000])
        self.vsplitter.setSizes([3000,1000])
        
        return
    
    
    def Action_Refresh(self):
        '''
        Load the virtual paths from the File_System.
        '''
        # Disable the button while working.
        #self.widget_Table_Update.setEnabled(False)

        ## Reset the live editor table group that is be re-requested.
        ## This will fill in new items that may get created by the
        ## user script.
        #self.Queue_Thread(
        #    Live_Editor.Get_Tree_View,
        #    self.table_name, 
        #    rebuild = True,
        #    )
        
        # This is pretty quick; maybe skip the threading entirely.
        # Pattern this for supported file types; don't want everything
        # because the vfs builder is kinda slow currently.
        # Only support xml for now, as that is what the file viewer
        # supports (others not having multiple version support).
        virtual_paths = [ x for pattern in ['*.xml']#,'*.lua']
              for x in File_System.Gen_All_Virtual_Paths(pattern = pattern) ]
        assert virtual_paths
        self.tree_model.Set_File_Listing(virtual_paths)
        return
    

    def Soft_Refresh(self):
        '''
        Does a partial refresh of the table, redrawing the current items.
        '''
        # The tree will update the list, so only refresh the tree.
        self.tree_model.Soft_Refresh()
        #self.list_model.Soft_Refresh()
        return
    
    def Reset_From_File_System(self):
        '''
        Trigger regather of the file system on reset.
        '''
        self.Action_Refresh()
        return

    #def Action_Make_Table_Group(self):
    #    '''
    #    Update button was presssed; clear loaded files and rerun
    #    the plugin to gather the table group and set up the tree.
    #    '''
    #    # Disable the button while working.
    #    self.widget_Table_Update.setEnabled(False)
    #
    #    # Reset the live editor table group that is be re-requested.
    #    # This will fill in new items that may get created by the
    #    # user script.
    #    self.Queue_Thread(
    #        Live_Editor.Get_Tree_View,
    #        self.table_name, 
    #        rebuild = True,
    #        )
    #    return


    # TODO: maybe use a thread to gather the file system info.
    #def Handle_Thread_Finished(self, return_value):
    #    '''
    #    Catch the returned table_group and updated the widgets.
    #    '''
    #    super().Handle_Thread_Finished()
    #    # Turn the button back on, before handling the response
    #    # (in case it gets an error, this lets it be rerun).
    #    self.widget_Table_Update.setEnabled(True)
    #
    #    # Pass the Edit_Tree_View down to the model.
    #    self.tree_model .Set_Edit_Tree_View(return_value)
    #    #self.table_model.Set_Edit_Tree_View(return_value)
    #    return


    def Close(self):
        '''
        Prepare this window for closing, either at shutdown or
        on tab closure.
        '''
        super().Close()
        return
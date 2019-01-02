

from pathlib import Path
from PyQt5.uic import loadUiType

from ..Shared import Tab_Page_Widget
from Framework import Live_Editor
from .Edit_Tree_Model import Edit_Tree_Model
from .Edit_Table_Model import Edit_Table_Model

gui_file = Path(__file__).parents[1] / 'x4c_gui_viewer_tab.ui'
generated_class, qt_base_class = loadUiType(str(gui_file))


class Edit_View_Window(Tab_Page_Widget, generated_class):
    '''
    Window used for editing table data, aiming to use the
    qt model/view objects to get better formatting than custom
    made widgets.
    Intended to be replicated across multiple tabs for different
    table groups.

    Widget names:
    * widget_treeView
    * widget_tableView
    * hsplitter
    * widget_Hideme
    * widget_Table_Update
    * widget_table_checkBox_0
    * widget_table_checkBox_1
    * widget_table_checkBox_2
    * widget_table_checkBox_3

    Attributes:
    * window
      - The parent main window holding this tab.
    * table_name
      - String, name of the table to display, as understood by the
        Live_Editor.
    * tree_model
      - Edit_Tree_Model controlling the widget_treeView.
    * table_model
      - Edit_Table_Model controlling the widget_tableView.
    '''
    def __init__(self, parent, window, table_name):
        super().__init__(parent, window)
        self.table_name = table_name

        # Set up initial, blank models.
        self.tree_model  = Edit_Tree_Model(self, self.widget_treeView)
        self.table_model = Edit_Table_Model(self, self.widget_tableView)
        
        # Hook them into the views.
        self.widget_treeView .setModel(self.tree_model)
        self.widget_tableView.setModel(self.table_model)

        # Hook up some signals.
        # Let the table know when the tree selection changes.
        #self.widget_treeView.selectionModel().selectionChanged.connect(
        #    self.table_model.Handle_selectionChanged)
        self.widget_treeView.selectionModel().selectionChanged.connect(
            self.tree_model.Handle_selectionChanged)


        # Want the placeholder along the top bar to be invisible
        #  but still take space.
        # It is a little tricky to hide the placeholder; it will
        #  normally stop taking space when invisible; use the sizePolicy
        #  to adjust it.
        self.widget_Hideme.setVisible(False)
        # Note: cannot edit the sizepolicy directly; need to pull it
        #  out, modify it, and set it back to update properly.
        sizepolicy = self.widget_Hideme.sizePolicy()
        sizepolicy.setRetainSizeWhenHidden(True)
        self.widget_Hideme.setSizePolicy(sizepolicy)
        

        # Trigger button for loading the table.
        self.widget_Table_Update.clicked.connect(self.Action_Make_Table_Group)
        # TODO: maybe automate an initial reload on tab loading
        # if paths are set up in settings.
        
        # Force the initial splitter position.
        # Note: these are pixel sizes, that then stretch to fill the
        # width, but internally it upsizes these based on the original
        # box min sizes (apparently), so just set the sizes to something
        # huge to ensure the ratios go through.
        self.hsplitter.setSizes([1000,2000])
        
        self.Init_Checkboxes()
        return
    

    def Init_Checkboxes(self):
        '''
        Name and connect up the checkboxes from the parent window.
        '''
        # For now, these boxes are pre-created but not named.
        # 0-3 are left to right.
        checkboxes = [
            self.widget_table_checkBox_0,
            self.widget_table_checkBox_1,
            self.widget_table_checkBox_2,
            self.widget_table_checkBox_3,
            ]

        # Go through columns in display order.
        box_index = 0
        for column_key, column_name in zip(self.table_model.column_keys,
                                           self.table_model.column_headers):            
            # Get the next checkbox.
            checkbox = checkboxes[box_index]
            # Name it.  TODO: maybe tooltip.
            checkbox.setText(column_name)

            # Connect up its action.
            # This will use a lambda function trick, like was done
            # with the style selector.
            checkbox.stateChanged.connect(
                lambda state, column = column_key: self.table_model.Action_Checkbox_Changed(
                    state, column))

            # Do an initial call to set up the table state.
            self.table_model.Action_Checkbox_Changed(
                checkbox.isChecked(), column_key)

            # Increment for next loop.
            box_index += 1
        return


    def Soft_Refresh(self):
        '''
        Does a partial refresh of the table, redrawing the current
        items. A call to Live_Editor.Reset_Current_Item_Values should
        preceed this, shared across all pages being refreshed.
        '''
        self.table_model.Redraw()
        return


    def Action_Make_Table_Group(self):
        '''
        Update button was presssed; clear loaded files and rerun
        the plugin to gather the table group and set up the tree.
        '''
        # Disable the button while working.
        self.widget_Table_Update.setEnabled(False)

        # Reset the live editor table group that is be re-requested.
        # This will fill in new items that may get created by the
        # user script.
        self.Queue_Thread(
            Live_Editor.Get_Tree_View,
            self.table_name, 
            rebuild = True,
            )
        return


    def Reset_From_File_System(self):
        '''
        Trigger regather of the table group on reset.
        '''
        self.Action_Make_Table_Group()
        return


    def Handle_Thread_Finished(self, return_value):
        '''
        Catch the returned table_group and updated the widgets.
        '''
        super().Handle_Thread_Finished()
        # Turn the button back on, before handling the response
        # (in case it gets an error, this lets it be rerun).
        self.widget_Table_Update.setEnabled(True)

        # Pass the Edit_Tree_View down to the model.
        self.tree_model .Set_Edit_Tree_View(return_value)
        #self.table_model.Set_Edit_Tree_View(return_value)
        return


    def Close(self):
        '''
        Prepare this window for closing, either at shutdown or
        on tab closure.
        '''
        super().Close()
        # Since models across tabs are sharing Edit_Items, and
        # hence Q_Item_Groups, and those recycle QStandardItems,
        # each model should have all of its items detached before
        # closing (to avoid "underlying C/C++ object has been deleted"
        # errors).
        # This is only needed for tables, for now.
        self.table_model.Release_Items()
        return


from pathlib import Path

from PyQt5.uic import loadUiType
from PyQt5 import QtWidgets, QtCore, QtGui

from ..Shared import Tab_Page_Widget
from ...Transforms.Live_Editor import Live_Editor

# Load the .ui file into a reuseable base class.
# This will return the designer generated class ("form"), and
# the Qt base class it is based on (QWidget in this case).
# http://pyqt.sourceforge.net/Docs/PyQt5/designer.html
gui_file = Path(__file__).parents[1] / 'x4c_gui_table_tab.ui'
generated_class, qt_base_class = loadUiType(str(gui_file))


# Ignore the Qt Designer base class and use Tab_Page_Widget
# instead. Designer doesn't allow promotion of it for some
# reason.
class Edit_Table_Window(Tab_Page_Widget, generated_class):
    '''
    Window used for editing table data.
    Intended to be replicated across multiple tabs for different
    table groups.

    Widget names:
    * widget_tree_view
    * widget_item_info
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
      - TODO: move away from defaulting this to 'weapons'.
    '''
    def __init__(self, parent, window, table_name = 'weapons'):
        super().__init__(parent, window)
        self.table_name = table_name

        # Link the tree to the list view, so it can
        # updated it when item selections change.
        self.widget_tree_view.widget_item_info = self.widget_item_info

        # Want the placeholder along the top bar to be invisible
        # but still take space.
        # It is a little tricky to hide the placeholder; it will
        # normally stop taking space when invisible; use the sizePolicy
        # to adjust it.
        self.widget_Hideme.setVisible(False)
        # Note: cannot edit the sizepolicy directly; need to pull it
        # out, modify it, and set it back to update properly.
        sizepolicy = self.widget_Hideme.sizePolicy()
        sizepolicy.setRetainSizeWhenHidden(True)
        self.widget_Hideme.setSizePolicy(sizepolicy)


        # Trigger button for loading the table.
        self.widget_Table_Update.clicked.connect(self.Action_Make_Table_Group)
        
        # Force the initial splitter position, because qt designer is
        #  dumb as a rock about splitters.
        # Give extra space to the right side, since it has 5 columns.
        # TODO: look into this; it still splits 1:1.
        self.hsplitter.setSizes([1,4])

        # Call delayed init on the item info viewer, since it
        #  will look at the check box widgets held here.
        self.widget_item_info.Delayed_Init()
        return
    

    def Soft_Refresh(self):
        '''
        Does a partial refresh of the table, redrawing the current
        items. A call to Live_Editor.Reset_Current_Item_Values should
        preceed this, shared across all pages being refreshed.
        '''
        self.widget_tree_view.Soft_Refresh()


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
            Live_Editor.Get_Table_Group,
            self.table_name, 
            rebuild = True,
            )
        return


    def Handle_Thread_Finished(self, return_value):
        '''
        Catch the returned table_group and updated the widgets.
        '''
        super().Handle_Thread_Finished()
        # Pass the table group down to the tree viewer.
        self.widget_tree_view.Set_Table_Group(return_value)
        # Turn the button back on.
        self.widget_Table_Update.setEnabled(True)
        return
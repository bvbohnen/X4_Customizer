'''
Widget(s) for viewing generated tables holding x4 data.
The initial test version of this will be just for weapons, with
some hooks for later generalization.
'''

from itertools import chain
from PyQt5 import QtWidgets

from ..Analyses import Print_Weapon_Stats
from Framework import Settings
from Framework import File_System

class Widget_X4_Table_Tree(QtWidgets.QTreeWidget):
    '''
    Tree view of the table entries, by name and possibly categorized.
    Clicking a plugin will signal a separate documentation
    window to display info (field names and data values).

    Attributes:
    * table
      - List of lists holding the table info, already sorted for
        some nice display order.
      - The first row holds column headers; the first column holds the
        preferred display name of the entry.
    * widget_item_info
      - QGroupBox widget that will display the item info.
      - Should be set up by the parent after initial init.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.currentItemChanged.connect(self.Handle_currentItemChanged)
        return


    def Delayed_Init(self):
        '''
        Hooks up some widgets and actions after the gui has
        initialized fully, and all widgets are available.
        '''
        parent = self.parent
        # Note: this should all be cleaned up when setting up
        # a template window to be added to generated tabs.
        self.widget_item_info = parent.widget_weapons_info

        # It is a little tricky to hide the placeholder; it will
        # normally stop taking space when invisible.
        parent.widget_Hideme.setVisible(False)
        # Note: cannot edit the sizepolicy directly; need to pull it
        # out, modify it, and set it back to update properly.
        sizepolicy = parent.widget_Hideme.sizePolicy()
        sizepolicy.setRetainSizeWhenHidden(True)
        parent.widget_Hideme.setSizePolicy(sizepolicy)

        # Trigger button for loading the table.
        parent.widget_Table_Update.clicked.connect(self.Action_Make_Table)
        
        # Force the initial splitter position, because qt designer is
        # dumb as a rock about splitters.
        # TODO: do this for other splitters, though they behave slightly
        # better so far.
        parent.hsplitter_weapons.setSizes([1,1])
        return

        
    # TODO: make some of this thread stuff generic, since it is
    # shared with script launching.
    def Action_Make_Table(self):
        '''
        Update button was presssed; clear loaded files and rerun
        the plugin to gather the table and set up the tree.
        '''
        # Do nothing if a thread is running.
        if self.parent.worker_thread.isRunning():
            return
        
        # Reset the Settings, so that it will do path checks again.
        Settings.Reset()
        # Ensure the settings are updated from gui values.
        self.parent.widget_settings.Store_Settings()

        # Clear out the file system from any prior run changes.
        # TODO: consider somehow setting up multiple file systems,
        # and using a temporary one for this.
        # TODO: consider having the game files hold three copies
        # of their xml: vanilla, patched with other extensions,
        # patched with all extensions; then it would be easier
        # to switch table sources; though perhaps having 3 file
        # systems would work just as well.
        File_System.Reset()


        # Tweak Settings based on radio buttons.
        # TODO: consider restoring settings back to originals, though
        # it shouldn't matter since anything that uses the settings
        # should be restoring them from gui selections anyway.
        # If vanilla only, ignore extensions.
        if self.parent.widget_Table_Vanilla_button.isChecked():
            Settings.ignore_extensions = True
        # If wanting the customizer extension to be included.
        elif self.parent.widget_Table_Customized_button.isChecked():
            Settings.ignore_extensions = False
            Settings.ignore_output_extension = False
        else:
            Settings.ignore_extensions = False
            Settings.ignore_output_extension = True

        
        self.parent.worker_thread.Set_Function(
            Print_Weapon_Stats,
            return_tables = True)
        # Listen for the 'finished' signal.
        self.parent.worker_thread.finished.connect(self.Handle_Thread_Finished)

        # Disable the button while working.
        self.parent.widget_Table_Update.setEnabled(False)

        # Start the thread.
        self.parent.worker_thread.Start()

        return


    def Handle_Thread_Finished(self):
        '''
        Update widgets up after the plugin thread has finished.
        '''
        # Stop listening.
        self.parent.worker_thread.finished.disconnect(self.Handle_Thread_Finished)
        
        # Load in the table from the thread results.
        # Just grab the first one for testing for now.
        self.table = self.parent.worker_thread.return_value[0]

        # Clear out old table items.
        # Note: existing items cannot easily be reused, since their
        # tree structure might change (eg. it's not always a flat list).
        # Tree widgets make this easy.
        self.clear()

        # Set up the tree view.
        # TODO: add in categories in some intelligent way.
        # Skip the first row, which just has headers.
        for index_m1, row in enumerate(self.table[1:]):

            # Make a new leaf item.
            item = QtWidgets.QTreeWidgetItem()
            # Attach the widget item to the parent tree.
            self.addTopLevelItem(item)

            # Set the name in column 0.
            item.setText(0, row[0])
            
            # For convenience, annotate the item with its table index.
            # This is real index (including the column headers row).
            item.table_index = index_m1 +1

        # Display info on the first item by default.
        self.widget_item_info.Update(self.table[0], self.table[1])
            
        self.expandAll()

        self.parent.widget_Table_Update.setEnabled(True)
        return


    def Handle_currentItemChanged(self, new_item = None):
        '''
        A different item was clicked on.
        '''
        # Ignore if it doesn't have a table index (eg. could be a
        # category header).
        if not hasattr(new_item, 'table_index'):
            return

        # Pull out two lists: column headers and item data.
        headers = self.table[0]
        values  = self.table[new_item.table_index]

        # Set the display widget to update.
        self.widget_item_info.Update(headers, values)
        return

    
class Widget_X4_Table_Item_Info(QtWidgets.QGroupBox):
    '''
    Viewer for a selected table entry's attributes and values.
    Constructed with a QGroupBox, offering potential user input
    in the future (if editing support ever added).

    * field_widgets
      - List of QLabels holding field text, in row order.
      - Some number of these may be set invisible/innactive when unused.
      - More are added as needed to capture all fields of the
        latest display.
    * value_widgets
      - List of QLineEdits holding values, in row order.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.field_widgets = []
        self.value_widgets = []

        # Set up a new layout, form style (rows with 2 columns).
        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)
        # TODO: consider if field names could always be the same,
        # in which case the entries can be initialized and just
        # their text updated.
                
        return


    def Update(self, fields, values):
        '''
        Update the display to a new item.

        * fields
          - List of names of the fields being displayed.
        * values
          - List of matching values.
        '''
        '''
        Note: it appears that deleting widgets is a big headache, so updating
        the item display when the number of fields changes cannot be done
        by wiping and recreating row widgets.
        For a cleaner, though slightly more complicated, solution, this
        code will create rows as needed to capture all fields, then
        will hide excess rows leftover from prior displays, and finally
        will update the row widgets with the latest update info.
        '''

        # Start with row expansion, as needed.
        while len(fields) > len(self.field_widgets):

            field_widget = QtWidgets.QLabel()
            # In prep for possibly editing this in the future, set
            # up QLineEdit widgets to hold the values. Set them
            # read only, though.
            value_widget = QtWidgets.QLineEdit()
            value_widget.setReadOnly(True)
            
            # Set up a new layout row.
            self.layout().addRow(field_widget, value_widget)
            # Record the widgets for convenient lookup.
            self.field_widgets.append(field_widget)
            self.value_widgets.append(value_widget)


        # Hide any excess from the last update.
        # For now, this is easiest to do by hiding all widgets,
        # then displaying them again as they are filled in.
        for widget in chain(self.field_widgets, self.value_widgets):
            widget.setVisible(False)


        # Can now fill in the display info.
        for index, (field, value) in enumerate(zip(fields, values)):
        
            self.field_widgets[index].setText(field)
            self.value_widgets[index].setText(value)
            self.field_widgets[index].setVisible(True)
            self.value_widgets[index].setVisible(True)
                        
        return
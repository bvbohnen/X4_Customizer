
from PyQt5 import QtWidgets

from .Edit_Item import Widget_Edit_Item

class Widget_X4_Table_Item_Info(QtWidgets.QGroupBox):
    '''
    Viewer for a selected table entry's attribute names with edit_items
    or display_items. This will have 5 columns: field names, values for
    vanilla, patched, edited, and current. Only the edited column
    will be interractive.

    Attributes:
    * widgets_dict
      - Dict of lists of widgets, intended for reuse.
      - Keys are ['fields','vanilla','patched','edited','current']
      - Fields:
        - QLabels with attribute name text.
      - Edited:
        - QLineEdit boxes, generally allowing user input when associated
          with items that aren't read_only.
      - Vanilla, patched, current:
        - QLineEdit read_only boxes displaying static information.
      - Each list will be the same length, and will grow to the maximum
        amount needed at any display update.
      - The first widget in each list is a label.
      - Unused list entires are set invisible/innactive, and are flagged
        as 'in_use = False'.
    * column_visibility_dict
      - Dict, keyed by widget_dict key, holding a Bool: True to display
        the column, False to hide it.
    * current_object_view
      - The Object_View currently displayed.
    '''
    # Keys for the widget lists, in display order.
    widget_keys = ['fields','vanilla','patched','edited','current']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_object_view = None

        # Add column heading QLabels to start each list.
        self.widgets_dict = {
            'fields'  : [QtWidgets.QLabel('Fields')],
            'vanilla' : [QtWidgets.QLabel('Vanilla')],
            'patched' : [QtWidgets.QLabel('Diff Patched')],
            'edited'  : [QtWidgets.QLabel('Edited' )],
            'current' : [QtWidgets.QLabel('Post Script')],
            }

        # Display all columns by default.
        self.column_visibility_dict = {x:True for x in self.widget_keys}

        # Set up a new layout, grid style for multiple columns.
        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)

        # Add the column labels, and set their in_use tag.
        for key, widget_list in self.widgets_dict.items():
            widget = widget_list[0]
            widget.in_use = False
            self.Add_Layout_Widget(widget, 0, key)                
        return


    def Delayed_Init(self):
        '''
        Name and connect up the checkboxes from the parent window.
        TODO: maybe move this to parent init.
        '''
        # For now, these boxes are pre-created but not named.
        # 0-3 are left to right.
        checkboxes = [
            self.window.widget_table_checkBox_0,
            self.window.widget_table_checkBox_1,
            self.window.widget_table_checkBox_2,
            self.window.widget_table_checkBox_3,
            ]

        # Go through columns in display order.
        box_index = 0
        for column_name in self.widget_keys:

            # No box for fields.
            if column_name == 'fields':
                continue

            # Get the next checkbox.
            checkbox = checkboxes[box_index]

            # Look up the display name and write it.
            checkbox.setText(self.widgets_dict[column_name][0].text())

            # Init checked state to on.
            # TODO: maybe save this as part of a session.
            # TODO: this comes up unchecked on a new tab?
            checkbox.setChecked(True)

            # Connect up its action.
            # This will use a lambda function trick, like was done
            # with the style selector.
            checkbox.stateChanged.connect(
                lambda state, column = column_name: self.Action_Checkbox_Changed(
                    state, column))

            # Increment for next loop.
            box_index += 1
        return


    def Action_Checkbox_Changed(self, state, column):
        '''
        Hide or show columns based on checkbox state.
        Note: state is 0 for unchecked, 2 for checked, with 1 reserved
        for intermediate on tristate boxes (not used here).
        '''
        # Update the visility tracking dict.
        self.column_visibility_dict[column] = state == 2
        # Pass to another function to handle showing/hiding columns.
        self.Update_Column_Visibilities()
        return


    def Update_Column_Visibilities(self):
        '''
        Updates the visibility state of widgets in each column
        based on checkbox state.
        '''
        for column_name, widget_list in self.widgets_dict.items():
            for widget in widget_list:
                # Require a widget to be flagged as in_use to show it;
                # ignore its prior visibility status.
                if widget.in_use and self.column_visibility_dict[column_name]:
                    widget.setVisible(True)
                else:
                    widget.setVisible(False)
        return


    def Add_Layout_Widget(self, widget, row, key):
        '''
        Adds a widget to the layout, selecting the column based
        on the key.
        TODO: maybe take a group of 5 widgets, remove key and row,
        and always add a new row.
        '''
        # This will always add a new row.
        # Note: the rowCount response will always start with 1 row,
        # for some reason. Also, this is only useful if adding all
        # row widgets at once.
        #row = self.layout().rowCount()
        column = self.widget_keys.index(key)
        self.layout().addWidget(widget, row, column)

        # Column headers want to expand excessively if there aren't
        # many rows; try to keep their size down here.
        # TODO: find a better solution; this balances the rows, but
        # still has vertical stretch when there are few rows.
        widget.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                             QtWidgets.QSizePolicy.Minimum)

        # Start out hidden.
        widget.setVisible(False)
        return

    
    def Handle_Widget_Redraw_Request(self):
        '''
        Redraw the window when a widget requests it.
        For use when item refrences change.
        '''
        # This has a desire to trigger during its own draw process
        # when setting widget text; to suppress, don't redraw when
        # current_object_view is None, and make sure it is None
        # during drawing.
        if self.current_object_view != None:
            self.Update(self.current_object_view)
        return


    def Update(self, object_view):
        '''
        Update the display to a new item.

        * object_view
          - The Object_View that will supply labels and items to display.
        '''
        '''
        Note: it appears that deleting widgets is a big headache, so updating
        the item display when the number of fields changes cannot be done
        by wiping and recreating row widgets.
        For a cleaner though slightly more complicated solution, this
        code will create rows as needed to capture all fields, then
        will hide excess rows leftover from prior displays, and finally
        will update the row widgets with the latest update info.
        '''
        # Set this to None while drawing, to prevent spurious redraws.
        self.current_object_view = None

        # Gather the dict, keyed by version, holding item lists.
        version_items_list_dict = object_view.Get_Display_Version_Items_Dict()

        # From this, get the labels and descriptions for each row.
        # Some rows may be partially None, to avoid those when picking
        #  sampled items.
        labels       = []
        descriptions = []
        for item_row in zip(*version_items_list_dict.values()):
            for item in item_row:
                if item != None:
                    break
            labels      .append(item.display_name)
            descriptions.append(item.description)
        row_count = len(labels)

            
        # Start with row expansion, as needed.
        # Don't count the widget headers for this.
        while row_count > len(self.widgets_dict['fields'])-1:
            row = len(self.widgets_dict['fields'])

            # Set up a new layout row with 5 columns.
            # Loop over the lists to append to.
            for key, widget_list in self.widgets_dict.items():

                # Create a widget based on field name.
                if key == 'fields':
                    widget = QtWidgets.QLabel(self)
                else:
                    # Give the edit_item widgets their value version.
                    widget = Widget_Edit_Item(self, version = key)
                    # Hook into its redraw signal.
                    widget.redraw_request.connect(self.Handle_Widget_Redraw_Request)

                # Record to the local list and to the qt layout.
                widget_list.append(widget)
                self.Add_Layout_Widget(widget, row, key)


        # Hide any excess from the last update.
        # Note: when redrawing a view, doing a full hide + reshow
        # causes the scroll bar to jump to the bottom of the layout.
        # To avoid this problem, be conservative with the visibility
        # changes here.
        for widget_list in self.widgets_dict.values():
            for row, widget in enumerate(widget_list):

                # Low rows become visible; adjust by 1 for the headers.
                if row < row_count +1:
                    widget.setVisible(True)
                    widget.in_use = True
                else:
                    # High rows invisible.
                    widget.setVisible(False)
                    # Annotate as not being in_use.
                    # This helps when columns are shown/hidden to have a
                    # way to remember which cells are too far down.
                    widget.in_use = False


        # If there are any items being displayed, unhide the column headers.
        if labels:
            for widget_list in self.widgets_dict.values():
                widget_list[0].setVisible(True)


        # Can now fill in the display info.
        for row in range(row_count):

            # Loop over the widget columns.
            for key, widget_list in self.widgets_dict.items():
                
                # Pick out the widget being updated.
                widget = widget_list[row +1]

                # The fields widget gets label text directly.
                if key == 'fields':
                    widget.setText(labels[row])
                    widget.setToolTip(descriptions[row])                
                else:
                    # Grab the right item for the column.
                    # Top level object items will always match across
                    # versions, but references can mismatch.
                    item = version_items_list_dict[key][row]
                    # Others are handled through their class method.
                    widget.Set_Item(item)


        # When done, maybe hide some columns again based on check boxes.
        self.Update_Column_Visibilities()
        
        # Record the view for redraws.
        self.current_object_view = object_view                                           
        return


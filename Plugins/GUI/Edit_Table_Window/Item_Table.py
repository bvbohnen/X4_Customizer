
from PyQt5 import QtWidgets

from .Edit_Item import Widget_Edit_Item

class Widget_X4_Table_Item_Info(QtWidgets.QGroupBox):
    '''
    Viewer for a selected table entry's attribute names with edit_items
    or display_items. This will have 5 columns: names, and values for
    vanilla, patched, edited, and current. Only the edited column
    will be interractive.

    Attributes:
    * widgets_dict
      - Dict of lists of widgets, intended for reuse.
      - Keys are ['fields','vanilla','patched','edited','current']
      - Fields:  QLabels with attribute name text.
      - Edited:  QLineEdit boxes, generally allowing user input
                 when associated with items that aren't read_only.
      - Vanilla, patched, current: QLineEdit read_only boxes displaying
                 static information.
      - Each list will be the same length, and will grow to the maximum
        amount needed at any display update.
      - The first widget in each list is a label.
      - Unused list entires are set invisible/innactive, and are flagged
        as 'in_use = False'.
    * column_visibility_dict
      - Dict, keyed by widget_dict key, holding a Bool: True to display
        the column, False to hide it.
    '''
    # Keys for the widget lists, in display order.
    widget_keys = ['fields','vanilla','patched','edited','current']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        Name and connect up the checkboxes.
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
                if widget.in_use and self.column_visibility_dict[column_name]:
                    widget.setVisible(True)
                else:
                    widget.setVisible(False)
        return


    def Add_Layout_Widget(self, widget, row, key):
        '''
        Adds a widget to the layout, selecting the column based
        on the key.
        '''
        column = self.widget_keys.index(key)
        self.layout().addWidget(widget, row, column)

        # Prevent vertical stretching; looks bad before a table
        # is loaded and the headers are stretched.
        # -Removed; this failed to shrink the items. Need to use the backup
        # approach of hiding them.
        #widget.sizePolicy().setVerticalPolicy(QtWidgets.QSizePolicy.Minimum)
        #widget.sizePolicy().setVerticalStretch(QtWidgets.QSizePolicy.Minimum)
        #widget.sizePolicy().setHorizontalPolicy(QtWidgets.QSizePolicy.Minimum)
        #widget.sizePolicy().setHorizontalStretch(QtWidgets.QSizePolicy.Minimum)

        # Start out hidden.
        widget.setVisible(False)
        return


    def Update(self, fields, items):
        '''
        Update the display to a new item.

        * fields
          - List of names of the fields being displayed.
        * items
          - List of matching Edit_Items or Display_Items or None entries.
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
        # Don't count the widget headers.
        while len(fields) > len(self.widgets_dict['fields'])-1:

            # Set up a new layout row with 5 columns.
            row = len(self.widgets_dict['fields'])

            # Loop over the lists to append to.
            for key, widget_list in self.widgets_dict.items():

                # Create a widget based on field name.
                if key == 'fields':
                    widget = QtWidgets.QLabel(self)
                else:
                    # TODO: maybe only use Widget_Edit_Item for the
                    #  edited column.
                    # Give these the parent right away, to maybe help
                    # with a problem where some don't inherit font.
                    widget = Widget_Edit_Item(self, version = key)

                # Record to the list and to the layout.
                widget_list.append(widget)
                self.Add_Layout_Widget(widget, row, key)


        # Hide any excess from the last update.
        # For now, this is easiest to do by hiding all widgets,
        # then displaying them again as they are filled in.
        for widget_list in self.widgets_dict.values():
            for widget in widget_list:
                widget.setVisible(False)
                # Annotate as not being in_use.
                # This helps when columns are shown/hidden to have a
                # way to remember which cells are too far down.
                widget.in_use = False


        # If there are any items being displayed, unhide the column headers.
        if fields:
            for widget_list in self.widgets_dict.values():
                widget_list[0].setVisible(True)

        # Can now fill in the display info.
        for index, (field, item) in enumerate(zip(fields, items)):

            # Loop over the widget columns.
            for key, widget_list in self.widgets_dict.items():

                # Pick out the widget being updated.
                widget = widget_list[index +1]
                # Flip it to visible.
                widget.setVisible(True)
                widget.in_use = True

                # The fields widget gets field text directly.
                if key == 'fields':
                    widget.setText(field)
                    continue
                
                else:
                    # Others are handled through their class method.
                    widget.Set_Item(item)


        # When done, maybe hide some columns again based on check boxes.
        self.Update_Column_Visibilities()
                                           
        return


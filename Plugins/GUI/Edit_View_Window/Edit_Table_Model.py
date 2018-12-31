
from PyQt5 import QtWidgets, QtCore, QtGui
#from .Edit_Item import Widget_Edit_Item
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush


class Edit_Table_Model(QStandardItemModel):
    '''
    Model container for an Edit_Tree_View, to interract with
    a table view widget.

    Attributes:
    * qt_view
      - Table view in qt showing this model.
    * column_visibility_dict
      - Dict, keyed by widget_dict key, holding a Bool: True to display
        the column, False to hide it.
    * current_object_view
      - The Object_View currently displayed.
    '''
    # Keys for the widget lists, in display order.
    widget_keys = ['fields','vanilla','patched','edited','current']

    column_keys    = ['vanilla','patched','edited','current']
    column_headers = ['Vanilla','Diff.Patched','Edited','PostScript']

    def __init__(self, window, qt_view):
        super().__init__(window)
        self.window = window
        self.current_object_view = None
        self.qt_view = qt_view
        
        # Set the column headers.
        self.setHorizontalHeaderLabels(self.column_headers)

        # Set the columns to resize.
        # This is an annoying chain of lookups, in keeping with
        # model/views being overcomplicated.
        self.qt_view.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch )

        # Display all columns by default.
        # This provides some dummy terms for when the window
        # initializes these one at a time (which then do an
        # update call that needs all of them filled in).
        self.column_visibility_dict = {x:True for x in self.column_keys}

        self.itemChanged.connect(self.Handle_itemChanged)
        return
    

    def Action_Checkbox_Changed(self, state, column):
        '''
        Hide or show columns based on checkbox state.
        Note: state is 0 for unchecked, 2 for checked, with 1 reserved
        for intermediate on tristate boxes (not used here).
        '''
        # Update the visility tracking dict.
        self.column_visibility_dict[column] = bool(state)
        # Pass to another function to handle showing/hiding columns.
        self.Update_Column_Visibilities()
        return


    def Update_Column_Visibilities(self):
        '''
        Updates the visibility state of widgets in each column
        based on checkbox state.
        '''
        for index, column_name in enumerate(self.column_keys):
            # If this column checkbox is checked, unhide, else hide.
            self.qt_view.setColumnHidden(
                index, not self.column_visibility_dict[column_name])
        return
    
    
    def Handle_Widget_Redraw_Request(self):
        '''
        Redraw the window when a widget requests it.
        For use when item references change.
        '''
        # This has a desire to trigger during its own draw process
        # when setting widget text; to suppress, don't redraw when
        # current_object_view is None, and make sure it is None
        # during drawing.
        if self.current_object_view != None:
            self.Update(self.current_object_view)
        return


    def Handle_itemChanged(self, item):
        '''
        This is called when an item's data is changed, either
        at creation (should ignore) or by user editing (should
        catch).
        '''
        # Ignore during the object draw process.
        if self.current_object_view == None:
            return
        # TODO
        return


    def Update(self, object_view):
        '''
        Update the display to a new item.

        * object_view
          - The Object_View that will supply labels and items to display.
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

        # Resize to the right number of rows.
        # Could also clear(), but that would require regenerating rows
        # and also destroys the column headers.
        # TODO: delink existing q_items from edit_items as needed;
        #  this will probably be done during q_item setup.
        self.setRowCount(row_count)
        
        # Apply the labels.
        # TODO: maybe reuse existing items, but it probably isn't
        # worth it.
        for row in range(row_count):
            label_item = QStandardItem(labels[row])
            label_item.setToolTip(descriptions[row])
            self.setVerticalHeaderItem(row, label_item)
               

        # Can now fill in the display info.
        for row in range(row_count):
            for col, version in enumerate(self.column_keys):
              
                # Grab the right item for the column.
                # Top level object items will always match across versions,
                # but references can mismatch.
                item = version_items_list_dict[version][row]

                q_item = QStandardItem(item.Get_Value(version))
                q_item.edit_item = item
                q_item.version = version
                self.Polish_Item(q_item)
                self.setItem(row, col, q_item)

                # Others are handled through their class method.
                #widget.Set_Item(item)


        # This may be unnecessary, but do it anyway.
        #self.Update_Column_Visibilities()
        return


    def Polish_Item(self, item):
        '''
        Polish an item with formatting, editability, etc.
        TODO: move to QStandardItem subclass, maybe.
        '''
        # Set up editability.
        if item.edit_item.read_only or item.version != 'edited':
            item.setEditable(False)
            # TODO: shade this.
            brush = QBrush(QtCore.Qt.SolidPattern)
            brush.setColor(QtGui.QColor(247, 247, 247))
            item.setBackground( brush )
        else:
            item.setEditable(True)

        # TODO: live editing polish, eg. highlights on modified items?
        return

        ## Start with row expansion, as needed.
        ## Don't count the widget headers for this.
        #while row_count > len(self.widgets_dict['fields'])-1:
        #    row = len(self.widgets_dict['fields'])
        #
        #    # Set up a new layout row with 5 columns.
        #    # Loop over the lists to append to.
        #    for key, widget_list in self.widgets_dict.items():
        #
        #        # Create a widget based on field name.
        #        if key == 'fields':
        #            widget = QtWidgets.QLabel(self)
        #        else:
        #            # Give the edit_item widgets their value version.
        #            widget = Widget_Edit_Item(self, version = key)
        #            # Hook into its redraw signal.
        #            widget.redraw_request.connect(self.Handle_Widget_Redraw_Request)
        #
        #        # Record to the local list and to the qt layout.
        #        widget_list.append(widget)
        #        self.Add_Layout_Widget(widget, row, key)
        #
        #
        ## Hide any excess from the last update.
        ## Note: when redrawing a view, doing a full hide + reshow
        ## causes the scroll bar to jump to the bottom of the layout.
        ## To avoid this problem, be conservative with the visibility
        ## changes here.
        #for widget_list in self.widgets_dict.values():
        #    for row, widget in enumerate(widget_list):
        #
        #        # Low rows become visible; adjust by 1 for the headers.
        #        if row < row_count +1:
        #            widget.setVisible(True)
        #            widget.in_use = True
        #        else:
        #            # High rows invisible.
        #            widget.setVisible(False)
        #            # Annotate as not being in_use.
        #            # This helps when columns are shown/hidden to have a
        #            # way to remember which cells are too far down.
        #            widget.in_use = False
        #
        #
        ## If there are any items being displayed, unhide the column headers.
        #if labels:
        #    for widget_list in self.widgets_dict.values():
        #        widget_list[0].setVisible(True)
        #
        #
        ## Can now fill in the display info.
        #for row in range(row_count):
        #
        #    # Loop over the widget columns.
        #    for key, widget_list in self.widgets_dict.items():
        #        
        #        # Pick out the widget being updated.
        #        widget = widget_list[row +1]
        #
        #        # The fields widget gets label text directly.
        #        if key == 'fields':
        #            widget.setText(labels[row])
        #            widget.setToolTip(descriptions[row])                
        #        else:
        #            # Grab the right item for the column.
        #            # Top level object items will always match across
        #            # versions, but references can mismatch.
        #            item = version_items_list_dict[key][row]
        #            # Others are handled through their class method.
        #            widget.Set_Item(item)
        #
        #
        ## When done, maybe hide some columns again based on check boxes.
        #self.Update_Column_Visibilities()
        #
        ## Record the view for redraws.
        #self.current_object_view = object_view                                           
        #return



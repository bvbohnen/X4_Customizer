
from collections import defaultdict
from PyQt5.QtGui import QStandardItem, QBrush
from PyQt5 import QtCore, QtGui

from Framework.Live_Editor_Components import Display_Item


class Q_Item_Group:
    '''
    This will generate and track a group of QStandardItems which
    associate with a single Live_Editor Edit_Item.
    This simplifies the reverse link from Edit_Items to here, as
    they only need to request a group update.
    When a new gui item is displayed, if its Edit_Item has no attached
    group, then a new group should be created.

    Attributes:
    * edit_item
      - Either an Edit_Item or Display_Item object.
    * version_q_items
      - Dict, keyed by version, of QStandardItems in this group.
    '''
    def __init__(
            self, 
            edit_item
        ):
        self.edit_item = edit_item
        self.q_items = defaultdict(list)


    def New_Q_Item(self, version):
        '''
        Returns a QStandardItem for a model that wants to display
        the current edit_item and version.
        It will be annotated with 'q_item_group', a link back to here.
        If a prior created QStandardItem is no longer attached to
        a model, it will be reused.
        '''
        # Check if there are any unused existing items.
        for q_item in self.q_items[version]:
            if not q_item.model():
                return q_item

        # If here, a new item is needed.
        q_item = QStandardItem()
        q_item.q_item_group = self
        q_item.version    = version
        self.q_items[version].append(q_item)
        # Just update all items for now, instead of splitting code
        # to have a single item updater.
        self.Update(version)
        return q_item


    def Value_Changed(self, q_item):
        '''
        This should be called when the user changes the q_item's value.
        The change will be pushed to the Edit_Item and other q_item
        displays.
        '''
        # Note: currently using setText in Update will cause a
        # signal to be emitted that ends up back here, even for
        # non-edit items that were just updating their display.
        # Ignore non-edit items.
        # As a workaround, ignore non-edit items, and ignore cases
        # where the value is the same as the original.
        if q_item.version != 'edited':
            return
        if self.edit_item.Get_Value(q_item.version) == q_item.text():
            return

        self.edit_item.Set_Value(q_item.version, q_item.text())
        # Do a general update of all items of this version.
        # Note: reference items may end up calling for their
        # model to redraw.
        self.Update(q_item.version, value_changed = True)

        return


    def Update(self, version, value_changed = False):
        '''
        Pulls the edit_item value and does a fresh update of all q_items.
        This gets called by New_Q_Item() with all version types, and by
        Value_Changed() and Display_Items for the 'edited' version.
        TODO: think about how to push window redraw requests back out
        to the views.

        * value_changed
          - Bool, if True then this is handling a new value, which will
            cause reference items will force a table model redraw when,
            and others to resize the table rows.
          - Should be left False during table drawing (avoid a loop),
            and only True for user edits.
        '''
        value = self.edit_item.Get_Value(version)
        # Can edit only for the 'edited' version of non-read_only items.
        editable = self.edit_item.read_only == False and version == 'edited'
        modified = self.edit_item.Is_Modified() and version == 'edited'

        # Pick the box coloring.
        background_brush = QBrush(QtCore.Qt.SolidPattern)
        foreground_brush = QBrush(QtCore.Qt.SolidPattern)
        
        if isinstance(self.edit_item, Display_Item):
            background_brush.setColor(QtGui.QColor('antiquewhite'))            
        elif not editable:
            background_brush.setColor(QtGui.QColor(247, 247, 247))
        else:
            background_brush.setColor(QtGui.QColor('white'))

        if modified:
            foreground_brush.setColor(QtGui.QColor('crimson'))
        else:
            foreground_brush.setColor(QtGui.QColor('black'))


        # Note: this will update items that may not be owned by
        # any model currently, which is helpful since new models
        # can use them directly out of New_Q_Item.
        for q_item in self.q_items[version]:
            # TODO: stop this from triggering the item as modified,
            # which causes this update to be called again (but only
            # only, since apparently qt breaks the loop somehow).
            q_item.setText(value)
            q_item.setEditable(editable)
            # Allow dropping on editable items only.
            # TODO: maybe does nothing; when added it didn't get
            # drops working.
            q_item.setDropEnabled(editable)
            q_item.setBackground(background_brush)
            q_item.setForeground(foreground_brush)

            # Blindly tell the view to resize its rows based on contents.
            # TODO: maybe suppress this on the initial drawing of the
            # table, since it will get called on every item of every row.
            if value_changed and q_item.model() != None:
                q_item.model().Resize_Rows()
                

        # For any items that are references, they can just request
        # a table model redraw to update changed cells.
        # Note that this will cause the item to get delinked, and
        # it may not show up in the redrawn table, so don't do anything
        # with it past this point.
        if value_changed and self.edit_item.Is_Reference():
            for q_item in self.q_items[version]:
                if q_item.model() == None:
                    continue
                q_item.model().Redraw()

        return
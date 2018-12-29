
from collections import OrderedDict
from .Edit_Items import Placeholder_Item

class Edit_Table_Group:
    '''
    A group of Edit_Tables intended to be displayed together, mainly for
    output to html.

    Attributes:
    * name
      - String, internal name for the table.
      - Optional now that Edit_Tree_View is the standard form
        for grouping objects.
    * table_dict
      - OrderedDict of Edit_Tables, keyed by their name, in the
        preferred display order.
    '''
    def __init__(self, name = None):
        self.name = name
        self.table_dict = OrderedDict()

    def Add_Table(self, edit_table):
        '''
        Add an Edit_Table to this group, placed at the end.
        '''
        self.table_dict[edit_table.name] = edit_table

    def Get_Tables(self):
        '''
        Returns a list of stored Edit_Tables, in order.
        '''
        return [x for x in self.table_dict.values()]


class Edit_Table:
    '''
    A table of Edit_Object of the same or closely related type,
    which will be displayed together.  Initially this will deal
    ith inter-object references by collecting all items together.

    Attributes:
    * name
      - String, internal name for the table.
      - May be used as a display name.
    * objects_dict
      - OrderedDict, keyed by object name, holding top level Object_Views
        to display, in preferred display order.
    * table
      - List of lists, holding a 2d table of items.
      - The first row is column headers.
      - Each row holds Edit_Item and Display_Item objects (or None) taken from
        the Edit_Object used for that row.
      - Intended for easing display code.
    '''
    '''
    TODO: maybe split out headers.
    * table_column_headers
      - List of strings, labels to use for each table column,
        after filtering out unused item names.
    '''
    def __init__(self, name):
        self.name = name
        self.objects_dict = OrderedDict()
        self.table = None
        return


    def Add_Object(self, object_view):
        '''
        Attach an Edit_Object to this table.
        '''
        self.objects_dict[object_view.name] = object_view


    def Reset_Table(self):
        '''
        Resets the local table, requiring it to be reconstructed.
        This may be useful as a way of dealing with changed object
        references.
        '''
        self.table = None


    def Get_Table(self, version = 'current', rebuild = False):
        '''
        Returns the list of lists holding table items.
        Constructs the table on the first call.
        Columns unused by any object will be pruned out.

        * version
          - String, version of the items to use for evaluating references.
          - Defaults to 'current'.
        '''
        if self.table == None or rebuild:
            # A list of lists will make up the table.
            # First row will be column headers.
            table = []
            
            # This gets a little tricky to pick out what to print, and
            # in what order, once references get involved. Some objects
            # may have missing references, others may ref objects with
            # differing fields, and there may be multiple refs for
            # an object that have overlapping fields.
            # Display of a single object is straightforward, but merging
            # multiple displays onto the same table can be quirky.

            # To get something working, just assume that all objects will
            # have references of the same types, and hence will have
            # matching fields.

            # Collect lists of items from each object.
            for object in self.objects_dict.values():
                # Grab the items for this version.
                items = object.Get_Display_Version_Items_Dict(version = version)[version]
                # Add to the table.
                table.append(items)
                
            # If for some reason tables are not the same size, pad them out.
            # Also sample the first full row to get labels.
            # TODO: maybe do something smarter; this will only work well
            # if there is a single reference that is sometimes missing.
            num_columns = max(len(x) for x in table)
            labels = None
            for row in table:
                # Get labels from a full row.
                if labels == None and len(row) == num_columns:
                    labels = [x.display_name for x in row]
                # Pad out the row with a simple loop.
                while len(row) < num_columns:
                    row.append(None)


            # Go through the constructed table and find columns that
            # don't have meaningful data, to prune them.
            indices_to_remove = []
            for index in range(len(labels)):
                # Consider it unused if all items are Placeholder_Items
                # or None. Leave other items in place, even if they
                # are valueless, in case this table is ever used for
                # display and editing.
                if all(row[index] == None or isinstance(row[index], Placeholder_Item)
                       for row in table):
                    indices_to_remove.append(index)

            # Removal done on second pass.
            # Go from last to first, so the earlier indexes aren't
            # getting shifted.
            for index in reversed(indices_to_remove):
                for row in table:
                    del(row[index])
                del(labels[index])
                       
            # Insert labels to be the new first row.
            table.insert(0, labels)

            # Store the table.
            self.table = table
        return self.table


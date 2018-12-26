
from collections import OrderedDict

class Edit_Table_Group:
    '''
    A group of Edit_Tables intended to be displayed together,
    eg. on the same tree view in the gui or sequentially in
    the same output html file.

    Attributes:
    * name
      - String, internal name for the table.
    * table_dict
      - OrderedDict of Edit_Tables, keyed by their name, in the
        preferred display order.
    '''
    def __init__(self, name):
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
    TODO: better/dynamic reference support.

    Attributes:
    * name
      - String, internal name for the table.
      - May be used as a display name; decision pending at time of comment.
    * objects_dict
      - OrderedDict, keyed by object name, holding top level Edit_Objects
        to display, in preferred display order.
      - Note: Objects may have references to other objects not captured
        in this dict.
    * item_names_ordered_dict
      - OrderedDict pairing item names in the objects with their
        display names, in the preferred display order.
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
        self.item_names_ordered_dict = OrderedDict()
        return


    def Add_Object(self, edit_object):
        '''
        Attach an Edit_Object to this table.
        '''
        self.objects_dict[edit_object.name] = edit_object

    def Reset_Table(self):
        '''
        Resets the local table, requiring it to be reconstructed.
        This may be useful as a way of dealing with changed object
        references. TODO: maybe offer way to recompute just a row
        when references are changed.
        '''
        self.table = None


    def Get_Table(self):
        '''
        Returns the list of lists holding table items.
        Constructs the table on the first call.
        '''
        if self.table == None:
            # A list of lists will make up the table.
            # First entry is the weapon type.
            # Second entry is the column labels.
            table = []

            # Determine which item names are in use.
            item_names_used = set()
            for object in self.objects_dict.values():
                for item in object.Get_All_Items():
                    item_names_used.add(item.name)
        
            # Join the ordered list of display names with the used attributes,
            # to get which column headers will be active.
            item_names_to_print = [name for name in self.item_names_ordered_dict
                                    if name in item_names_used]
            
            # Record column labels on the first row.
            table.append([self.item_names_ordered_dict[x] 
                            for x in item_names_to_print])

            # Loop over the objects; these should have been added in
            # the preferred display order already.
            for name, object in self.objects_dict.items():
                line = []
                table.append(line)
                for item_name in item_names_to_print:

                    # Get the object's item of this name, or None if
                    # it doesn't have one.
                    item = object.Get_Item(item_name)
                    line.append(item)

            # Store the table.
            self.table = table
        return self.table


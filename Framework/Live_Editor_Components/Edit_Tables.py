
from ..Documentation import Doc_Category_Default
_doc_category = Doc_Category_Default('Live_Editor')

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

    def Get_Table_With_Object(self, object_view):
        '''
        Returns the Edit_Table containing the given object_view.
        Assumes as most one such table.
        If no table found, returns None.
        '''
        for table in self.table_dict.values():
            # Search the objects.
            for table_object_view in table.object_view_list:
                if object_view is table_object_view:
                    return table
        return None


class Edit_Table:
    '''
    A table of Edit_Object of the same or closely related type,
    which will be displayed together.  Initially this will deal
    ith inter-object references by collecting all items together.

    Attributes:
    * name
      - String, internal name for the table.
      - May be used as a display name.
    * object_view_list
      - List of tuples of (label, object view), holding top level Object_Views
        to display, in preferred display order.
    * version_table_dict
      - Dict, keyed by version, holding a list of lists, a 2d table of items.
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
        self.object_view_list = []
        self.version_table_dict = {}
        return


    def Add_Object(self, object_view):
        '''
        Attach an Object_View to this table.
        '''
        self.object_view_list.append(object_view)
        return


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
        The 'description' field will be automatically skipped.
        Generated tables are cached; avoid editing the returned table.

        * version
          - String, version of the items to use for evaluating references.
          - Defaults to 'current'.
        '''
        if version not in self.version_table_dict or rebuild:
            
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

            #-Removed; this doesn't work well when objects have potentially
            # differing items or multiple refs.
            ## Collect lists of items from each object.
            #for object in self.objects_dict.values():
            #    # Grab the items for this version.
            #    items = object.Get_Display_Version_Items_Dict(
            #        version = version,
            #        # The descriptions can be long, so skip them.
            #        skipped_item_names = ['description']
            #        )[version]
            #    # Add to the table.
            #    table.append(items)
            #    
            ## If for some reason tables are not the same size, pad them out,
            ##  to catch cases where one object has a reference that another
            ##  is missing.
            ## Also sample the first full row to get labels.
            ## TODO: maybe do something smarter; this will only work well
            ## if there is a single reference that is sometimes missing.
            #num_columns = max(len(x) for x in table)
            #labels = None
            #for row in table:
            #    # Get labels from a full row.
            #    if labels == None and len(row) == num_columns:
            #        labels = [x.display_name for x in row]
            #    # Pad out the row with a simple loop.
            #    while len(row) < num_columns:
            #        row.append(None)

            # Unpack the object views to get edit objects.
            # TODO: maybe always work with edit objects.
            edit_objects = [x.edit_object for x in self.object_view_list]
            
            # Build up the table by working through the object in parallel.
            # References will be unpacked in a matched order, with any
            # object that is missing a ref having it filled with None
            # entries.
            table = self._Get_Object_Group_Items(edit_objects)


            # Find all inter-object references.
            # Note: this will order the refs according to object search
            # order, then its item order, so it could be out of sync
            # with the original reference items if some objects are
            # missing those ref items.
            reference_item_names = []
            for object in edit_objects:
                for item in object.Get_Items():
                    name = item.name
                    if item.Is_Reference() and name not in reference_item_names:
                        reference_item_names.append(name)
                        
            # Set up padding between refs.
            padding = Placeholder_Item(display_name = '', is_separator = True)

            # Go through them, in order.
            for ref_name in reference_item_names:

                # Collect the referenced objects.
                ref_objects = []
                for object in edit_objects:
                    ref_objects.append( object.Get_Reference(ref_name, version))

                # Collect items from the objects.
                ref_table = self._Get_Object_Group_Items(ref_objects)

                # Add to the base table.
                # Note: these rows extend the base rows.
                for base_item_row, ref_item_row in zip(table, ref_table):
                    # Create a padding column.
                    base_item_row.append(padding)
                    base_item_row += ref_item_row
                     
                
            # Collect the column labels, for convenience.
            # These are display names, so differ from field names.
            # Since some column entries can be None, this will search
            # each column to find a non-None and get its label.
            # Also, to verify, this will ensure all the column labels
            # match across items.
            labels = []
            for col in range(len(table[0])):
                label_set = set()
                for row_items in table:
                    item = row_items[col]
                    if item != None:
                        label_set.add(item.display_name)
                # There should have been just one label found.
                assert len(label_set) == 1
                labels.append(label_set.pop())


            # Go through the constructed table and find columns that
            # don't have meaningful data, to prune them.
            # Note: this comes up when there are Placeholder items present.
            indices_to_remove = []
            for index in range(len(labels)):

                # Consider it unused if all items are Placeholder_Items
                # or None. Leave other items in place, even if they
                # are valueless, in case this table is ever used for
                # display and editing. Leave placeholder separators in place.
                if all(row[index] == None 
                       or (isinstance(row[index], Placeholder_Item)
                           and not row[index].is_separator)
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
            self.version_table_dict[version] = table
        return self.version_table_dict[version]


    def _Get_Object_Group_Items(self, object_list):
        '''
        From the given list of objects, select the items to be included,
        and align them so that names match.
        Returns a list of lists of items, or None entries for padding.
        All items in a column will be from the same field name.
        '''
        # If objects have different field amounts, they will be sync'd
        # up here to pad them out so that all objects get entries
        # as necessary (eg. wares with multiple production formulas
        # may cause other wares to pad with None entries at those
        # locations).

        # TODO: move this to an arg.
        skipped_item_names = ['description']
        
        # Start by gathering the fields, in some sort of order.
        # This assumes they are all uniquely named.
        item_fields = []
        # The best way to shuffle these together is unclear, but this
        # will aim to do one object at a time, and do field insertions
        # when a new field is encountered, placing it after the
        # prior name (wherever it is).
        prior_name = None
        for object in object_list:
            # Skip None entries.
            if object == None:
                continue

            # Work through the object items.
            for item in object.Get_Items():
                name = item.name

                # Skip names as requested.
                if name in skipped_item_names:
                    continue

                # Skip if the name is known.
                if name in item_fields:
                    continue

                # If there is a prior name, look for it.
                # (Note: this doesn't work so well when there is no
                # prior but there are existing fields, in which case
                # matching to the following name might be wanted,
                # but that case is not currently expected.)
                if prior_name != None:
                    # Stick this name after the prior one.
                    prior_index = item_fields.index(prior_name)
                    item_fields.insert(prior_index+1, name)
                else:
                    # Stick this name at the end.
                    item_fields.append(name)

                # Update the prior_name for next iteration.
                prior_name = name


        # With the item names sorted out, can now do a pass to fill
        # in the items.
        table = []
        for object in object_list:
            row = []
            table.append(row)

            for field in item_fields:
                if object == None:
                    item = None
                else:
                    # Make sure it comes from the object itself,
                    # not a ref (to be safe).
                    item = object.Get_Item(field, allow_refs = False)
                row.append(item)

        return table
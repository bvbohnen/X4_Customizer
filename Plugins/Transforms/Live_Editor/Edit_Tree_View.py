
from collections import OrderedDict
from .Edit_Items import version_names

class Object_View:
    '''
    Specification for how an object's items should be viewed, including
    ordering of items, display labels, and expansion of references.

    * edit_object
      - The main object being viewed.
    * skipped_item_names
      - List of strings, item names to be ignored.
    '''
    def __init__(self, edit_object, skipped_item_names = None):
        self.edit_object         = edit_object
        if not skipped_item_names:
            skipped_item_names = []
        self.skipped_item_names = skipped_item_names
        return
    

    def Get_Display_Version_Items_Dict(self):
        '''
        Returns a dict keyed by version name and holding lists of
        items, taken from here or first level references.
        Labels may be read from any non-None item in each list row.
        '''
        # TODO: maybe cache this, and reset on reference changes
        # in the object.
        return self.edit_object.Get_Display_Version_Items_Dict(
            skipped_item_names = self.skipped_item_names)



class Edit_Tree_View:
    '''
    Class for specying how a group of objects should be displayed,
    as a tree suitable for the gui.
    Some attempt should be made to have objects in the same category
    use the same display labels, even if some items are left empty,
    for continuity.

    Attributes:
    * name
      - String, internal name of this tree view.
    * tree
      - OrderedDict holding nested OrderedDicts and Object_Views, laying out
        how the tree should be displayed.
      - Keys are the display labels for the gui tree, generally taken
        from object category names or the object names themselves.
      - Flat views will simply have the top OrderedDict filled with
        Object_Views.
    * ???
    '''
    def __init__(self, name):
        self.name = name
        # Start with an empty ordered dict for the tree top level.
        self.tree = OrderedDict()
        return


    def Get_Tree(self):
        'Returns the top tree node.'
        return self.tree

    #-Removed; just let users access 'tree' directly.
    #def Add_Node(self, label, new_node):
    #    '''
    #    Adds a node to the top level of the tree, with the given label.
    #    The node should be either an OrderedDict or Object_View.
    #    '''
    #    assert isinstancew(new_node, (OrderedDict, Object_View))
    #    self.tree[label] = new_node


    # TODO: maybe this would be better as a static method or standalone
    # function.
    def Apply_Filtered_Labels(self, node):#, label_dict):
        '''
        Filters a given set of labels based on items present in
        objects at the given tree node.

        * node
          - OrderedDict holding the Object_Views being updated.
          - Expected to be part of the current tree, but does not
            need to be.
        '''
        '''
        -Removed
        * label_dict
          - OrderedDict holding {item_name : display_label} pairs.
        '''
        # Get a flat list of objects under this node, recursively.
        # TODO; just work with the first level for now.
        object_view_list = node.values()
        assert isinstance(next(iter(object_view_list)), Object_View)
        
        # Determine which item names are in use, for any version of
        #  the object. This should return the main object labels first,
        #  then those of references.
        # Limit to main object, and let references take care of
        #  themselves (eg. if a weapon swaps from bullet to missile,
        #  this static logic can't deal with it nicely).
        # TODO: maybe prune first level refs as well, though that isn't
        #  as safe if refs are changed during live editing.
        item_names_used = set()
        item_names_seen = set()
        for object_view in object_view_list:


            # Get all items, including placeholders, and consider them seen.
            for item in object_view.edit_object.Get_Items(
                    allow_placeholders = True):
                item_names_seen.add(item.name)
            # Get all items without placeholders, and consider them used.
            for item in object_view.edit_object.Get_Items(
                    allow_placeholders = False):
                item_names_used.add(item.name)


        # Items seen but not used can be omitted.
        item_names_not_used = item_names_seen - item_names_used

            
        # Apply to all object views.
        for object_view in object_view_list:
            object_view.skipped_item_names = item_names_not_used

        return
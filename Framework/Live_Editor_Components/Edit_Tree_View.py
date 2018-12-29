
from collections import OrderedDict
from .Edit_Items import version_names
from .Edit_Tables import Edit_Table, Edit_Table_Group

class Object_View:
    '''
    Specification for how an object's items should be viewed, including
    ordering of items, display labels, and expansion of references.

    Attributes:
    * name
      - String, display name for this object in the tree.
    * edit_object
      - The main object being viewed.
    * skipped_item_names
      - List of strings, item names to be ignored.
    '''
    def __init__(self, name, edit_object, skipped_item_names = None):
        self.name = name
        self.edit_object = edit_object
        if not skipped_item_names:
            skipped_item_names = []
        self.skipped_item_names = skipped_item_names
        return
    

    def Get_Display_Version_Items_Dict(self, version = None):
        '''
        Returns a dict keyed by version name and holding lists of
        items, taken from here or first level references.
        Labels may be read from any non-None item in each list row.

        * version
          - Optional, the version to limit responses to.
        '''
        # TODO: maybe cache this, and reset on reference changes
        # in the object.
        return self.edit_object.Get_Display_Version_Items_Dict(
            skipped_item_names = self.skipped_item_names,
            version = version)



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
      - A single tree node should never mix OrderedDicts and Object_Views
        in its children (for now).
    '''
    def __init__(self, name):
        self.name = name
        # Start with an empty ordered dict for the tree top level.
        self.tree = OrderedDict()
        return


    def Get_Tree(self):
        'Returns the top tree node.'
        return self.tree


    def Add_Object(self, label, edit_object, *keys):
        '''
        Adds an Edit_Object to the tree, wrapping it in an Object_View
        automatically.  Multiple keys may be given to place the object
        deeper in the tree; branches will be created automatically.
        '''
        # Start with branch creation.
        # This will loop through keys and trace a path.
        branch_node = self.tree
        for key in keys:
            # If the branch doesn't exist, start it.
            if key not in branch_node:
                branch_node[key] = OrderedDict()
            branch_node = branch_node[key]

        # Can now record the object.
        branch_node[label] = Object_View(label, edit_object)
        return


    #-Removed; just let users access 'tree' directly.
    #def Add_Node(self, label, new_node):
    #    '''
    #    Adds a node to the top level of the tree, with the given label.
    #    The node should be either an OrderedDict or Object_View.
    #    '''
    #    assert isinstancew(new_node, (OrderedDict, Object_View))
    #    self.tree[label] = new_node

    def Get_Branch_Nodes(self, start_node = None):
        '''
        Returns all tree OrderedDict nodes at any level at or below
        the given node.

        * start_node
          - The node to begin at. Defaults to the top tree node.
          - Should be an OrderedDict.
          - This will be included in the return list.
        '''
        if start_node == None:
            start_node = self.tree

        # Could use recursion for this, but try a flatter approach
        # since trees aren't very deep.
        # Track a running list of unvisited nodes, and visit them
        # progressively in a loop.
        found_nodes = []
        unvisited_nodes = [start_node]
        while unvisited_nodes:
            # Sample a node to visit, move to found nodes.
            node = unvisited_nodes.pop(0)
            found_nodes.append(node)

            # If it is not flat, its children are further nodes.
            if not self.Is_Flat(node):
                unvisited_nodes += list(node.values())

        return found_nodes

    
    def Get_Leaf_Nodes(self, start_node = None):
        '''
        Returns all tree Object_View nodes at any level at or below
        the given node.

        * start_node
          - The node to begin at. Defaults to the top tree node.
          - Should be an OrderedDict.
          - This will be included in the return list.       
        '''
        ret_list = []
        # Loop over the branch nodes involved.
        for node in self.Get_Branch_Nodes(start_node):
            # If it is flat (just has leaves), record them.
            if self.Is_Flat(node):
                ret_list += list(node.values())
        return ret_list


    def Sort_Branches(self, start_node = None):
        '''
        Sort all branch nodes at or below the given node, by label.
        This can be used to construct the tree in a lazy order,
        then post-sort it.
        '''
        # Work through the branches.
        for node in self.Get_Branch_Nodes(start_node):
            # Sorting an ordered dict can be done nicely using its
            # move_to_end method.
            for key in sorted(node.keys()):
                node.move_to_end(key)
        return


    def Apply_Filtered_Labels(self, start_node = None):#, label_dict):
        '''
        Filters the object view item names for each branch of the
        tree at or below the given branch.
        
        * start_node
          - The node to begin at. Defaults to the top tree node.
          - Should be an OrderedDict.
          - This will be included in the return list.
        '''
        '''
        -Removed
        * label_dict
          - OrderedDict holding {item_name : display_label} pairs.
        '''
        # Loop over all branches.
        for node in self.Get_Branch_Nodes(start_node):
            # Skip non-flat ones.
            if not self.Is_Flat(node):
                continue

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
            for object_view in node.values():

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
            for object_view in node.values():
                object_view.skipped_item_names = item_names_not_used

        return


    def Is_Flat(self, node = None):
        '''
        Returns True if the given node has a flat object list.
        If no node given, operates on the top tree node.
        '''
        if node == None:
            node = self.tree
        # Sample the first element, and check its type.
        # If it is an object, this should be flat.
        return isinstance( next(iter(node.values())), Object_View)


    def Convert_To_Table_Group(self):
        '''
        Returns an Edit_Table_Group holding the tree contents.
        A table will be formed for each first level tree subnode, or
        for the entire tree if it is a flat list.
        Table columns are not pruned, even if no object uses them.
        '''
        table_group = Edit_Table_Group(self.name)
        
        # Form a dict of lists, holding the objects to assign to
        # each subtable. Inner elements are tuples of (label, object view).
        # Outer key is the original node label (possibly tree name).
        label_object_groups_dict = OrderedDict()

        # Check if this tree has a flat list or not.
        if self.Is_Flat():
            label_object_groups_dict[self.name] = self.Get_Leaf_Nodes(self.tree)

        else:
            # Loop over first level subnodes.
            for label, subnode in self.tree.items():
                label_object_groups_dict[label] = self.Get_Leaf_Nodes(subnode)


        # Make tables for each of these object groups.
        for label, object_group in label_object_groups_dict.items():
            edit_table = Edit_Table(name = label)
            table_group.Add_Table(edit_table)
            for object in object_group:
                edit_table.Add_Object(object)

        return table_group
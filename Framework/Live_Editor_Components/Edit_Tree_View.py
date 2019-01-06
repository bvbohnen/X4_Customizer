
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
    

    def Get_Display_Version_Items_Dict(self, *args, **kwargs):
        '''
        Returns a dict keyed by version name and holding lists of
        items, taken from here or first level references.
        Labels may be read from any non-None item in each list row.
        Args are the same as Edit_Object.Get_Display_Version_Items_Dict.
        Any skipped_item_names fed to here will be joined with the
        view skipped_item_names and passed along.
        '''
        # Fill or extend the skipped_item_names, as needed.
        if 'skipped_item_names' in kwargs:
            kwargs['skipped_item_names'].extend(self.skipped_item_names)
        else:
            kwargs['skipped_item_names'] = self.skipped_item_names
        # Pass along the args/kwargs.
        return self.edit_object.Get_Display_Version_Items_Dict(*args, **kwargs)



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
    * display_name
      - String, name to use for this tree in name displays, such as
        gui tabs or when nested under another tree later.
    * tree
      - List holding nested tuples of (key, node), where nodes are 
        Lists and Object_Views, laying out how the tree should be displayed.
      - Keys are the display labels for the gui tree, generally taken
        from object category names or the object names themselves.
      - Flat views will simply have the top List filled with
        Object_Views.
      - A single tree node should never mix Lists and Object_Views
        in its children (for now).
    * table_group
      - Cached Edit_Table_Group generated from this tree view.
    '''
    def __init__(self, name, display_name = None):
        self.name = name
        self.display_name = display_name if display_name else name
        self.tree = []
        self.table_group = None
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

            # Look for the branch.
            next_node = None
            for subnode in branch_node:
                if subnode[0] == key:
                    next_node = subnode
                    break

            # If the branch doesn't exist, start it.
            if next_node == None:
                next_node = (key, [])
                branch_node.append(next_node)

            # Advance to the next_node's list.
            branch_node = next_node[1]

        # Can now record the object.
        branch_node.append((label, Object_View(label, edit_object)))
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
        Returns all tree List nodes at any level at or below
        the given node.

        * start_node
          - The node to begin at. Defaults to the top tree node.
          - Should be a List.
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
                unvisited_nodes += self.Expand_Node(node)

        return found_nodes


    def Expand_Node(self, node):
        '''
        Expands the children of the given node into a list.
        This may be sublists or object views.
        '''
        return [x[1] for x in node]
    

    def Get_Leaf_Nodes(self, start_node = None):
        '''
        Returns all tree Object_View nodes at any level at or below
        the given node.

        * start_node
          - The node to begin at. Defaults to the top tree node.
          - Should be a List.
          - This will be included in the return list.       
        '''
        ret_list = []
        # Loop over the branch nodes involved.
        for node in self.Get_Branch_Nodes(start_node):
            # If it is flat (just has leaves), record them.
            if self.Is_Flat(node):
                ret_list += self.Expand_Node(node)
        return ret_list


    def Sort_Branches(self, start_node = None):
        '''
        Sort all branch nodes at or below the given node, by label.
        This can be used to construct the tree in a lazy order,
        then post-sort it.
        '''
        # Work through the branches.
        for node in self.Get_Branch_Nodes(start_node):
            node.sort(key = lambda k: k[0])
            ## Sorting an ordered dict can be done nicely using its
            ## move_to_end method.
            #for key in sorted(node.keys()):
            #    node.move_to_end(key)
        return


    def Apply_Filtered_Labels(self, start_node = None):#, label_dict):
        '''
        Filters the object view item names for each branch of the
        tree at or below the given branch.
        
        * start_node
          - The node to begin at. Defaults to the top tree node.
          - Should be a List.
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
            for object_view in self.Expand_Node(node):

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
            for object_view in self.Expand_Node(node):
                object_view.skipped_item_names = item_names_not_used

        return


    def Is_Flat(self, node = None):
        '''
        Returns True if the given node has a flat object list.
        If no node given, operates on the top tree node.
        '''
        if node == None:
            node = self.tree
        # Note: the node is expected to have stuff in it.
        if not node:
            raise AssertionError('Empty branch found in tree')
        # Sample the first element, and check its type.
        # If it is an object, this should be flat.
        return isinstance(node[0][1], Object_View)


    def Convert_To_Table_Group(self, rebuild = False):
        '''
        Returns an Edit_Table_Group holding the tree contents.
        A table will be formed for each first or second tree subnode, or
        for the entire tree if it is a flat list.
        Table columns are not pruned, even if no object uses them.
        Caches the result, and returns it on prior calls.
        The returned table should not be edited.

        * rebuild
          - Bool, if True then the table group is always regenerated.
        '''
        # Return a cached version.
        if self.table_group != None and not rebuild:
            return self.table_group

        # Start a new table group.
        self.table_group = Edit_Table_Group(self.name)
        
        # Form a list of tuples, holding the objects to assign to
        # each subtable.
        # Elements are tuples of (label, object_dict), where the object
        # dict is keyed by object name and holds all objects for
        # a single table.
        label_object_groups = []

        def Find_Object_Groups(label, branch, depth):
            '''
            Recursive function that returns a list of (label,object_list)
            pairs, collecting from branches when depth hits 0, else
            recursing into branches when there is depth remaining.
            If an end branch is seen before depth=0 reached, it is
            packed into a group.
            '''
            ret_list = []
            if depth == 0 or self.Is_Flat(branch):
                ret_list.append((label, self.Get_Leaf_Nodes(branch)))
            else:
                for sublabel, subnode in branch:
                    # Reduce depth and expand the branch.
                    # Append the sublabel to the current label,
                    # so that the results are reasonably named.
                    ret_list += Find_Object_Groups(label + '/' + sublabel, 
                                                   subnode, depth -1)
            return ret_list

        # Try out a depth of 2.
        label_object_groups = Find_Object_Groups(self.name, self.tree, 2)

        # Error check: all objects should be accounted for.
        assert len(self.Get_Leaf_Nodes()) == sum(len(x[1]) for x in label_object_groups)
        
        # Make tables for each of these object groups.
        for label, object_group in label_object_groups:
            edit_table = Edit_Table(name = label)
            self.table_group.Add_Table(edit_table)
            for object in object_group:
                edit_table.Add_Object(object)

        return self.table_group


    def Add_Tree(self, other_tree):
        '''
        Adds another Edit_Tree_View to this Edit_Tree_View.
        The label will be the other's display name.
        '''
        assert other_tree.display_name
        self.tree.append((other_tree.display_name, other_tree.tree))
        return
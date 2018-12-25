
from collections import namedtuple, OrderedDict, defaultdict
import inspect
import json

from Framework import Load_File, File_System, Settings, Print


# Use a named tuple to track custom patches.
# Values are strings.
Custom_Patch = namedtuple(
    'Custom_Patch', 
    ['virtual_path', 'xpath', 'attribute', 'value'])


class Live_Editor_class:
    '''
    This will handle live editing of tables in the gui.
    All tables should be added to the global Live_Editor.
    TODO: save/restore custom patches using some special file,
    probably json, probably in the output extension folder.

    Attributes:
    * objects_dict
      - Dict, keyed by object name, holding every created Edit_Object,
        both those used in tables and others used as references.
    * table_group_dict
      - Dict holding Edit_Table_Group objects, keyed by their name.
    * table_group_builders
      - Dict, keyed by supported table_group name, holding the
        functions which will build the groups.
      - Used to autobuild table groups when a group is requested that
        isn't available.
      - Other modules should register their builder functions with
        the Live_Editor at their import time, so that the editor
        does not need to know about them when importing this module.
    * patches_dict
      - Dict holding patch values, loaded from a prior run or
        updated with current changes.
      - Key is a stringified tuple of (virtual_path, xpath, attribute),
        formed this way to make json save/load easier.
      - To be checked and applied whenever an Edit_Object is added,
        and updated before writing out to json.
    '''
    def __init__(self):
        self.objects_dict = {}
        self.table_group_dict = {}
        self.table_group_builders = {}
        self.patches_dict = {}
            
        
    def Reset(self):
        '''
        Resets the live editor.
        '''
        self.objects_dict = {}
        self.table_group_dict = {}


    def Add_Object(self, edit_object):
        '''
        Record a new Edit_Object.
        Error if the name is already taken; this is a generally
        unexpected situation, and should be handled specially
        if it comes up, for now.
        '''
        assert edit_object.name not in self.objects_dict
        self.objects_dict[edit_object.name] = edit_object
        # Check for patches to apply.
        # This will need to check each item, since they may be sourced
        # from different original files.
        for item in edit_object.Get_Items():
            # Skip if not an Edit_Item.
            if not isinstance(item, Edit_Item):
                continue

            if item.key in self.patches_dict:
                # A patch was found.
                value = self.patches_dict[item.key]
                # Can just overwrite the edited value directly.
                # This doesn't need to worry about deletions, like
                # the xml patcher will.
                item.Set_Edited_Value(value)
        return


    def Get_Object(self, name):
        '''
        Returns an Edit_Object of the given name, or None if not found.
        '''
        return self.objects_dict.get(name, None)


    def Record_Table_Group_Builder(self, name, build_function):
        '''
        Records the build function for a Table_Group of the given name.
        '''
        self.table_group_builders[name] = build_function


    def Add_Table_Group(self, edit_table_group):
        '''
        Record a new Edit_Table.
        '''
        self.table_group_dict[edit_table_group.name] = edit_table_group
        

    def Get_Table_Group(self, name):
        '''
        Returns an Table_Group of the given name, building it if needed
        and a builder is available, or returns None otherwise.
        '''
        group = self.table_group_dict.get(name, None)
        if group == None and self.table_group_builders.get(name, None) != None:
            # Call the builder function and store the group.
            group = self.table_group_builders[name]()
            self.Add_Table_Group(group)
        return group


    def Update_Patches(self):
        '''
        Updates the loaded patches, adding/updating any new ones from
        modified items, removing old patches when their item is no longer
        modified.
        '''
        # Loop over objects and their items.
        for edit_object in self.objects_dict.values():
            for item in edit_object.Get_Items():
                # Skip non-edit items.
                if not isinstance(item, Edit_Item):
                    continue

                # Check for modified Edit_Item objects.
                if item.Is_Modified():
                    self.patches_dict[item.key] = item.Get_Edited_Value()
                # When not modified, delete any old patch for this item.
                elif item.key in self.patches_dict:
                    self.patches_dict.pop(item.key)
        return


    def Save_Patches(self, file_name = 'edited_attributes.json'):
        '''
        Save the loaded patches to a json file.
        By default, saves to the output extension folder.
        This will preserve existing patches loaded earlier.
        '''
        # Start by bringing loaded patches up to date.
        self.Update_Patches()

        # Give on layer of nesting to the json, in case it will
        # ever have other fields added.
        patch_dict = {}
        json_dict = {'patches' : patch_dict}
        # Record patches in sorted order.
        for key, value in sorted(self.patches_dict.items()):
            patch_dict[key] = value
        with open(Settings.Get_Output_Folder() / file_name, 'w') as file:
            json.dump(json_dict, file, indent = 2)
        return


    def Load_Patches(self, file_name = 'edited_attributes.json'):
        '''
        Load a prior saved json file holding simple patches.
        On json load error, this will crash gracelessly to avoid
        continuing and accidentally overwriting a file that a user
        may have hand edited.
        This may be called multiple times to load patches from
        multiple files, if needed.

        Note: this load may happen before the patched objects are
        set up; actual patch application will be checked when
        objects are added.
        '''
        path = Settings.Get_Output_Folder() / file_name
        if not path.exists():
            return
        Print('Loading custom edits from "{}"'.format(path))

        with open(path, 'r') as file:
            json_dict = json.load(file)
        # TODO: consider having a backup way to identify patches
        # using item name, in case the xpath gets changed between
        # versions if it ever gets a multi-match error.
        for key, value in json_dict['patches'].items():
            self.patches_dict[key] = value
        return
    

# Global version.
Live_Editor = Live_Editor_class()
    

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

            # Sort the objects by name and record them.
            # TODO: better sorting style; probably move to support function
            #  that can be easily customized.
            for name, object in sorted(self.objects_dict.items()):
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


class Edit_Object:
    '''
    An object represented by a collection of Edit_Items and Display_Items,
    or references to other attached Edit_Objects.
    Objects of different types should subclass this to fill in
    their own initialization code.
    This could source from one xml file, a piece of an xml file, or
    multiple xml files, depending on what is represented.

    Attributes:
    * name
      - String, name for this object, generally taken from game
        files in some way ('id' or 'name' attribute of some node).
    * items_dict
      - Dict, keyed by arbitrary item name (eg. 'dps'), holding
        Edit_Item and Display_Item objects belonging to this object.
    * refs_dict
      - OrderedDict, keyed by object name, holding other objects closely
        related to this object, whose items will be displayed along
        with this object's items.
      - These will be searched for item_names in the order they were added.
      - TODO: think about the best way to update this if an Edit_Item
        that sets the reference is changed.
    '''
    def __init__(self, name):
        self.name = name
        self.items_dict = {}
        self.refs_dict = OrderedDict()


    def Add_Item(self, item):
        '''
        Add an item to this object.
        '''
        self.items_dict[item.name] = item


    def Add_Reference(self, edit_object):
        '''
        Adds a reference to another Edit_Object. Triggers an error
        if this object is already a reference of that object;
        circular refs are not supported at this time.
        '''
        assert self.name not in edit_object.refs_dict
        self.refs_dict[edit_object.name] = edit_object


    def Get_Items(self):
        '''
        Returns a list of items belonging to this object.
        '''
        return list(self.items_dict.values())


    def Get_All_Items(self):
        '''
        Returns a list of all items in this object or any
        of its references.
        '''
        ret_list = list(self.items_dict.values())
        for ref_object in self.refs_dict.values():
            ret_list += ref_object.Get_All_Items()
        return ret_list


    def Get_Item(self, item_name):
        '''
        Look up and return the item matching the given name.
        Item may be pulled from this object or one of its references.
        If the item_name isn't found, returns None.
        '''
        # Start with local lookup.
        if item_name in self.items_dict:
            return self.items_dict[item_name]
        # Check references.
        for ref_object in self.refs_dict.values():
            # If it found an item, return it.
            item = ref_object.Get_Item(item_name)
            if item != None:
                return item
        # Couldn't find a match.
        return None

    
    def Make_Edit_Items(
            self,
            game_file,
            control_list
        ):
        '''
        Creates and records a list of Edit_Items constructed from the given
        xml game_file with the given control_list.
        Each entry in the control_list is a tuple of:
        (item name, xpath, xml_attribute, display name, kwargs)
        Entries are skipped if the xpath is not found, though they are
        still created if the attribute is not found.
        '''
        virtual_path = game_file.virtual_path
        xml_root = game_file.Get_Root_Readonly()
    
        for entry in control_list:
            name, xpath, xml_attribute = entry[0:3]
            # Kwargs are optional.
            kwargs = {} if len(entry) < 4 else entry[3]


            # Skip if node not found; there is currently no support
            # for adding a node like there is for creating an attribute.
            node = xml_root.find(xpath)
            if node == None:
                continue

            # Create the item.
            self.Add_Item( Edit_Item(
                name = name,
                virtual_path = virtual_path,
                xpath = xpath,
                attribute = xml_attribute,
                **kwargs
                ))
        return


    def Make_Display_Items(
            self,
            control_list
        ):
        '''
        Creates and records a list of Display_Items constructed from the
        given Edit_Object and control_list.
        Each entry in the control_list is a tuple of:
        (item name, display_function, display name, kwargs)
        Dependencies should be given as a list of item names, which will match
        to items already recorded in this Edit_Object or one of its
        references.
        Note: this may end up being unused in favor of custom class objects
        that fill in their methods.
        '''
        for entry in control_list:
            name, display_function = entry[0:2]
            # Kwargs are optional.
            kwargs = {} if len(entry) < 3 else entry[2]

            # Look up the dependency items.
            # Parse dependencies from the function arg names.
            # Note: these could come from other Edit_Objects, found through
            # a reference.
            dependencies = []
            for dep_name in inspect.signature(display_function).parameters:
                dep_item = self.Get_Item(dep_name)
                #-Removed; allow None dependencies for cases where the
                # display will simply not be computable or needs to
                # use an alt calc or default.
                #if dep_item == None:
                #    raise AssertionError(('Failed to look up dependency item'
                #    ' named "{}" in object "{}".').format(dep_name, self.name))
                dependencies.append(dep_item)

            # Create the item.
            self.Add_Item( Display_Item(
                name = name,
                dependencies = dependencies,
                display_function = display_function,
                **kwargs
                ))
        return


class _Base_Item:
    '''
    Base class for Edit_Item and Display_Item objects.

    Attributes:
    * name
      - String, internal name of the item.
    * display_name
      - String, name to be used during display in the gui or a file.
      - Defaults to an empty string for non-displayed items.
    * read_only
      - Bool, if True then edits of this item should be disallowed.
      - May be used for object references or similar, until those
        have support added.
      - Defaults True on Display_Items, False on Edit_Items.
    * widget
      - Qt Widget with a setText method that is attached to
        the edited version of this item.
    '''
    def __init__(
            self, 
            name, 
            display_name = '',
            read_only = False,
        ):
        self.name = name
        self.display_name = display_name
        self.read_only = read_only
        self.widget = None

    def Set_Widget(self, widget):
        '''
        Attach this item to the widget, or detach if None.
        '''
        self.widget = widget


class Display_Item(_Base_Item):
    '''
    Container for a computed display value, that will not be editable.
    This should be updated when associated edit items or display items
    are changed.
    
    Attributes:
    * version_value_dict
      - Dict of values, keyed by version.
      - Versions include: ['vanilla','patched','current','edited']
      - These are computed and buffered here.
      - Use Reset() to clear a value if its dependencies have changed.
    * display_function
      - Attached function which will compute a display value.
      - Takes a list of string value inputs: (*dependency_values).
      - Can name its dependencies whatever it likes, but their order
        will need to match the dependencies list here.
    * dependencies
      - List of Edit_Item and Display_Item objects this item requires
        for its computations; will be fed to the function when called.
      - When these are reset or edited, they should call Reset on this item.
      - Some entries may be None for when a dependency is not available.
    * dependents
      - List of Display_Item objects that depend on this item.
      - These should be filled in by the other items when they
        are set up with dependencies.
      - When this item is reset, dependents will be reset
        as well automatically
      - Note: avoid circular dependencies, as they might cause lockup.
    '''
    '''
    TODO:
    * edit_function
      - Attached function which will translate edits to this display
        item into edits of the source dependency items.
      - Takes a list of _Base_Item inputs: (*dependencies).
      - Allows a displayed term, like 'dps', be back-converted into
        edits of the source items, like 'damage'.
    '''
    def __init__(
            self, 
            display_function, 
            dependencies,
            read_only = True, # Customize default.
            **kwargs
        ):
        super().__init__(read_only = read_only, **kwargs)
        self.version_value_dict = {}
        self.display_function = display_function
        self.dependencies = dependencies
        # Blank list of dependents initially.
        self.dependents = []
        # Add self as a dependent to all dependencies.
        for dep in dependencies:
            if dep != None:
                dep.dependents.append(self)
        return


    def Reset(self, version):
        '''
        Resets the given version of the value to None, triggering
        a recompute later. Also resets dependents.
        If a widget is attached, the 'edited' version of the value
        will be recomputed and sent to the widget.
        '''
        self.version_value_dict[version] = None
        if self.widget != None and version == 'edited':
            # Update the widget text using setText.
            value = self.Get_Value(version)
            if value == None:
                value = ''
            self.widget.setText(value)
        for dep in self.dependents:
            dep.Reset(version)
        

    def Get_Value(self, version):
        '''
        Return the value from the given version, computing it if
        needed.
        '''
        # On first call or after a reset, need to recompute the value.
        if self.version_value_dict.get(version) == None:
            # Gather values from dependencies, triggering their updates
            # as needed, for the selected version.
            # Missing dependencies will stay as None.
            # TODO: maybe just pass the dependency items directly.
            values = [x.Get_Value(version) if x != None else None
                        for x in self.dependencies]
            # Pass the values to the display_function.
            self.version_value_dict[version] = self.display_function(*values)
        return self.version_value_dict[version]


class Edit_Item(_Base_Item):
    '''
    Container for a single editable item, eg. one field in the xml.
    Initializor takes paths to the field, and fills in values automatically.

    Attributes:
    * virtual_path
      - Path for the game file being edited.
    * xpath
      - Xpath to the node being edited.
      - Note: the attribute does not have to exist in the node prior
        to editing, for cases where an attribute will be added.
    * attribute
      - Node attribute being edited.
    * key
      - String made from a tuple of (virtual_path, xpath, attribute), used as
        a way to identify this item uniquely but generically, for saving
        patches and elsewhere applyling them to xml.
    * version_value_dict
      - Dict of values, keyed by version.
      - Versions include: ['vanilla','patched','current','edited']
      - Only 'edited' will be editable; the others are read-only and
        meant for display.
      - The 'patched' copy is after other (non-customizer) extensions have
        been applied.
      - The 'current' copy is after a customizer script has run, possibly
        performing additional edits after the live changes.
        TODO: think about how/when to gather/update this.
    * dependents
      - List of Display_Item objects that depend on this item.
      - When this item is edited, dependents will be reset automatically.
      - These should be filled in by the other items when they
        are set up with dependencies.
    '''
    def __init__(
            self,
            virtual_path,
            xpath,
            attribute,
            read_only = False, # Customize default.
            **kwargs
        ):
        super().__init__(read_only = read_only, **kwargs)
        self.virtual_path       = virtual_path
        self.xpath              = xpath
        self.attribute          = attribute
        self.key                = str((virtual_path, xpath, attribute))
        self.version_values     = {}
        self.dependents         = []

        # Grab the game file with the source info.
        game_file = Load_File(virtual_path)

        # Loop over versions of the xml.
        for version in ['vanilla','patched','current']:
            xml_root = game_file.Get_Root_Readonly(version)

            # Look up the xpath node; should be just one.
            nodes = xml_root.findall(xpath)
            if len(nodes) != 1:
                raise AssertionError('Error: Found {} nodes for file "{}", xpath "{}".'
                                     .format(len(nodes), virtual_path, xpath))

            # Pull out the field info.
            # Note: may be empty, in which case use an empty string.
            self.version_values[version] = nodes[0].get(attribute, default = '')

        # The edited value will initialize to the patched version.
        # Note: originally this started as an empty string, but that
        # got messy with display items that couldn't do calculations
        # off of blank input. Also, that style wouldn't pick up on
        # deleted attributes very well.
        self.version_values['edited'] = self.version_values['patched']
        return


    def Get_Value(self, version):
        '''
        Return the value from the given version.
        '''
        return self.version_values[version]
    

    def Get_Edited_Value(self):
        '''
        Returns the edited value.
        '''
        return self.version_values['edited']


    def Set_Value(self, version, value):
        '''
        Sets the value for the given version, and triggers resets on
        dependents. Normally expected to be used for edited values only,
        so consider using Set_Edited_Value.
        '''
        self.version_values[version] = value
        for dep in self.dependents:
            dep.Reset(version)
        return


    def Set_Edited_Value(self, value):
        '''
        Sets the edited value, and resets dependents.
        '''
        self.Set_Value('edited', value)

        
    def Is_Modified(self):
        '''
        Returns True if this item appears to be modified, else False
        '''
        # Check if the edit differs from the patched value.
        if self.version_values['edited'] != self.version_values['patched']:
            return True
        return False


    def Get_Patch(self):
        '''
        Returns a Simple_Patch object capturing the edited value.
        If not modified, returns None.
        '''
        if not self.Is_Modified():
            return None
        # Note: edited values should never be None; at least they
        # should be an empty string.
        assert self.version_values['edited'] != None
        
        return Custom_Patch(
            virtual_path = self.virtual_path, 
            xpath        = self.xpath,
            attribute    = self.attribute,
            value        = self.version_values['edited'],
            )

    
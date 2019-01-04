

import inspect
from collections import OrderedDict, defaultdict
from collections import namedtuple

from .Edit_Items import Edit_Item, Display_Item, Placeholder_Item
from .Edit_Items import version_names

# Macro tuples for aiding in construction of items.
# TODO: maybe convert to classes, to make it easier to copy base
# macros and edit fields programatically.
Edit_Item_Macro = namedtuple('Edit_Item_Macro', 
    ['name', 'xpath', 'attribute', 
     'display_name', 'description', 
     'read_only', 'is_reference', 'hidden' ], 
     # Note: defaults apply to the last so many terms.
     defaults = [False, False, False])

Display_Item_Macro = namedtuple('Display_Item_Macro', 
    ['name', 'display_function', 
     'display_name', 'description', 
     'read_only', 'hidden' ], 
     defaults = ['','', True, False])

# To support xml items that appear in lists of duplicates,
# grouping support will be available.
# This will work as part of a list of macros, in the style:
# [
# Item_Group_Macro(stuff, ...)
# Edit_Item_Macros(...)
# ...
# Item_Group_Macro(/stuff, ...)
# ]
# This forms a mini language, for which the processing function will
# note the opening of a group, record its name and xpath prefixes,
# and recursively deal with the innards (prefixing them as needed)
# based on matching group xml nodes found.
# The macro group is closed with the closing tag, '/stuff'.
# Macro groups may be nested, hence the recursive implementation.
Item_Group_Macro = namedtuple('Item_Group_Macro',
    ['name', 'xpath', 'tag', 'display_name'],
    # Last 3 terms are optional, not used in group closing tags.
    defaults = ['','',''])


class Edit_Object:
    '''
    An object represented by a collection of Edit_Items and Display_Items,
    or references to other attached Edit_Objects.
    Objects of different types should subclass this to fill in
    their own initialization code.
    This could source from one xml file, a piece of an xml file, or
    multiple xml files, depending on what is represented.

    Attributes:
    * parent
      - Live_Editor holding this object.
    * name
      - String, name for this object, generally taken from game
        files in some way ('id' or 'name' attribute of some node).
    * category
      - String, category of this object as used in the Live_Editor.
    * items_dict
      - Dict, keyed by arbitrary item name (eg. 'dps'), holding
        Edit_Item and Display_Item objects belonging to this object.
    * item_version_object_refs
      - Dict, keyed by item name, then keyed by version, holding
        the Edit_Object the item references (or None if not found).
    * category_item_name_list
      - List of strings, item names in preferred display order for
        this category of objects.
      - This should always match for objects of the same category, 
        even if one or both of them do not having matching items.
      - Used to aid in display of multiple parallel objects.
    '''
    def __init__(self, name, category = None, parent = None):
        self.parent = parent
        self.name = name
        self.category = category
        self.category_item_name_list = None
        self.items_dict = {}
        self.item_version_object_refs = defaultdict(dict)
        return


    def Delayed_Init(self):
        '''
        Once all items are filled in, set initial dependencies
        and references.
        '''
        for version in version_names:
            self.Update_Item_Dependencies(version)
        # Do the initial reference setup for items.
        for item in self.Get_Items():
            item.Init_References()
        return


    def Add_Item(self, item):
        '''
        Add an item to this object.
        '''
        self.items_dict[item.name] = item
        return


    def Update_Reference(self, item_name, version, ref_name):
        '''
        Update the reference to another edit object, overwriting
        any prior ref for the same item.
        '''
        # Look up the object in the Live_Editor; it may be None
        # if there is a problem (eg. the user typed in an invalid name).
        ref_object = self.parent.Get_Object(ref_name)
        # Record it. Note: if not found, this clears the prior ref.
        self.item_version_object_refs[item_name][version] = ref_object
        # Update dependencies of display items.
        self.Update_Item_Dependencies(version)
        return


    def Gen_All_References(self, version):
        '''
        Generates all referenced Edit_Objects, recursively.
        Skips empty entries.
        '''
        for subdict in self.item_version_object_refs.values():
            ref_object = subdict[version]
            if ref_object != None:
                yield ref_object
                yield from ref_object.Gen_All_References[version]
        return


    def Update_Item_Dependencies(self, version):
        '''
        Updates dependencies for owned display items, primarily for use
        at startup and when references change.
        '''
        # First, delink all dependencies, to prune dependent lists.
        # Eg. don't want an old dependency to think a local display
        # item is still dependent on it.
        for item in self.Get_Items():
            # Only looking to update display items.
            if not isinstance(item, Display_Item):
                continue

            # Loop over its existing dependencies, if any.
            for dep in item.version_dependencies[version]:
                if dep != None:
                    # Delink from that item.
                    dep.version_dependents[version].remove(item)

            # Now clear the list.
            item.version_dependencies[version].clear()


        # Now do a pass to fill in deps, both directions.
        for item in self.Get_Items():
            # Only looking to update display items.
            if not isinstance(item, Display_Item):
                continue

            # Loop over the dep item names.
            for dep_name in item.dependency_names:

                # Look up the item; this may be from a reference.
                dep_item = self.Get_Item(dep_name, version)

                # Record it, even if None.
                item.version_dependencies[version].append(dep_item)

                # If not none, add the dependent link.
                if dep_item != None:
                    dep_item.version_dependents[version].append(item)

        return


    def Get_Items(self, allow_placeholders = False):
        '''
        Returns a list of items belonging to this object.
        
        * allow_placeholders
          - Bool, if True then Placeholder_Items may be returned.
        '''
        return [x for x in self.items_dict.values()
                # Prune out placeholders, conditionally.
                if allow_placeholders or not isinstance(x, Placeholder_Item)]


    def Get_All_Items(self, allow_placeholders = False):
        '''
        Returns a list of all items in this object or any of its references,
        across all versions.
        
        * allow_placeholders
          - Bool, if True then Placeholder_Items may be returned.
        '''
        ret_list = self.Get_Items()
        for item_name, subdict in self.item_version_object_refs.items():
            for ref_object in subdict.values():
                ret_list += ref_object.Get_All_Items()
        return ret_list


    def Get_Item(self, item_name, version = 'current', allow_placeholders = False):
        '''
        Look up and return the item matching the given name.
        Item may be pulled from this object or one of its references.
        If the item_name isn't found, returns None.
        If an item is found but has a blank value
        
        * item_name
          - String, the item's name.
        * version
          - When the item is not found locally, this is the version of
            references to use in ref lookups.
        * allow_placeholders
          - Bool, if True then a Placeholder_Item object may be returned.
        '''
        # Start with local lookup.
        if item_name in self.items_dict:
            item = self.items_dict[item_name]

            # Skip if a disallowed placeholder.
            if not allow_placeholders and isinstance(item, Placeholder_Item):
                pass
            # Otherwise, can return it.
            else:
                return self.items_dict[item_name]

        # Check references.
        for subdict in self.item_version_object_refs.values():
            ref_object = subdict[version]
            # Skip empty refs.
            if ref_object == None:
                continue
            # If it found an item, return it.
            item = ref_object.Get_Item(item_name, version)
            if item != None:
                return item

        # Couldn't find a match.
        return None


    def Get_Item_Value(self, item_name, version = 'current', default = ''):
        '''
        Finds an item of the given name for the given version, and
        returns its version value. If the item is not found or has
        an empty string value,this  returns an empty string or the
        given default.
        
        * item_name
          - String, the item's name.
        * version
          - Version of the item (used in reference lookup) and value.
        * default
          - Optional, return value if the item is missing.
        '''
        item = self.Get_Item(item_name, version)
        if not item:
            return default
        value = item.Get_Value(version)
        if not value:
            return default
        return value

    
    def Make_Items(
            self,
            game_file,
            macro_list,
            xpath_replacements = None
        ):
        '''
        Creates and records a list of Edit_Items and Display_Items
        constructed from the given xml game_file with the given macro list.

        * game_file
          - XML_File used to check xpaths.
          - Macros are skipped if the xpath is not found, though they are
            still created if the attribute is not found.
        * macro_list
          - List of Edit_Item_Macro and Display_Item_Macro objects,
            or pairs of Item_Group_Macro objects that will repeat over
            the intermediate other macros.
        * xpath_replacements
          - Dict holding replacements for macro xpath placeholders.
          - May be full or partial replacements; care should be
            taken to ensure the replaced terms are unique.
          - Added to deal with weapon component connection tags, which
            have varying xml node tags, so that they can all use the
            same macro.
          - Also useful for files which hold multiple objects, to
            be able to insert a per-object xpath prefix.
        '''
        # Bounce to the recursive function, unpacking the initial
        # root node.
        self._Make_Items_Recursive(
            game_file = game_file,
            xml_node = game_file.Get_Root_Readonly(),
            # Copy the list, so the function can pop items off it privately.
            macro_list = list(macro_list),
            xpath_replacements = xpath_replacements )
        return

    
    def _Make_Items_Recursive(
            self,
            game_file,
            xml_node,
            macro_list,
            name_prefix         = '',
            xpath_prefix        = '',
            display_name_prefix = '',
            xpath_replacements  = None
        ):
        '''
        Recursive item builder. This will call itself when dealing
        with item groups.

        * game_file
          - Game file macros are applied to.
        * xml_node
          - Base xml node to process macros xpaths against.
        * macro_list
          - Macros to process at this level.
          - This should be a unique list that can be modified.
        * xpath_prefix
          - String, xpath prefix to apply to any nested item xpaths.
        * name_prefix
          - String, prefix to apply to any item names.
        * display_name_prefix
          - String, prefix to apply to any item display names.
        * xpath_replacements
          - Dict of xpath term replacements.
        '''
        # To deal with macro groups, this will pop off macros as they are
        # consumed, where groups pop off all macros in their group
        # at once.
        while macro_list:
            macro = macro_list.pop(0)
            
            # Replace the xpath if needed.
            if hasattr(macro, 'xpath'):
                xpath = macro.xpath
                if xpath_replacements != None:
                    # Check for any partial replacement opportunities.
                    for old, new in xpath_replacements.items():
                        if old in xpath:
                            xpath = xpath.replace(old, new)
                
                # Prefix the xpath for recording, though not
                # for lookups at this node.
                # In this case, a node lookup will begin like './stuff'
                # or just '.', where a prefix is meant to replace the '.'.
                if xpath_prefix:
                    assert xpath.startswith('.')
                    abs_xpath = xpath.replace('.',xpath_prefix,1)
                else:
                    abs_xpath = xpath

            # Extend the name and display name.
            name         = name_prefix + macro.name
            display_name = display_name_prefix + macro.display_name


            # Deal with the macros based on type.
            if isinstance(macro, Item_Group_Macro):

                # Collect the following macros up until the group closer,
                # which is the same name prefixed with '/'.
                # This loop pops one macro at a time, recording it if
                # is not the closer, stopping the loop otherwise, such
                # that the closer is consumed from the macro_list.
                nested_macros = []
                next_macro = macro_list.pop(0)
                while next_macro.name != '/' + macro.name:
                    nested_macros.append(next_macro)
                    next_macro = macro_list.pop(0)
                    
                # Look up the xml node being expanded.
                group_node = xml_node.find(xpath)
                # If it wasn't found, skip this macro group entirely.
                # Note: placeholders aren't added for groups, for now,
                # unlike raw edit_items.
                if group_node == None:
                    continue

                # Find the xml children with the tag being grouped.
                child_nodes = group_node.findall(macro.tag)

                for index, child_node in enumerate(child_nodes):
                    # Pick an extention for item names, to uniquify
                    # them based on index.
                    extension = '_{}_'.format(index)

                    # Tweak the xpath; this will be to the group node,
                    # then to this child, with nexted macros being
                    # relative to the child.
                    # Note: xpath indices are 1-based, so offset by 1.
                    child_xpath_prefix = '{}/{}[{}]'.format(abs_xpath, macro.tag, index+1)

                    self._Make_Items_Recursive(
                        game_file           = game_file,
                        xml_node            = child_node,
                        # Give a copy of the macros to each child, for
                        # them to consume internally.
                        macro_list          = list(nested_macros),
                        xpath_prefix        = child_xpath_prefix,
                        name_prefix         = name + extension,
                        display_name_prefix = display_name + extension,
                        )
            
            elif isinstance(macro, Edit_Item_Macro):
                
                # Use a placeholder if the node is not found; there is
                #  currently no support for adding a node like there is for
                #  creating an attribute.
                # TODO: consider how to deal with this if the xpath is
                #  valid for only one version of the filep; perhaps an
                #  Edit_Item should always be created, and it will just
                #  deal with missing nodes internally.
                node = xml_node.find(xpath)
                if node == None:
                    self.Add_Item( Placeholder_Item(
                        parent       = self,
                        name         = name,
                        display_name = display_name,
                        description  = macro.description,
                        hidden       = macro.hidden,
                        ))
                else:
                    # Create the item.
                    self.Add_Item( Edit_Item(
                        parent       = self,
                        game_file    = game_file,
                        virtual_path = game_file.virtual_path,
                        name         = name,
                        display_name = display_name,
                        description  = macro.description,
                        xpath        = abs_xpath,
                        attribute    = macro.attribute,
                        read_only    = macro.read_only,
                        is_reference = macro.is_reference,
                        hidden       = macro.hidden,
                        ))

            else:                
                # Look up the dependency names.
                # Parse dependencies from the function arg names.
                # Note: these could come from other Edit_Objects, found
                #  through a reference.
                dependency_names = [
                    x for x in inspect.signature(macro.display_function).parameters]
                                
                # Create the item.
                self.Add_Item( Display_Item(
                    parent           = self,
                    name             = name,
                    display_name     = display_name,
                    description      = macro.description,
                    dependency_names = dependency_names,
                    display_function = macro.display_function,
                    read_only        = macro.read_only,
                    hidden           = macro.hidden,
                    ))

        return


    def Get_Display_Version_Items_Dict(
            self, 
            skipped_item_names = None,
            include_refs = True,
            version = None,
            include_ref_separators = True,
        ):
        '''
        Returns a dict keyed by version name and holding lists of
        items, taken from here or first level references.
        Lists may include Placeholder_Items or None entries, though
        the same spot in each list will always have at least one item.
        
        If a row has Placeholder_Items with is_reference==True, they
        were added to put spacing before a reference section, with
        a label indicating which field they are expanding on.

        Lists will be in sync, such that every item from the same
        position in the lists will have the same item name and
        display label (or be None).

        * skipped_item_names
          - List of strings, names of items to skip.
        * include_refs
          - Bool, if True then first level references are included,
            else they are skipped.
        * version
          - Optional string, the version to include in the response.
          - When not given, all versions are included.
        * include_ref_separators
          - If the extra row of placeholders should be included before a
            reference section.
        '''
        version_items = defaultdict(list)

        # Make item names a list for easy usage.
        if skipped_item_names == None:
            skipped_item_names = []

        # Pick the versions to be included.
        if version == None:
            version_list = version_names
        else:
            version_list = [version]
        
        # Start with the top level items, which are always the same
        # across versions. Include placeholders for now.
        for version in version_list:
            for item in self.Get_Items(allow_placeholders = True):
                # Skip if a skipped name.
                if item.name in skipped_item_names:
                    continue
                # Skip if hidden.
                if item.hidden:
                    continue
                version_items[version].append(item)

        # Loop over references, by item name, alphabetical.
        # TODO: consider inserting these where their original field was placed.
        for item_name, subdict in sorted(self.item_version_object_refs.items()):

            # TODO: pick a nice display name label.
            padding = Placeholder_Item(display_name = '', is_separator = True)

            # Different versions may have refs to different objects, though
            # they should all be of the same type and with the same item
            # names.  Eg. switching from bullet to missile still will pull
            # from the generic bullet names.
            for version in version_list:
                ref_object = subdict[version]
                # Skip missing refs.
                if ref_object == None:
                    continue

                # Add the padding item.
                version_items[version].append(padding)
                
                # Check each of its items.
                for item in ref_object.Get_Items(allow_placeholders = True):
                    # Skip some names.
                    if item.name in skipped_item_names:
                        continue
                    # Skip if hidden.
                    if item.hidden:
                        continue
                    version_items[version].append(item)
                        
            # Since some versions may have had missing refs, the lists
            # could be out of sync. Pad with Nones to sync them.
            list_length = max(len(x) for x in version_items.values())
            for version in version_list:
                this_list = version_items[version]
                while len(this_list) < list_length:
                    this_list.append(None)


        # Do some verification.
        # All labels should be in sync, all indexes should have a non-None
        # item.
        for item_row in zip(*version_items.values()):
            assert any(x != None for x in item_row)
            # Name check is a little trickier.
            name = None
            for item in item_row:
                if item == None:
                    continue
                # Record the first name seen.
                if name == None:
                    name = item.name
                # Else verify.
                else:
                    assert name == item.name

        return version_items
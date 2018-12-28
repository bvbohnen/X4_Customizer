

import inspect
from collections import OrderedDict, defaultdict
from .Edit_Items import Edit_Item, Display_Item, Placeholder_Item
from .Edit_Items import version_names

from collections import namedtuple
# Macro tuples for aiding in construction of items.
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
            # To setup refs, just stride over items and make sure they have
            # pulled all of their values.
            for item in self.Get_Items():
                item.Get_Value(version)
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
        # Record it.
        self.item_version_object_refs[item_name][version] = ref_object
        # Update dependencies of display items.
        self.Update_Item_Dependencies(version)
        return


    def Gen_All_References(self, version):
        '''
        Generates all referenced Edit_Objects, recursively.
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
            # If it found an item, return it.
            item = ref_object.Get_Item(item_name, version)
            if item != None:
                return item

        # Couldn't find a match.
        return None

    
    def Make_Items(
            self,
            game_file,
            macro_list,
            xpath_replacements = None
        ):
        '''
        Creates and records a list of Edit_Items and Display_Items
        constructed from the given xml game_file with the given macro list.

        TODO: automatically add references.
        * game_file
          - XML_File used to check xpaths.
          - Macros are skipped if the xpath is not found, though they are
            still created if the attribute is not found.
        * macro_list
          - List of Edit_Item_Macro and Display_Item_Macro objects.
        * xpath_replacements
          - Dict holding replacements for macro xpath placeholders.
          - Added to deal with weapon component connection tags, which
            have varying xml node tags, so that they can all use the
            same macro.
        '''
        virtual_path = game_file.virtual_path
        xml_root = game_file.Get_Root_Readonly()
    
        for macro in macro_list:
            
            if isinstance(macro, Edit_Item_Macro):
                
                # Replace the xpath if needed.
                xpath = macro.xpath
                if xpath_replacements != None and xpath in xpath_replacements:
                    xpath = xpath_replacements[xpath]
                
                # Use a placeholder if the node is not found; there is
                #  currently no support for adding a node like there is for
                #  creating an attribute.
                node = xml_root.find(xpath)
                if node == None:
                    self.Add_Item( Placeholder_Item(
                        parent       = self,
                        name         = macro.name,
                        display_name = macro.display_name,
                        description  = macro.description,
                        hidden       = macro.hidden,
                        ))
                else:
                    # Create the item.
                    self.Add_Item( Edit_Item(
                        parent       = self,
                        virtual_path = virtual_path,
                        name         = macro.name,
                        display_name = macro.display_name,
                        description  = macro.description,
                        xpath        = xpath,
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
                    name             = macro.name,
                    display_name     = macro.display_name,
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
            include_refs = True
        ):
        '''
        Returns a dict keyed by version name and holding lists of
        items, taken from here or first level references.
        Lists may include Placeholder_Items or None entries, though
        the same spot in each list will always have at least one item.

        Lists will be in sync, such that every item from the same
        position in the lists will have the same item name and
        display label (or be None).

        * skipped_item_names
          - List of strings, names of items to skip.
        * include_refs
          - Bool, if True then first level references are included,
            else they are skipped.
        '''
        version_items = defaultdict(list)
        # Make this a list for easy usage.
        if skipped_item_names == None:
            skipped_item_names = []
        
        # Start with the top level items, which are always the same
        # across versions. Include placeholders for now.
        for version in version_names:
            for item in self.Get_Items(allow_placeholders = True):
                # Skip if a skipped name.
                if item.name in skipped_item_names:
                    continue
                # Skip if hidden.
                if item.hidden:
                    continue
                version_items[version].append(item)

        # Loop over references, by item name.
        for item_name, subdict in self.item_version_object_refs.items():
            # Different versions may have refs to different objects,
            # though they should all be of the same type and with
            # the same item names.  Eg. switching from bullet to
            # missile still will pull from the generic bullet
            # names.
            for version in version_names:
                ref_object = subdict[version]
                # Skip missing refs.
                if ref_object == None:
                    continue
                
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
            for version in version_names:
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


import inspect
from collections import OrderedDict
from .Edit_Items import Edit_Item, Display_Item

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

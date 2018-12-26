
from Framework import Load_File

class _Base_Item:
    '''
    Base class for Edit_Item and Display_Item objects, representing
    an attribute of an xml node in some file, or else a computation
    for display.

    Attributes:
    * name
      - String, internal name of the item.
    * display_name
      - String, name to be used during display in the gui or a file.
      - Defaults to an empty string for non-displayed items.
    * version_value_dict
      - Dict of values, keyed by version.
      - Versions include: ['vanilla','patched','current','edited']
      - These are computed and buffered here.
      - Only 'edited' will be editable; the others are read-only and
        meant for display.
      - The 'patched' copy is after other (non-customizer) extensions have
        been applied.
      - The 'current' copy is after a customizer script has run, possibly
        performing additional edits after the live changes.
      - Use Reset_Value() to clear a value if its dependencies have changed.
    * read_only
      - Bool, if True then edits of this item should be disallowed.
      - May be used for object references or similar, until those
        have support added.
      - Defaults True on Display_Items, False on Edit_Items.
    * widget
      - Qt Widget with a setText method that is attached to
        the edited version of this item.
    * dependents
      - List of Display_Item objects that depend on this item.
      - When this item is edited or reset, dependents will be
        reset automatically.
      - These should be filled in by the other items when they
        are set up with dependencies.
      - Note: avoid circular dependencies, as they might cause lockup.
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
        self.version_value_dict = {}
        # Blank list of dependents initially.
        self.dependents = []

    def Set_Widget(self, widget):
        '''
        Attach this item to the widget, or detach if None.
        '''
        self.widget = widget
        

    def Reset_Value(self, version):
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
            dep.Reset_Value(version)
        return
        

class Display_Item(_Base_Item):
    '''
    Container for a computed display value, that will not be editable.
    This should be updated when associated edit items or display items
    are changed.
    
    Attributes:
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
        self.display_function = display_function
        self.dependencies = dependencies
        # Add self as a dependent to all dependencies.
        for dep in dependencies:
            if dep != None:
                dep.dependents.append(self)
        return


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
            # If this has trouble (eg. if bad text was fed in, such as
            #  non-float text when expecting a float), catch that case
            #  and swap the value to an 'error'.
            try:
                value = self.display_function(*values)
            except Exception:
                value = 'error'
            self.version_value_dict[version] = value
        return self.version_value_dict[version]
    
        
    def Is_Modified(self):
        '''
        Returns True if this display item computed an output and
        any dependency is modified, else False.
        Note: may go awry if the display item string is meant to
        be empty, but that is a very minor issue since this
        function is only used for gui highlights.
        Note: may false-positive if an optional but unused dependency
        was modified.
        '''
        if not self.Get_Value('edited'):
            return False
        # Now look for modified dependencies.
        if any(dep.Is_Modified() for dep in self.dependencies if dep != None):
            return True
        return False


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
      - String made from a "name,virtual_path,xpath,attribute", used as
        a way to identify this item uniquely but generically, for saving
        patches and elsewhere applyling them to xml.
      - For safety across versions, there is some slight redundancy
        between name and the other fields, but this can allow either
        name or another field to change and the correct item to
        still be identified. This is pending further development
        at this time.
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
        self.key                = '{},{},{},{}'.format(
            self.name, virtual_path, xpath, attribute)
        # Just to be safe, there should only be 3 commas, none from
        # the xpath or attribute.
        assert self.key.count(',') == 3

        # The edited value will initialize to the patched version.
        # Note: originally this started as an empty string, but that
        #  got messy with display items that couldn't do calculations
        #  off of blank input. Also, that style wouldn't pick up on
        #  deleted attributes very well.
        self.version_value_dict['edited'] = self.Get_Value('patched')
        return


    def Get_Value(self, version):
        '''
        Return the value from the given version.
        '''
        # On first call or after a reset, need to recheck the value.
        if self.version_value_dict.get(version) == None:

            # Should never arrive here for the edited version; that gets
            # initialized and never reset (or re-initialized upon reset).

            # TODO: consider leaving 'current' blank if the xml node
            # does not have a modified root yet (eg. when first starting
            # up, before running any plugins). This might not work so
            # well when pre-running some plugins, though.

            # Grab the game file with the source info.
            game_file = Load_File(self.virtual_path)            
            xml_root = game_file.Get_Root_Readonly(version)

            # Look up the xpath node; should be just one.
            nodes = xml_root.findall(self.xpath)
            if len(nodes) != 1:
                raise AssertionError(
                    'Error: Found {} nodes for file "{}", xpath "{}".'
                    .format(len(nodes), self.virtual_path, self.xpath))

            # Pull out the field info.
            # Note: may be empty, in which case use an empty string.
            self.version_value_dict[version] = nodes[0].get(self.attribute, default = '')
            
        return self.version_value_dict[version]
    

    def Get_Edited_Value(self):
        '''
        Returns the edited value.
        '''
        return self.Get_Value('edited')


    def Set_Value(self, version, value):
        '''
        Sets the value for the given version, and triggers resets on
        dependents. Normally expected to be used for edited values only,
        so consider using Set_Edited_Value. To update other versions,
        reset them and let them recheck the xml.
        '''
        self.version_value_dict[version] = value
        for dep in self.dependents:
            dep.Reset_Value(version)
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
        if self.version_value_dict['edited'] != self.version_value_dict['patched']:
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
        assert self.version_value_dict['edited'] != None
        
        return Custom_Patch(
            virtual_path = self.virtual_path, 
            xpath        = self.xpath,
            attribute    = self.attribute,
            value        = self.version_value_dict['edited'],
            )

    

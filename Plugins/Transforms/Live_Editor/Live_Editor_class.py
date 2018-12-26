
from collections import namedtuple
import json

from Framework import Settings, Print
from .Edit_Items import Edit_Item, Display_Item

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
        return

        
    def Reset(self):
        '''
        Resets the live editor.
        '''
        self.objects_dict     .clear()
        self.table_group_dict .clear()
        self.patches_dict     .clear()
        # Leave the table builders alone.
        return


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
        

    def Get_Table_Group(self, name, rebuild = False):
        '''
        Returns an Table_Group of the given name, building it if needed
        and a builder is available, or returns None otherwise.

        * rebuild
          - Bool, if True then the table group will be rebuilt even if
            it already exists.
          - May be useful if the xml may have changed since the last build.
        '''
        group = self.table_group_dict.get(name, None)
        if ((group == None or rebuild) 
        and self.table_group_builders.get(name, None) != None):
            # Call the builder function and store the group.
            group = self.table_group_builders[name]()
            self.Add_Table_Group(group)
        return group


    def Gen_Items(self):
        '''
        Generator which will yield all items from all objects.
        '''
        for edit_object in self.objects_dict.values():
            for item in edit_object.Get_Items():
                yield item
        return


    def Reset_Current_Item_Values(self):
        '''
        For all items, resets their 'current' value to force an update.
        For use when plugins have run since the items were gathered.
        '''
        for item in self.Gen_Items():
            item.Reset_Value('current')


    def Update_Patches(self):
        '''
        Updates the loaded patches, adding/updating any new ones from
        modified items, removing old patches when their item is no longer
        modified.
        '''
        for item in self.Gen_Items():
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


    def Save_Patches(self, file_name = None):
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

        # Pick the patch to use for the file, either default or based
        # on the override name.
        if file_name:
            path = Settings.Get_Output_Folder() / file_name
        else:
            path = Settings.Get_Live_Editor_Log_Path()

        # Create and write the file.
        with open(path, 'w') as file:
            json.dump(json_dict, file, indent = 2)
        return


    def Load_Patches(self, file_name = None):
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
        # Pick the patch to use for the file, either default or based
        # on the override name.
        if file_name:
            path = Settings.Get_Output_Folder() / file_name
        else:
            path = Settings.Get_Live_Editor_Log_Path()

        if not path.exists():
            return
        Print('Live Editor: Loading custom edits from "{}"'.format(path))

        with open(path, 'r') as file:
            json_dict = json.load(file)
        # TODO: consider having a backup way to identify patches
        # using item name, in case the xpath gets changed between
        # versions if it ever gets a multi-match error.
        for key, value in json_dict['patches'].items():
            self.patches_dict[key] = value
        return


    def Get_Patches(self):
        '''
        Returns a list of all patches, packed into Custom_Patch objects
        to separate fields.
        '''
        patch_list = []
        for key, value in self.patches_dict.items():
            # Convert 
            split_key = key.split(',')
            patch_list.append(Custom_Patch(
                virtual_path = split_key[0],
                xpath        = split_key[1],
                attribute    = split_key[2],
                value        = value,
                ))
        return patch_list

            
    

# Global version.
Live_Editor = Live_Editor_class()
    

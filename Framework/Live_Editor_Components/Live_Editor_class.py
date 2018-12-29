
from collections import namedtuple
import json

from ..Common import Settings, Print
from .Edit_Items import Edit_Item, Display_Item

# Use a named tuple to track custom patches.
# Values are strings.
Custom_Patch = namedtuple(
    'Custom_Patch', 
    ['name', 'virtual_path', 'xpath', 'attribute', 'value'])


class Live_Editor_class:
    '''
    This will handle live editing of tables in the gui.
    All tables should be added to the global Live_Editor.
    TODO: save/restore custom patches using some special file,
    probably json, probably in the output extension folder.

    Attributes:
    * category_objects_dict
      - Dict of dicts, holding every created Edit_Object.
      - Outer key is supported category name ('weapons','bullets', etc.),
        inner key is the object name.
    * category_objects_builders
      - Dict, keyed by supported object category name, holding the
        iterable functions which will create the objects.
    * tree_view_dict
      - Dict holding Edit_Tree_View objects, keyed by their name.
      - Note: this is replacing table groups, in general.
        TODO: delete table groups once fully converted.
    * tree_view_builders
      - Dict, keyed by supported tree_view name, holding the
        functions which will build the trees.
      - Used to autobuild tree views when a view is requested that
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
        self.category_objects_dict = {}
        self.category_objects_builders = {}
        self.tree_view_dict = {}
        self.tree_view_builders = {}
        self.patches_dict = {}
        return

        
    def Reset(self):
        '''
        Resets the live editor records of objects and object views.
        Patches will be recorded for the pre-reset state, and carried
        to post-reset. The output file is not updated.
        '''
        # Save the patches from the current state.
        self.Update_Patches()
        # Leave the tree builders alone; they never need reset.
        # Leave patches alone; want their state to be kept.
        # Only really need to reset objects and tree views.
        self.category_objects_dict .clear()
        self.tree_view_dict        .clear()
        return


    def _Add_Object(self, category, edit_object):
        '''
        Record a new Edit_Object, and finish its setup.
        The object should have all items recorded by this point.
        Error if the name is already taken; this is a generally
        unexpected situation, and should be handled specially
        if it comes up, for now.
        Error if the category is missing, indicating an object
        was added from outside the expected builder function.
        '''
        # Verify there is no name collision in any category.
        assert all(edit_object.name not in x 
                   for x in self.category_objects_dict.values())
        # Record to the given category.
        self.category_objects_dict[category][edit_object.name] = edit_object

        # Fill its category and parent attributes.
        edit_object.category = category
        edit_object.parent   = self
        # Do an initial depedency filling.
        edit_object.Delayed_Init()

        # Check for patches to apply.
        # This will need to check each item, since they may be sourced
        # from different original files.
        # Note: for robustness against changes to base item names or
        # xpaths, support matching based on one or the other of those
        # terms.
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
        for subdict in self.category_objects_dict.values():
            if name in subdict:
                return subdict[name]
        return None


    def Record_Tree_View_Builder(self, name, build_function):
        '''
        Records the build function for a Edit_Tree_View of the given name.
        '''
        self.tree_view_builders[name] = build_function
        return

    
    def Record_Category_Objects_Builder(self, category, build_function):
        '''
        Records the build function for a Edit_Objects of the given category.
        '''
        self.category_objects_builders[category] = build_function
        return


    def Get_Tree_View(self, name, rebuild = False):
        '''
        Returns an Edit_Tree_View of the given name, building it if needed
        and a builder is available; error if the builder isn't found.

        * rebuild
          - Bool, if True then the table group will be rebuilt even if
            it already exists.
          - May be useful if the xml may have changed since the last build.
        '''
        if name not in self.tree_view_dict or rebuild:
            # Call the builder function and store the view.
            edit_tree_view = self.tree_view_builders[name]()
            self.tree_view_dict[edit_tree_view.name] = edit_tree_view
        return self.tree_view_dict[name]


    def Get_Category_Objects(self, category, rebuild = False):
        '''
        Returns a list of Edit_Objects from the given category.
        Builds the category objects if they haven't been built yet.
        '''
        if category not in self.category_objects_dict or rebuild:
            # Set up a category for the objects, also clearing
            #  out any existing objects.
            self.category_objects_dict[category] = {}

            # Add the objects in.
            for object in self.category_objects_builders[category]():
                self._Add_Object(category, object)

        return list(self.category_objects_dict[category].values())


    def Gen_Items(self):
        '''
        Generator which will yield all items from all objects.
        '''
        for subdict in self.category_objects_dict.values():
            for edit_object in subdict.values():
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
            split_key = key.split(',')
            patch_list.append(Custom_Patch(
                name         = split_key[0],
                virtual_path = split_key[1],
                xpath        = split_key[2],
                attribute    = split_key[3],
                value        = value,
                ))
        return patch_list

            
    

# Global version.
Live_Editor = Live_Editor_class()
    

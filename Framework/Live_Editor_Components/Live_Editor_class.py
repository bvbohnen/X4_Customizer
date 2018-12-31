
from collections import namedtuple
import json

from ..Common import Settings, Print
from .Edit_Items import Edit_Item, Display_Item
from ..File_Manager import Load_File


from functools import wraps

# Two layer decorators; outer layer captures misc args, and returns
# an inner layer that captures the function being wrapped.
def Live_Editor_Object_Builder(category):
    'Wrapper function for Edit_Object builders for the Live Editor.'
    def inner_decorator(function):
        Live_Editor.Record_Category_Objects_Builder(category, function)
        return function
    return inner_decorator

def Live_Editor_Tree_View_Builder(name):
    'Wrapper function for Edit_Tree_View builders for the Live Editor.'
    def inner_decorator(function):
        Live_Editor.Record_Tree_View_Builder(name, function)
        return function
    return inner_decorator


class Custom_Patch:
    '''
    Patch captuing a hand edited value that was changed from default.

    Attributes (all strings):
    * name
    * virtual_path
    * xpath
    * attribute
    * value
    * xml_node_id
    '''
    def __init__(self, name, virtual_path, xpath, attribute, value, xml_node_id = None):
        self.name = name
        self.virtual_path = virtual_path
        self.xpath = xpath
        self.attribute = attribute
        self.value = value
        self.xml_node_id = xml_node_id

    def Get_Item_Key(self):
        '''
        Returns a key with (name,virtual_path,xpath,attribute).
        '''
        return '{},{},{},{}'.format(
            self.name, self.virtual_path, self.xpath, self.attribute)

    def Get_Node_ID_Key(self):
        '''
        Returns a key with (virtual_path,xml_node_id,attribute), or
        None if the xml_node_id is not filled in.
        '''
        if self.xml_node_id == None:
            return None
        return '{},{},{}'.format(
                self.virtual_path, self.xml_node_id, self.attribute) 

    def Update_From_Item(self, item):
        '''
        When item is found to match this patch, the patch will update
        its name and xpath from the item (to update it across version
        changes). These changes will be reflected in the next file
        output.
        '''
        self.name = item.name
        self.xpath = item.xpath


## Use a named tuple to track custom patches.
## Values are strings.
#Custom_Patch = namedtuple(
#    'Custom_Patch', 
#    ['name', 'virtual_path', 'xpath', 'attribute', 'value', 'xml_node_id'])


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
    * patches_key_dict
      - Dict holding patch values, loaded from a prior run or
        updated with current changes.
      - Key is taken from item keys, eg. (name, virtual_path, xpath, attribute),
        formed this way to make json save/load easier.
      - To be checked and applied whenever an Edit_Object is added,
        and updated before writing out to json.
    * patches_node_id_dict
      - As above, except keyed by an alternate combination of attributes
        that includes the xml node id.
      - This is only set up as json loading, and used as a backup match
        for new items.
      - During runtime, this dict may get out of date (holding deleted
        patches and similar), but any such discrepencies should be
        harmless as long as the patches_key_dict is checked first.
    '''
    def __init__(self):
        self.category_objects_dict = {}
        self.category_objects_builders = {}
        self.tree_view_dict = {}
        self.tree_view_builders = {}
        self.patches_key_dict = {}
        self.patches_node_id_dict = {}
        self.init_complete = False
        return

        
    def Reset(self):
        '''
        Resets the live editor records of objects and object views.
        Patches will be recorded for the pre-reset state, and carried
        to post-reset. The output file is not updated.
        '''
        # Save the patches from the current state; these should never
        # need a full reset (unless switching to writing a file and
        # reading it back in).
        self.Update_Patches()
        # Leave the tree builders alone; they never need reset.
        # Leave patches alone; want their state to be kept.
        # Only really need to reset objects and tree views.
        self.category_objects_dict .clear()
        self.tree_view_dict        .clear()
        return


    def Delayed_Init(self):
        '''
        Load old patches and do any other delayed initialization.
        Since patches will load xml files to find patched nodes,
        this should be called after settings and the file system
        are set up, but before objects are loaded.
        '''
        # Only do this once.
        if self.init_complete:
            return
        self.init_complete = True
        self.Load_Patches()
        # TODO: anything else needed here.
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

            # Check the key.
            # Do this two ways, first using the item key as a primary check,
            # then do a backup check for node ids (for protection against
            # version changes).
            node_id_key = '{},{},{}'.format(item.virtual_path, 
                                            item.xml_node_id, 
                                            item.attribute)

            patch = None
            if item.key in self.patches_key_dict:
                patch = self.patches_key_dict[item.key]

            elif node_id_key in self.patches_node_id_dict:
                Print('Updating a live editor patch format to: "{}"'.format(item.key))
                patch = self.patches_node_id_dict[node_id_key]
                # If here, the patch is from an older version of the tool
                # which had a different item name or xpath.
                # Update the patch to the current item.
                patch.Update_From_Item(item)

            # Check if a patch was found.
            if patch != None:
                # Can just overwrite the edited value directly.
                # This doesn't need to worry about attribute deletions.
                item.Set_Edited_Value(patch.value)
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
        Runs Delayed_Init on the first call that builds objects.
        '''
        if category not in self.category_objects_dict or rebuild:
            self.Delayed_Init()
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
        return


    def Update_Patches(self):
        '''
        Updates the loaded patches, adding/updating any new ones from
        modified items, removing old patches when their item is no longer
        modified, keeping patches that are not matched to an item.

        This will only modify the patches_key_dict, while the
        patches_node_id_dict will be allowed to get out of sync.
        '''
        for item in self.Gen_Items():
            # Skip non-edit items.
            if not isinstance(item, Edit_Item):
                continue

            # Check for modified Edit_Item objects.
            # Note: at this point patches should be in sync with
            # the item keys, having been updated at item loading.

            if item.Is_Modified():

                # Update an existing patch if present.
                if item.key in self.patches_key_dict:
                    self.patches_key_dict[item.key].value = item.Get_Edited_Value()

                # Else make a new one.
                else:
                    self.patches_key_dict[item.key] = Custom_Patch(
                        name         = item.name,
                        virtual_path = item.virtual_path,
                        xpath        = item.xpath,
                        attribute    = item.attribute,
                        value        = item.Get_Edited_Value(),
                        xml_node_id  = item.xml_node_id,
                        )                                       

            # When not modified, delete any old patch for this item.
            elif item.key in self.patches_key_dict:
                self.patches_key_dict.pop(item.key)
        return


    def Save_Patches(self, file_name = None):
        '''
        Save the loaded patches to a json file.
        By default, saves to the output extension folder.
        This will preserve existing patches loaded earlier.
        If Delayed_Init was not run, this will do nothing, avoiding
        overwriting a file with prior patches that were never loaded.
        '''
        # Skip when not initialized.
        # Alternative would be to initialize before continuing, but
        # that can add runtime delay that is unnecessary, since saving
        # is done when closing the gui currently.
        if not self.init_complete:
            return

        # Start by bringing loaded patches up to date.
        self.Update_Patches()

        # Give on layer of nesting to the json, in case it will
        # ever have other fields added.
        patch_dict = {}
        json_dict = {'patches' : patch_dict}

        # Record patches in sorted order.
        # Aim to sort by virtual_path then xpath, eg. clumping edits
        # to the same node together.
        for patch in sorted(self.Get_Patches(), 
                            key = lambda x: (x.virtual_path, x.xpath, x.name)):
            # Use the recording key for it, which doesn't include
            # node id (which doesn't carry between sessions).
            patch_dict[patch.Get_Item_Key()] = patch.value

        # Pick the path to use for the file, either default or based
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
        On json load error, this will crash gracelessly to avoid continuing
        and accidentally overwriting a file that a user may have hand edited.       
        This may be called multiple times to load patches from multiple files,
        if needed.

        Note: this load may happen before the patched objects are set up;
        actual patch application will be checked when objects are added.
       
        '''
        # Pick the patch to use for the file, either default or based
        # on the override name.
        if file_name:
            path = Settings.Get_Output_Folder() / file_name
        else:
            path = Settings.Get_Live_Editor_Log_Path()

        # Skip if the file doesn't exist.
        if not path.exists():
            return
        Print('Live Editor: Loading custom edits from "{}"'.format(path))

        # Load the json; let it crash if something goes wrong.
        with open(path, 'r') as file:
            json_dict = json.load(file)

        # Work through the patches, looking to find their matching
        # xml nodes.
        for key, value in json_dict['patches'].items():
            split_key = key.split(',')
            virtual_path = split_key[1]
            xpath        = split_key[2]
            
            # Load the file with the patch target node.
            game_file = Load_File(virtual_path)
            if game_file == None:
                xml_node_id = None
            else:
                # Search for the node, patched version.
                # Note: this should sync up with what the Edit_Items
                # use for their xml_node_id.
                nodes = game_file.Get_Xpath_Nodes(xpath, version = 'patched')
                # It is possible a node won't be found.
                if not nodes:
                    xml_node_id = None
                else:
                    # Don't check for >1 for now; that is checked when
                    # patched are properly applied in a transform.
                    xml_node_id = nodes[0].tail
                    # An id should have been attached.
                    assert xml_node_id
            
            patch = Custom_Patch(
                name         = split_key[0],
                virtual_path = split_key[1],
                xpath        = split_key[2],
                attribute    = split_key[3],
                value        = value,
                xml_node_id  = xml_node_id,
                )
            
            # Record the patch by all supported keys.
            self.patches_key_dict[patch.Get_Item_Key()] = patch
            if patch.Get_Node_ID_Key() != None:
                self.patches_node_id_dict[patch.Get_Node_ID_Key()] = patch
            
        return


    def Get_Patches(self):
        '''
        Returns a list of all patches, as Custom_Patch objects.
        '''
        # Can use either patch dict for this, though keys may
        # be slightly more in date.
        return list(self.patches_key_dict.values())

            
    

# Global version.
Live_Editor = Live_Editor_class()
    

'''
Thoughts on how to deal with patch key changes across versions:

    The basic idea: between customizer versions, either an
    xpath or field name may change in the item macros,
    which will break directly patch key matching.

    Option 1)
        Since the keys have both a local field name and an xpath,
        along with the virtual path and attribute name, they can potentially
        check alternate versions of the keys: 
            (field,virtual,attr)
            (virtual,xpath,attr)
        When doing this, an alternate match found should update the patch
        in question, so that it doesn't carry old version cruft into
        future versions.

        To carry this out somewhat efficiently (not rebuilding the alt
        keys every time), the alt keys would need to be generated per
        patch as well as per item, and then cross checked.

    Option 2)
        Since xpaths should always find the same node for the
        item and the patch of that item, this could instead
        do a sample xml node lookup for each patch, and compare against
        the node(s) referenced by the item when it was intialized.
        When nodes match, the item can be patched, and the patch itself
        updated with the item key.

        This approach would be the most robust, since field name and
        xpath can be tweaked in the item macros without worrying out
        patches getting too out of sync.

        However, this approach has higher overhead, paying the
        full patch application penalty (almost) for xpath lookups,
        though this should be relatively small compared to the items
        being loaded (which check 3 versions of all fields, whereas
        most items will not be patched and the patch only checks
        one version).

        Regarding xml node version, patches are applied to the 'edited'
        item value, which in turn starts as a copy of the 'patched'
        item value, so this can compare based on the 'patched' xml.
        Note that this is different than when patches are properly
        applied to xml, using the 'current' version (same as 'patched'
        up until transforms are run).
        TODO: revisit this when pre-edit transform support is added,
        since the source xml will be some special version.

        Side note: the element objects returned by xpath checks can
        change location across xpath evaluations; reuse the node
        ids added to element tags for diff generation support.
'''
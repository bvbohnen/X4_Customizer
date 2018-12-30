
from collections import defaultdict
from Framework import Transform_Wrapper, Settings, Plugin_Log, Load_File
from Framework import Live_Editor


@Transform_Wrapper(category = 'Live_Editor')
def Apply_Live_Editor_Patches(
        file_name = None
    ):
    '''
    This will apply all patches created by hand through the live editor
    in the GUI.
    This should be called no more than once per script, and currently
    should be called before any other transforms which might read
    the edited values.
    Pending support for running some transforms prior to hand edits.

    * file_name
      - Optional, alternate name of a json file holding the 
        Live_Editor generated patches file.
      - Default uses the name in Settings.
    '''
    # Make sure the live editor is up to date with patches.
    # TODO: think about how safe this is, or if it could overwrite
    # meaningful existing state.
    Live_Editor.Load_Patches(file_name)
    
    # TODO: fork the xml game files at this point, keeping a copy
    # of the pre-patch state, so that live editor pages loaded
    # after this point and properly display the xml version from
    # before the hand edits and later transforms.
    # This may need to be done wherever pre-edit transform testing
    # is handled.

    # Work through the patches.
    # To do a cleaner job loading/saving game files, categorize
    # the patches by virtual_path first.
    path_patches_dict = defaultdict(list)
    for patch in Live_Editor.Get_Patches():
        path_patches_dict[patch.virtual_path].append(patch)

    for virtual_path, patch_list in path_patches_dict.items():
        # Note: if patches get out of date, they may end up failing at
        # any of these steps.

        # Load the file.
        game_file = Load_File(virtual_path)
        if game_file == None:
            Plugin_Log.Print(('Warning: Apply_Live_Editor_Patches could'
                            ' not find file "{}"'
                            ).format(virtual_path))
            continue

        # Modify it in one pass.
        root = game_file.Get_Root()

        for patch in patch_list:
            # Look up the edited node; assume just one xpath match.
            node = root.find(patch.xpath)
            if node == None:
                Plugin_Log.Print(('Warning: Apply_Live_Editor_Patches could'
                                ' not find node "{}" in file "{}"'
                                ).format(patch.xpath, virtual_path))
                continue

            # Either update or remove the attribute.
            # Assume it is safe to delete if the value is an empty string.
            if patch.value == '':
                if patch.attribute in node.keys():
                    node.attrib[patch.attribute].pop()
            else:
                node.set(patch.attribute, patch.value)

        # Put changes back.
        # TODO: maybe delay this until all patches get applied, putting
        # back before returning.
        game_file.Update_Root(root)
                
    return
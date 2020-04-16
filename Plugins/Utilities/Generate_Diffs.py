
from pathlib import Path
from itertools import zip_longest

from Framework import Utility_Wrapper
from Framework import Plugin_Log
from Framework import Print
from Framework.File_Manager import XML_File
from Framework.File_Manager.Cat_Reader import Get_Hash_String


@Utility_Wrapper()
def Generate_Diffs(
        original_file_path,
        modified_file_path,
        output_diff_path,
    ):
    '''
    Generate diffs for changes between two xml files, creating a diff patch.

    * original_file_path
      - Path to the original xml file that acts as the baseline.
    * modified_file_path
      - Path to the modified version of the xml file.
    * output_diff_path
      - Path to write the diff patch to.
    '''
    assert original_file_path != modified_file_path
    assert output_diff_path != original_file_path
    assert output_diff_path != modified_file_path

    '''
    This will reuse existing infrastructure as much as reasonable.
    Basic idea:
    - Load the original file into a Game_File.
    - Load the changed file, possibly to another temp Game_File.
    - Striding through the pair, set the changed file node ids to match
      those of the original file where nodes appear to be the same.
    - Put the id-matched version of the changed xml back in the original
      file's Game_File as its modified version.
    - Tell the Game_File to write a diff patch to the output path.
    '''
    # Load the original.
    base_game_file = XML_File(
        # Virtual path doesn't matter.
        virtual_path = '',
        binary = original_file_path.read_bytes(),
        # Flag as the source; this will trigger diff patch generation later.
        from_source = True,
        )

    # Finish initializing it; no diff patches to wait for.
    # This fills in initial node ids.
    base_game_file.Delayed_Init()

    # Load the modified. Just want the xml nodes, but use a game_file
    # for consistent loading format.
    temp_game_file = XML_File(
        virtual_path = '',
        binary = modified_file_path.read_bytes(),
        )
    # Go ahead and give node ids. Not too important, but might do some
    # misc formatting, eg. removing tails.
    temp_game_file.Delayed_Init()


    # Pick out the roots.
    original_root = base_game_file.Get_Root()
    modified_root = temp_game_file.Get_Root()

    # Gather hashes, with and without attributes included.
    attr_hash_dict, no_attr_hash_dict = Fill_Element_Hashes(original_root)
    Fill_Element_Hashes(modified_root, attr_hash_dict, no_attr_hash_dict)
    
    # Start matching ids.
    '''
    Basic matching ideas:
    - At a given level, collect child node lists.
    - Goal is to identify which children are the same basic node, which 
      only requires a tag match, but should ideally have attribute matches
      and many child matches.
    - Can build a hash of all nodes, progressively upward, to simplify
      matching identical nodes (same tag, attributes, and children).
    '''
    # The top level node should always match, so do that directly.
    if original_root.tag != modified_root.tag:
        Print('Generate_Diffs error: root tag mismatch, {} vs {}'.format(
            original_root.tag,
            modified_root.tag ))
    modified_root.tail = original_root.tail

    # Fill in child node tag matches, recursively.
    Match_Child_Tags(original_root, modified_root, attr_hash_dict, no_attr_hash_dict)


    # Put the modified xml back in the game_file.
    base_game_file.Update_Root(modified_root)

    # Write to file. This will trigger the diff patch generation. 
    base_game_file.Write_File(output_diff_path)

    return


def Fill_Element_Hashes(element, attr_hash_dict = None, no_attr_hash_dict = None):
    '''
    Returns a pair of dicts matching each xml element to a hash string, where
    the hash accounts for the node tag, attributes, and the hashes of
    all child nodes in order.

    The first dict includes node attributes in the hash; the second does
    not include attributes (of this node or any children).
    '''
    # Start a new dict if needed.
    if attr_hash_dict == None:
        attr_hash_dict = {}
    if no_attr_hash_dict == None:
        no_attr_hash_dict = {}

    # Construct a text string the summarizes this node and child hashes.
    # TODO: could maybe loop the attr and no-attr versions.
    attr_hash_text    = ''
    no_attr_hash_text = ''

    # Start with the element tag and attributes.
    attr_hash_text    += 'tag:{},'.format(element.tag)
    no_attr_hash_text += 'tag:{},'.format(element.tag)

    for attr, value in sorted(element.items()):
        attr_hash_text += '{}:{},'.format(attr, value)

    # Gather all child hashes.
    for child in element.getchildren():

        # Costruct the hash if needed (should generally occur).
        if child not in attr_hash_dict:
            Fill_Element_Hashes(child, attr_hash_dict, no_attr_hash_dict)

        # Use the attribute-including hash of the child.
        attr_hash_text    += attr_hash_dict[child]+','
        no_attr_hash_text += no_attr_hash_dict[child]+','

    # Shorten it for faster matching, using an md5 hash.
    attr_hash = Get_Hash_String(attr_hash_text.encode())
    attr_hash_dict[element] = attr_hash
    
    no_attr_hash = Get_Hash_String(no_attr_hash_text.encode())
    no_attr_hash_dict[element] = no_attr_hash

    return attr_hash_dict, no_attr_hash_dict


def Match_Child_Tags(
        original_node, 
        modified_node, 
        attr_hash_dict, 
        no_attr_hash_dict
    ):
    '''
    Search the children of the given pair of elements, and copy tags from
    the original elements to the modified elements where matches are found.
    '''
    # This will use code similar to what is in XML_Diff for matching children,
    # but modified somewhat to use hashes which may repeat.
    
    # Look for child node changes.
    # The approach will be to use a running walk between both child
    #  lists, matching up node hashes; when there is a mismatch, can
    #  check if one side's node is present in the other side's list,
    #  indicating what happened (add or remove).

    # Collect the child lists.
    # During processing, nodes will get popped off as their match/mismatch
    # status is determined. Matches pop off both lists. Mismatches may
    # pop off one list depending on if it appears to be an insert or delete.
    orig_children = original_node.getchildren()
    mod_children  = modified_node.getchildren()
    
    def Is_No_Attr_Match(orig, mod):
        return no_attr_hash_dict[orig] == no_attr_hash_dict[mod]

    # Loop while nodes remain in both lists.
    # Once one runs out, there are no more matches.
    while orig_children and mod_children:

        # Sample elements from both lists; don't remove yet.
        orig_child = orig_children[0]
        mod_child = mod_children[0]


        # If the no-attribute node hashes match, consider the nodes
        # to be fully matched; diff patches will be generated to
        # capture attribute changes.
        if Is_No_Attr_Match(orig_child, mod_child):
            # Copy over the IDs.
            Set_ID_Matches_Recursively(orig_child, mod_child)
            # Pop off both lists.
            orig_children.remove(orig_child)
            mod_children .remove(mod_child)
            continue

        # If here, either node tag or details of node children differ.
        # Tag mismatch is a certain node mismatch.
        # Tag mismatch is a maybe node mismatch.
        match = False
        if orig_child.tag == mod_child.tag:
            # Same tag; could potentially be set as a match, but it might
            # result in a bunch of unnecessary child node mismatches
            # if there is a better match later.
            # For version 1, just consider a match and move on.
            # TODO: check if there is a better match later, and wait for
            # it.
            match = True
                    
        if match:
            # Copy this top level node id.
            mod_child.tail = orig_child.tail

            # Process the children of the nodes.
            Match_Child_Tags(
                orig_child, 
                mod_child, 
                attr_hash_dict, 
                no_attr_hash_dict)

            # Pop off both lists.
            orig_children.remove(orig_child)
            mod_children .remove(mod_child)

        else:
            # Want to determine if this is an insertion or deletion.
            # An insert should advance the mod_children but not the
            # orig_children.
            # A deletion should do the reverse, advancing only orig_children.

            # Check if the mod_child matches elsewhere in the original.
            mod_child_in_orig = any( Is_No_Attr_Match(x, mod_child) for x in orig_children)
            # Check if the orig_child matches elsewhere in the child.
            orig_child_in_mod = any( Is_No_Attr_Match(orig_child, x) for x in mod_children)
            
            if mod_child_in_orig == True and orig_child_in_mod == False:
                # This case suggests a node was removed.
                orig_children.remove(orig_child)
            
            elif mod_child_in_orig == False and orig_child_in_mod == True:
                # This case suggests a node was added.
                mod_children .remove(mod_child)

            elif mod_child_in_orig == False and orig_child_in_mod == False:
                # Neither node is in the other; remove both.
                orig_children.remove(orig_child)
                mod_children .remove(mod_child)

            else:
                # Something weird happened; nodes somehow got reordered?
                # Just pick a node to throw out; go with modified node,
                # so the original tail is available for matching still
                # (maybe slightly better?).
                mod_children .remove(mod_child)

    return


def Set_ID_Matches_Recursively(original_node, modified_node):
    '''
    Copy ids from the original to the modified node. This should only
    be called if the node tags perfectly match (for all children as well).
    '''
    assert original_node.tag == modified_node.tag
    modified_node.tail = original_node.tail
    for orig_child, mod_child in zip_longest(
                                    original_node.getchildren(),
                                    modified_node.getchildren()):
        # Should never run out of nodes in either list.
        assert orig_child != None and mod_child != None
        Set_ID_Matches_Recursively(orig_child, mod_child)
    return
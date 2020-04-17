
from pathlib import Path
from itertools import zip_longest
import difflib

from Framework import Utility_Wrapper
from Framework import Plugin_Log
from Framework import Print
from Framework.File_Manager import XML_File
from Framework.File_Manager.Cat_Reader import Get_Hash_String
from Framework.File_Manager.XML_Diff import Print as XML_Print


@Utility_Wrapper(uses_paths_from_settings = False)
def Generate_Diffs(
        original_dir_path,
        modified_dir_path,
        output_dir_path,
        skip_unchanged = False,
        verbose = False,
    ):
    '''
    Generate diffs for changes between two xml files, creating a diff patch.

    * original_dir_path
      - Path to the original xml file that acts as the baseline.
    * modified_dir_path
      - Path to the modified version of the xml file.
    * output_dir_path
      - Path to write the diff patch to.
    * skip_unchanged
      - Bool, skip output for files that are unchanged (removing any
        existing diff patch).
      - Default will generate empty diff patches.
    * verbose
      - Bool, print the path of the outputs on succesful writes.
    '''
    # Gather all xml files from the input directorys.
    # Make dicts for ease of use, keyed by relative path from the
    # base folder.
    #original_paths = {x.relative_to(original_dir_path) : x for x in original_dir_path.glob('**/*.xml')}
    modified_paths = {x.relative_to(modified_dir_path) : x for x in modified_dir_path.glob('**/*.xml')}

    # Pair off the modified files with originals by name.
    # If an original is not found, error.
    # Ignore excess originals.
    for rel_path, mod_path in modified_paths.items():

        orig_path = original_dir_path / rel_path
        if not orig_path.exists() and orig_path.is_file():
            Print('No matching original file found for {}'.format(name))
            continue

        # Set up the output.
        out_path = output_dir_path / rel_path

        if verbose:
            Print('Generating diff for {}'.format(rel_path.name))

        # Generate the diff. If this errors, the file will be skipped
        # (due to plugin wrapper).
        Generate_Diff(
            original_file_path = orig_path,
            modified_file_path = mod_path,
            output_file_path   = out_path,
            skip_unchanged     = skip_unchanged,
            verbose            = verbose
        )

    return


@Utility_Wrapper(uses_paths_from_settings = False)
def Generate_Diff(
        original_file_path,
        modified_file_path,
        output_file_path,
        skip_unchanged = False,
        verbose = False,
    ):
    '''
    Generate a diff of changes between two xml files, creating a diff patch.

    * original_file_path
      - Path to the original xml file that acts as the baseline.
    * modified_file_path
      - Path to the modified version of the xml file.
    * output_file_path
      - Path to write the diff patch to.
    * skip_unchanged
      - Bool, skip output for files that are unchanged (removing any
        existing diff patch).
      - Default will generate empty diff patches.
    * verbose
      - Bool, print the path of the outputs on succesful writes.
    '''
    if (original_file_path == modified_file_path
    or  output_file_path == original_file_path
    or  output_file_path == modified_file_path):
        raise Exception('Path conflict error')

    # List of messages to print out.
    messages = []
    def Print_Messages():
        'Prints all pending messages.'
        while messages:
            message = messages.pop(0)
            # TODO: maybe allow this if Settings are set up, otherwise
            # might give an error on eg. missing x4 path.
            #Plugin_Log.Print(message)
            if verbose:
                Print(message)


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
    
    # Start by using a standard text diff library.
    # This is very good at matching up exact nodes regardless of their
    # parentage.  Not so good at handling attribute changes or data
    # structure changes.
    # Returns a dict pairing original with modified nodes.
    text_based_node_matches = Get_Text_Diff_Matches(original_root, modified_root)

    # Note: if all nodes were matches on both sides, then the
    # file hasn't been changed (except maybe formatting and such).
    num_matches = len(text_based_node_matches)
    num_orig_nodes = len([x for x in original_root.iter()])
    num_mod_nodes  = len([x for x in modified_root.iter()])
    unchanged = num_matches == num_orig_nodes == num_mod_nodes

    # If files match, check arg for skipping the file.
    if unchanged and skip_unchanged:

        messages.append('File unchanged: {}'.format(modified_file_path))
        # Check if an output file already exists and delete it.
        if output_file_path.exists():
            output_file_path.unlink()
            messages.append('Removing prior diff: {}'.format(output_file_path))

    else:
        # Don't need to put the modified root back if there are no changes.
        if not unchanged:
            # Follow up with a manual traversal of the trees, completing matches.
            Match_Trees(original_root, modified_root, text_based_node_matches)

            # Put the modified xml back in the game_file.
            base_game_file.Update_Root(modified_root)

        # Write to file. This will trigger the diff patch generation,
        # empty if no changes.
        # This also makes the directory if needed.
        base_game_file.Write_File(output_file_path)

        # The above can be handy as a print message to verify the update.
        messages.append('Generated diff written to: {}'.format(output_file_path))

    Print_Messages()
    return


class Element_Wrap:
    '''
    Wrapper on xml elements with custom comparison rules.
    '''
    def __init__(self, xml):
        self.xml = xml
        self.tag = xml.tag
        self.attrib = dict(xml.attrib)
        self.text = xml.text

    def __eq__(self, other):
        # Check tags, attributes, text.
        if(self.tag != other.tag 
        or self.attrib != other.attrib
        or self.text != other.text):
            return False
        # TODO: maybe check parent tags as well, for conservative matching.
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        # Note: just doing something like id(self) gives horrible results;
        # the hash appears to be part of the comparison.
        hash_str = '{},{},{}'.format(
            self.tag, 
            ','.join(['{}:{}'.format(k,v) for k,v in sorted(self.attrib.items())]),
            self.text)
        hash_int = hash(hash_str)
        return hash_int


def Get_Text_Diff_Matches(original_root, modified_root):
    '''
    Identify modifications with the help of a text diff library.
    Returns a dict matching original elements to modified elements that
    appear to be the same.
    '''

    # Flatten out all of the nodes, and wrap them with custom
    # match logic.
    original_nodes = [Element_Wrap(x) for x in original_root.iter()]
    modified_nodes = [Element_Wrap(x) for x in modified_root.iter()]

    # Sequence matcher will pair up the nodes.
    matcher = difflib.SequenceMatcher(None, original_nodes, modified_nodes)
    
    # Dict pairing original to modified nodes that the sequencer matched.
    orig_mod_matches = {}
    
    # get_matching_blocks returns a series of tuples of
    # (i, j, n) where a[i:i+n] == a[j:j+n]
    # Note: this may end up matching nodes from one parent's child elements
    # to those of another parent. However, this is not expected to be a
    # problem, since the diff generator just checks for matches under
    # an already matched parent.
    for orig_base, mod_base, num_lines in matcher.get_matching_blocks():    
        for offset in range(num_lines):
            orig_node = original_nodes[orig_base + offset].xml
            mod_node  = modified_nodes[mod_base + offset].xml
            orig_mod_matches[orig_node] = mod_node
            

    # When a node changed attributes, if it had children, they may have
    # been matched. Can treat the parent as matched if any children matched.
    # This is easiest to do backwards: for all matched nodes, set their
    # parents as matched if not already.
    # Error if any mod nodes are matched again.
    mod_nodes_matched = set([x for x in orig_mod_matches.values()])
    # Loop until all orig nodes processed; this list will extend on
    # each new match.
    orig_nodes_to_check = [x for x in orig_mod_matches]
    while orig_nodes_to_check:
        orig_node = orig_nodes_to_check.pop(0)
        mod_node  = orig_mod_matches[orig_node]

        # Get their parents.
        orig_parent = orig_node.getparent()
        mod_parent  = mod_node.getparent()
        # If reaching the top, skip.
        if orig_parent == None or mod_parent == None:
            continue

        # In some cases, nodes may have been matched across different parents.
        # Do some extra validation before trying to match these parents.
        if( (orig_parent not in orig_mod_matches)
        # Tag can't have changed.
        and (orig_parent.tag == mod_parent.tag)
        # These nodes should not have existing matches.
        and (orig_parent not in orig_mod_matches)
        and (mod_parent  not in mod_nodes_matched)
            ):
            orig_mod_matches[orig_parent] = mod_parent
            # Update dict and set for later loops.
            orig_nodes_to_check.append(orig_parent)
            mod_nodes_matched.add(mod_parent)

    return orig_mod_matches



def Match_Trees(original_root, modified_root, text_based_node_matches):
    '''
    Manually compare nodes between the xml trees, and try to find matches.
    Updates modified_root tail ids directly.
    '''
    # Gather hashes, with and without attributes included.
    attr_hash_dict, no_attr_hash_dict = Fill_Element_Hashes(original_root)
    Fill_Element_Hashes(modified_root, attr_hash_dict, no_attr_hash_dict)
    
    # The top level node should always match, so do that directly.
    if original_root.tag != modified_root.tag:
        Print('Generate_Diffs error: root tag mismatch, {} vs {}'.format(
            original_root.tag,
            modified_root.tag ))
    modified_root.tail = original_root.tail

    # Fill in child node matches, recursively.
    Match_Children(original_root, modified_root, 
                   attr_hash_dict, no_attr_hash_dict,
                   text_based_node_matches)
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


def Match_Children(
        original_node, 
        modified_node, 
        attr_hash_dict, 
        no_attr_hash_dict,
        text_based_node_matches
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
    # Note: use iterchildren instead of children to pick up comments.
    orig_children = [x for x in original_node.iterchildren()]
    mod_children  = [x for x in modified_node.iterchildren()]
    
    # Handy match check functions.
    def Is_Attr_Match(orig, mod):
        return attr_hash_dict[orig] == attr_hash_dict[mod]
    def Is_No_Attr_Match(orig, mod):
        return no_attr_hash_dict[orig] == no_attr_hash_dict[mod]
    def Is_Text_Diff_Match(orig, mod):
        return text_based_node_matches.get(orig) == mod

    # Loop while nodes remain in both lists.
    # Once one runs out, there are no more matches.
    while orig_children and mod_children:

        # Sample elements from both lists; don't remove yet.
        orig_child = orig_children[0]
        mod_child = mod_children[0]
        
        strong_match = False
        weak_match   = False
        
        # Check if there is a perfect match later, either direction.
        #mod_child_in_orig = any( Is_Attr_Match(x, mod_child) for x in orig_children[1:])
        #orig_child_in_mod = any( Is_Attr_Match(orig_child, x) for x in mod_children[1:])

        # Check if the text diff thinks there is a later match, either direction.
        mod_child_in_orig = any( Is_Text_Diff_Match(x, mod_child) for x in orig_children[1:])
        orig_child_in_mod = any( Is_Text_Diff_Match(orig_child, x) for x in mod_children[1:])


        # If node tags differ, not a match ever.
        if orig_child.tag != mod_child.tag:
            pass

        # If the text diff thinks these match, then treat as a match.
        # Note: if just the attributes differed, the backfill pass will
        # have set matches on parents of matching nodes, which is
        # caught here.
        elif Is_Text_Diff_Match(orig_child, mod_child):
            # If hashes are exact, save some time with an exact match.
            if Is_Attr_Match(orig_child, mod_child):
                strong_match = True
            else:
                # Set to look for nested changes.
                weak_match = True

        # If the attributes differed and the node had no children, there
        # is no existing match from the text diff.
        # In such cases, these nodes also don't match anything else later,
        # so can treat as the same if childless.
        elif (not mod_child_in_orig 
        and not orig_child_in_mod 
        and not list(orig_child) 
        and not list(mod_child)):
            weak_match = True
                    
        # TODO: if a node was inserted, and the following node changed,
        # the above can get confused and think a node was changed then
        # inserted.  Think of a general way to better handle such cases.

        if strong_match:
            # Copy over the IDs, for all children as well.
            for orig_subnode, mod_subnode in zip_longest(orig_child.iter(),
                                                        mod_child.iter()):
                assert mod_subnode.tag == orig_subnode.tag
                mod_subnode.tail = orig_subnode.tail
                
            # Pop off both lists.
            orig_children.remove(orig_child)
            mod_children .remove(mod_child)

        elif weak_match:
            # Copy this top level node id.
            mod_child.tail = orig_child.tail

            # Process the children of the nodes.
            Match_Children(
                orig_child, 
                mod_child, 
                attr_hash_dict, 
                no_attr_hash_dict,
                text_based_node_matches)

            # Pop off both lists.
            orig_children.remove(orig_child)
            mod_children .remove(mod_child)

        else:
            # Want to determine if this is an insertion or deletion.
            # An insert should advance the mod_children but not the
            # orig_children.
            # A deletion should do the reverse, advancing only orig_children.

            if mod_child_in_orig == True and orig_child_in_mod == False:
                # This case suggests a node was removed.
                orig_children.remove(orig_child)
            
            elif mod_child_in_orig == False and orig_child_in_mod == True:
                # This case suggests a node was added.
                mod_children .remove(mod_child)

            elif mod_child_in_orig == False and orig_child_in_mod == False:
                # Neither node is in the other; remove both.
                # TODO: check for a no-attribute match later, and if found,
                # just remove one of these.
                orig_children.remove(orig_child)
                mod_children .remove(mod_child)

            else:
                # This indicates a reordering.
                # Just pick a node to throw out; go with modified node,
                # so the original tail is available for matching still
                # (maybe slightly better?).
                mod_children .remove(mod_child)

    return

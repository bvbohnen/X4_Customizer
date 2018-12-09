'''
XML Diff patch support functions.
Aims to (roughly) support a common subset of RFC 5261.
https://tools.ietf.org/html/rfc5261
'''
'''
Side note: Python xml libraries (lxml and ElementTree) xpath operations
are always with reference to the proper root node.
X4 xpath appears to have a virtual node above root.
Eg. in Python, to select root, use '/', but in X4, use '/[0]' or similar.

Inputs to these functions will use Python roots, and internally do
temporary super-root addition to handle operations in the X4 style.
(X4 style does notably allow for replacement of root.)
'''
from lxml import etree as ET
from copy import deepcopy
from itertools import zip_longest
import random

from ..Common import Transform_Log

def Apply_Patch(original_node, patch_node):
    '''
    Apply a diff patch to the target xml node.
    Returns the modified node, possibly a changed-in-place original_node
    but maybe a complete replacement.

    If the patch_node is a 'diff', performs diff patching.
    Otherwise the patch_node must have the same tag as original_node,
    and its children will be appended to this original_node's children.
    '''
    # Requires elements as inputs.
    assert isinstance(original_node, ET._Element)
    assert isinstance(patch_node, ET._Element)
    
    if patch_node.tag != 'diff':
        # Error check for tag mismatch.
        if patch_node.tag != original_node.tag:
            raise Exception(
                'Patch failed, root tags differ: {} vs {}'.format(
                    original_node.tag,
                    patch_node.tag ))

        # Move over the children.
        original_node.extend(patch_node.getchildren())

    else:
        # Small convenience function for printing errors in various
        # conditions.
        def Print_Error(message):
            Transform_Log.Print(('Problem occured when handling diff '
                'node {}, xpath {}; skipping; error message: {}'
                ).format(
                    op_node.tag, xpath, message))
            
        # For patching purposes, to enable root replacement, nest
        # the original_node under a temporary parent, and then form
        # that into a tree (since '/...' style xpaths are absolute
        # paths, and only supported on a tree.
        temp_root = ET.Element('root')
        temp_root.append(original_node)
        temp_tree = ET.ElementTree(temp_root)
        
        # Work through the patch operation nodes.
        for op_node in patch_node.getchildren():                
            # Skip comments.
            if op_node.tag is ET.Comment:
                continue

            # Skip unexpected node types.
            if op_node.tag not in ['add','replace','remove']:
                Print_Error('node type {} not recognized'.format(op_node.tag))
                continue

            # All node types should have a 'sel' attribute with the
            # desired xpath.
            xpath = op_node.get('sel')
            if xpath == None:
                Print_Error('"sel" not found')
                continue

            # This gets a little messy here; the modification target
            # could be a node, a node attribute, or a node's text.
            # In any case, want to know the node itself being modified.
            # Do this by picking off of the 'sel' the piece that edits
            #  attributes or text, leaving just node selection.

            # Check for text edits.
            patch_text = False
            for suffix in ['/text()[1]', '/text()']:
                if xpath.endswith(suffix):
                    patch_text = True
                    xpath.replace(suffix, '')
                    break

            # Check for attribute edits.
            patch_attrib = False
            # These appear to be the only place an @ follows a /.
            if '/@' in xpath:
                if xpath.count('/@') != 1:
                    Print_Error('multiple "/@"')
                    continue
                xpath, attrib_name = xpath.rsplit('/@', 1)
                patch_attrib = True
                    

            # The remaining xpath should hopefully work.
            matched_nodes = temp_tree.findall(xpath)

            # On match failure, skip the operation similar to how
            # X4 would skip it.
            if not matched_nodes:
                Print_Error('no xpath match found')
                continue
                    
            # Only one node should be returned, as per diff patch reqs.
            if len(matched_nodes) > 1:
                Print_Error('multiple xpath matches found')
                continue

            # Convenience renaming.
            match_node = matched_nodes[0]
                
            if patch_text:
                if op_node.tag == 'add':
                    # This should never happen.
                    Print_Error('no handler for adding text')
                    continue

                if op_node.tag == 'remove':
                    # Unclear on how to handle this with lxml, but
                    # just set text to None.
                    match_node.text = None

                if op_node.tag == 'replace':
                    match_node.text = op_node.text

            elif patch_attrib:
                # Handle add and replace the same way.
                if op_node.tag in ('add', 'replace'):
                    # Error check.
                    if not op_node.text:
                        Print_Error('empty text value')
                        continue
                    match_node.set(attrib_name, op_node.text)

                if op_node.tag == 'remove':
                    # Check that the attrib is present, and remove it.
                    if match_node.get(attrib_name) != None:
                        match_node.attrib.pop(attrib_name)

            else:
                # Look up the parent node.
                parent = match_node.getparent()

                if op_node.tag == 'add':
                    # This could have a 'pos' attribute, which indicates
                    # adding a sibling instead of a child.
                    pos = op_node.get('pos')

                    if not pos:
                        # Move over the children (can be multiple).
                        match_node.extend(op_node.getchildren())

                    else:
                        # Find the index in the parent to insert at.
                        if pos == 'before':
                            index = parent.index(match_node)
                        elif pos == 'after':
                            index = parent.index(match_node) +1
                        else:
                            Print_Error('pos {} not understood'.format(pos))
                            continue
                        # Loop over children, inserting them from last
                        # to first.
                        for child in reversed(op_node.getchildren()):
                            # Note: copy the child nodes, to avoid multiple
                            # xml trees pointing at the same children.
                            parent.insert(index, deepcopy(child))

                if op_node.tag == 'remove':
                    # Remove from the parent.
                    # Note: the parent may be the top of the tree.
                    # TODO: check when happens when removing root.
                    parent.remove(match_node)
                    
                if op_node.tag == 'replace':
                    # Error check the op_node for the right children count.
                    if len(op_node.getchildren()) != 1:
                        Print_Error('0 or multiple children')
                        continue

                    # Similar to remove, but replace with the op_node
                    # child (should be just one).
                    replacement = deepcopy(op_node.getchildren()[0])
                    parent.replace(match_node, replacement)

        # Done with applying the patch.
        # Unpack the changed node from the temp root.
        replacement_node = temp_tree.getroot().getchildren()[0]
        # Quick verification tag is the same.
        assert replacement_node.tag == original_node.tag
        # Can now overwrite the original_node.
        original_node = replacement_node

    return original_node



def Make_Patch(original_node, modified_node, verify = True, maximal = True):
    '''
    Returns an xml diff node, suitable for converting from
    original_node to modified_node.

    * verify
      - Bool, if True the patch will verified, and an exception raised
        on apparent error.
    * maximal
      - Bool, if True then make a maximal diff patch, replacing the original
        root with the modified root.
      - Used for testing of other functions.
    '''
    if maximal:
        # Set up a diff node as root.
        patch_node = ET.Element('diff')

        # Replace the original root node, eg. <jobs>.
        # (TODO: would '/[0]' also work?)
        replace_node = ET.Element('replace')
        replace_node.set('sel', '/'+original_node.tag)
        # Copy the modified_node, else it leads to problems when multiple
        # xml nodes hold the same child.
        replace_node.append(deepcopy(modified_node))
        patch_node.append(replace_node)

    else:
        # Note: it is possible to do a non-diff patch if just adding nodes
        # to the original, but that case is almost as easy with a diff
        # patch and series of adds, so just always diff for now.
        # todo
        pass


    # Verify the patch appears to work okay.
    if verify and not Verify_Patch(original_node, modified_node, patch_node):
        raise Exception('XML patch generation failed')
    return patch_node


def Verify_Patch(original_node, modified_node, patch_node):
    '''
    Verify that the patch applied to the original recreates the modified
    xml node. Returns True on success, False on failure.
    '''
    # Copy the original, to do the patching without changing the input.
    original_node_patched = deepcopy(original_node)
    original_node_patched = Apply_Patch(original_node_patched, patch_node)

    # Easiest is just to convert both to strings, but it can be helpful
    # to break them up for line-by-line compare for debug.
    original_node_patched_lines = ET.tostring(
        original_node_patched, pretty_print = True).splitlines()
    modified_node_lines = ET.tostring(
        modified_node, pretty_print = True).splitlines()

    # Compare by line, out to the longest line list.
    success = True
    for line_number, (orig_line, mod_line) in enumerate(
            zip_longest(original_node_patched_lines, modified_node_lines)):

        if orig_line != mod_line:
            # If it was succesful up to this point, print a message.
            if success:
                print('Patch test failed on line {}; dumping xml.'.format(line_number))
                with open('test_original_node.xml', 'wb') as file:
                    file.write(ET.tostring(original_node, pretty_print = True))
                with open('test_modified_node.xml', 'wb') as file:
                    file.write(ET.tostring(modified_node, pretty_print = True))
                with open('test_patch_node.xml', 'wb') as file:
                    file.write(ET.tostring(patch_node, pretty_print = True))
                with open('test_original_node_patched.xml', 'wb') as file:
                    file.write(ET.tostring(original_node_patched, pretty_print = True))
                input('Press enter to continue testing.')
            # Flag as a failure.
            success = False

    return success



def Unit_Test(test_node, num_tests = 100, edits_per_test = 5, rand_seed = None):
    '''
    Performs a test of the diff patch code by making random edits
    to test_node and trying to patch them.
    Raises an exception on patch failure.

    * test_node
      - The xml node to play around with. Preferably not too large.
    * num_tests
      - Int, how many test edits to perform.
    * edits_per_test
      - Int, how many edits to make to the xml per test.
    * rand_seed
      - Int, optional, seed for the rng.
    '''
    if rand_seed != None:
        random.seed(rand_seed)
    assert isinstance(test_node, ET._Element)
    # List of possible edits to perform.
    test_combos = [ ]

    while num_tests > 0:
        num_tests -= 1

        # Copy the input node.
        # TODO: do something more efficient and full deepcopy.
        modified_node = deepcopy(test_node)

        # Get a flattened list of all nodes.
        node_list = modified_node.findall('.//')

        # Make a few edits.
        edits_remaining = edits_per_test
        # Put a limit on how many tries, in case there isn't enough xml
        # to do all the edits.
        tries_remaining = 100
        while edits_remaining > 0 and tries_remaining > 0:
            tries_remaining -= 1
            # edits_remaining gets decremented at the end, if the edit
            # attempted didn't get skipped.

            # Pick a random node to operate on.
            # Note: this could have been a child of some other node
            #  that was removed; that case should be okay, just means
            #  this edit won't be tested.
            edit_node = random.choice(node_list)
            
            # Pick an operation type.
            test_id = random.randint(0, 8)
            # (Debug pullout for viewing)
            #attrib = edit_node.attrib
            
            if test_id == 0:
                # Add attribute.
                edit_node.set(edit_node.tag, edit_node.tag)

            elif test_id == 1:
                # Add one or more nodes.
                # Can psuedo-randomize this by copying the node and
                # adding another set of its children to it.
                node_copy = deepcopy(edit_node)
                edit_node.extend(node_copy.getchildren())

            elif test_id == 2:
                # Remove text.
                edit_node.text = None

            elif test_id == 3:
                # Remove attribute.
                # If no attributes present, cannot remove any.
                try:
                    attrib_name = random.choice(edit_node.keys())
                except:
                    continue
                edit_node.attrib.pop(attrib_name)

            elif test_id == 4:
                # Remove node.
                parent = edit_node.getparent()
                parent.remove(edit_node)

            elif test_id == 5:
                # Replace text.
                edit_node.text = edit_node.tag

            elif test_id == 6:
                # Replace attribute, if any present.
                try:
                    attrib_name = random.choice(edit_node.keys())
                except:
                    continue
                edit_node.set(attrib_name, edit_node.tag)

            elif test_id == 7:
                # Replace node.
                # Randomize somewhat by replacing with a copy
                #  of its parent.
                parent = edit_node.getparent()
                parent_copy = deepcopy(parent)
                parent.replace(edit_node, parent_copy)
                
            # If here, an edit should have been performed.
            edits_remaining -= 1

        # Create a patch, turning on verification.
        test_patch = Make_Patch(test_node, modified_node, verify = True)

    return

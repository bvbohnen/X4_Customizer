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
'''
Note on patch generation approach:
    Handling of changes to attributes and text, if no nodes were
    added or removed, are straight forward.
    Node changes, however, rapidly become very complex to do well.

    For instance, if two nodes at the same depth have different
    children, then those child lists need to be matched up to
    determine which are the same subelement and which differ, but
    such comparisons get messy when a given subelement may be
    mostly the same but with a minor edit (eg. a nested attrib change).

    Getting a minimal patch from raw input xml is messy, and doesn't
    feel work doing.

    However, since the customizer had access to the original xml,
    and made the edits locally, it is possible to annotate all
    of the original nodes with a node_id, carry that into any
    modified copies, and then use node_id comparisons to guide
    the patching effort (knowing which nodes should be the same
    without worry about content differences).

    lxml uses low level elements that cannot have python attributes
    added, but they do off a 'sourceline' attribute that can be
    reused for this purpose.
    The original sourceline, filled during parsing, is not sufficient
    since multiple nodes could be declared on the same line.
    However, it can be overwritten with custom, unique node_id terms,
    and it will be carried through deepcopies into modified xml.

    To have uniqueness more globally, nodes can be tagged with
    their xml tree's object id along with a node offset, which
    should avoid confusion if comparing nodes that come from
    separate trees. Can use a tuple of (id(tree), node_index).

    Update: the sourcelines property has some funkiness going on
    when writing it (doing some <= comparison to an int), so it
    is unuseable for tuple writing.  Further, it does not allow
    values larger than an unsigned short (65k), nor does it
    allow values <= 0 (they get replaced with None).

    The only other halfway decent option is to overwrite the tail,
    which isn't expected to be in use for anything normally.
    In that case, printing will need to go through an intermediate
    function that clears out the tail id strings first.

    Refining this further:
        When the original nodes are given ids, and those are copied
        into the modified tree (for nice matching), any new nodes
        added to the modified tree will be id-less.

        To enable running matches, as a copy of the original_tree is
        patched to be more like the modified_tree, these new nodes
        will need their own unique ids.

        To get this, can rely on the python id() values: set all
        original nodes to have their id() as their tag; since the
        original_tree will continue to be live in memory, those ids
        can never be reused. So just before patching, the modified_tree
        can be visited to find all new nodes with no id, and fill it
        in with their id(), ensured to be unique.

        Update: another funkiness of lxml: with iterating over nodes
        in a tree, they appear to have only temporary python objects
        assigned, and as such during iteration id() values can
        be repeated. There doesn't appear to be a great fix for this;
        short of keeping a list of every node assigned an id.

        Though if needing a static tracker based solution, just
        as easy (why wasn't this used sooner...) is to have a global
        running id counter, that is sure to assign unique integer
        ids across all calls to id filling function.

'''
from lxml import etree as ET
from copy import deepcopy
from itertools import zip_longest
import random
import time # Used for some profiling.

from ..Common import Plugin_Log, Print
from ..Common.Exceptions import XML_Patch_Exception

# Statically track the number of node id values assigned, and just
# keep incrementing this.
_running_id = 0
def Fill_Node_IDs(xml_node):
    '''
    For all elements, fill their tail property with a unique integer
    node_id. Values remain unique throughput the python session.
    If an id string is already in the tail, it will be left unchanged.
    '''
    global _running_id
    # Loop over the nodes, including comments.
    for node in xml_node.iter():
        # If the tail is empty, fill it in.
        if not node.tail:
            node.tail = str(_running_id)
            _running_id += 1
    return xml_node


def Print(xml_node, **kwargs):
    '''
    Returns the prettyprinted string for the xml_node.
    Handles suppression of the node_id strings.
    Any kwargs are passed to ET.tostring.
    '''
    # Back up all tails, and clear them.
    node_id_dict = {}
    for node in xml_node.iter():
        node_id_dict[node] = node.tail
        node.tail = None
    # Print.
    text = ET.tostring(xml_node, pretty_print = True, **kwargs)
    # Put tails back.
    for node, tail in node_id_dict.items():
        node.tail = tail
    return text


def Apply_Patch(original_node, patch_node, error_prefix = None):
    '''
    Apply a diff patch to the target xml node.
    Returns the modified node, possibly a changed-in-place original_node
    but maybe a complete replacement.

    If the patch_node is a 'diff', performs diff patching.
    Otherwise the patch_node must have the same tag as original_node,
    and its children will be appended to this original_node's children.

    * error_prefix
      - Optional string, a prefix to put before any error messages.
      - Can be used to indicate the sources for the xml nodes.
    '''
    # Requires elements as inputs.
    assert isinstance(original_node, ET._Element)
    assert isinstance(patch_node, ET._Element)

    # Preprocess the error_prefix real quick.
    error_prefix = '' if not error_prefix else '({}) '.format(error_prefix)
    
    if patch_node.tag != 'diff':
        # Error check for tag mismatch.
        if patch_node.tag != original_node.tag:
            raise AssertionError(
                '{}Error: Root tags differ: {} vs {}; skipping patch'.format(
                    error_prefix,
                    original_node.tag,
                    patch_node.tag ))

        # Move over the children.
        original_node.extend(patch_node.getchildren())

        # TODO: maybe do error detection on adding a node with
        # an "id" attribute that matches an existing node, since
        # x4 prints such errors in some cases (maybe all?).
        # Would need to see if it can be done blindly for all files.

    else:
        # Small convenience function for printing errors in various
        # conditions.
        # TODO: note which extensions the files come from.
        def Print_Error(message):
            Plugin_Log.Print(('{}Error: Problem occured when handling diff '
                'node "{}" on line {}, xpath "{}"; skipping; error message: {}.'
                ).format(
                    error_prefix,
                    op_node.tag, op_node.sourceline, 
                    xpath, message))
            
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

            # Determine the type of the top, text/attrib/node change.
            # Can do this while isolating the xpath.
            type = 'node'

            # Check for text edits.
            for suffix in ['/text()[1]', '/text()']:
                if xpath.endswith(suffix):
                    type = 'text'
                    xpath = xpath.replace(suffix, '')

            # Check for attribute edits.
            # These either end the xpath with '/@<name>' for remove/replace,
            #  or have a 'type' property for adding.
            if '/@' in xpath:
                type = 'attrib'

                if xpath.count('/@') != 1:
                    Print_Error('multiple "/@"')
                    continue
                # Pull off the /@; it is diff funkiness and not part of
                #  a valid xpath.
                xpath, attrib_name = xpath.rsplit('/@', 1)

                # To ensure the xpath lookup still fails if the attrib
                #  is missing, put it back on the xpath using [@...]
                #  syntax.
                #xpath += '[@{}]'.format(attrib_name)
                # -Removed for now; x4 seems inconsistent on if this should
                #  give an error when replacing an attribute that doesn't
                #  exist.
                # Example:
                #  Fails in x4:
                #    turret_arg_m_mining_01_mk1_macro.xml:
                #    <replace sel="//macros/macro/properties/hull/@max">2500</replace>
                #  Succeeds in x4:
                #    bullet_par_m_railgun_01_mk1_macro.xml:
                #    <replace sel="//macros/macro/properties/bullet/@angle">0.2</replace>
                # Both lack this attribute in the base file.
                # Most commonly, x4 seems to allow missing attributes
                # TODO: revisit to sync up with x4 errors better.

            elif op_node.get('type'):
                type = 'attrib'

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

            # Apply the patch op.
            error_message = _Apply_Patch_Op(op_node, matched_nodes[0], type)
            # Print an error if it occurred.
            if error_message:
                Print_Error(error_message)
                

        # Done with applying the patch.
        # Unpack the changed node from the temp root.
        replacement_node = temp_tree.getroot().getchildren()[0]
        # Quick verification tag is the same.
        assert replacement_node.tag == original_node.tag
        # Can now overwrite the original_node.
        original_node = replacement_node

    return original_node



def _Apply_Patch_Op(op_node, target_node, type):
    '''
    Apply a diff patch operation (add/remove/replace) on the target node.
    Returns any error message, else None on success.
    '''
    if type == 'text':
        if op_node.tag == 'add':
            # This should never happen.
            return 'no handler for adding text'

        if op_node.tag == 'remove':
            # Unclear on how to handle this with lxml, but
            # just set text to None.
            target_node.text = None

        if op_node.tag == 'replace':
            target_node.text = op_node.text

    elif type == 'attrib':
        # Grab the attribute name out of the xpath for remove/replace,
        # or out the 'type' property for add.
        if op_node.tag == 'add':
            attrib_name = op_node.get('type').replace('@','')
        else:
            xpath = op_node.get('sel')
            attrib_name = xpath.rsplit('/@', 1)[1]

        # Handle add and replace the same way.
        if op_node.tag in ('add', 'replace'):
            # Error check.
            if not op_node.text:
                return 'empty text value'
            target_node.set(attrib_name, op_node.text)

        if op_node.tag == 'remove':
            # Check that the attrib is present, and remove it.
            if target_node.get(attrib_name) != None:
                target_node.attrib.pop(attrib_name)

    else:
        # Look up the parent node.
        parent = target_node.getparent()

        if op_node.tag == 'add':
            # This could have a 'pos' attribute, changing the exact
            # insert location.
            pos = op_node.get('pos')
            # Copy children for safety (avoid node confusion between
            #  xml trees).
            op_node_children = deepcopy(op_node.getchildren())

            if pos == None:
                # Move over the children (can be multiple).
                target_node.extend(op_node_children)

            elif pos == 'prepend':
                # Move over the children, but put at the start.
                # Use an insert loop for this, in reverse order (so
                #  the first child is the last inserted at 0, leaving
                #  it first in target_node).
                for child in reversed(op_node_children):
                    target_node.insert(0, child)

            elif pos == 'before':
                # Add nodes as siblings to the target, before it.
                # Loop on children, forward, so the last child is
                #  closest to the target_node.
                for child in op_node_children:
                    target_node.addprevious(child)

            elif pos == 'after':
                # As above, but loop in reverse and place children after
                #  the target, so that the first child is closest to
                #  the target.
                for child in reversed(op_node_children):
                    target_node.addnext(child)
            else:
                return 'pos {} not understood'.format(pos)

        if op_node.tag == 'remove':
            # Remove from the parent.
            # Note: the parent may be the top of the tree.
            # TODO: check when happens when removing root.
            parent.remove(target_node)
                    
        if op_node.tag == 'replace':
            # Error check the op_node for the right children count.
            if len(op_node.getchildren()) != 1:
                return '0 or multiple children'

            # Similar to remove, but replace with the op_node
            # child (should be just one).
            # Copy for safety.
            op_node_child = deepcopy(op_node.getchildren()[0])
            parent.replace(target_node, op_node_child)

    return


def Make_Patch(original_node, modified_node, verify = True, maximal = True):
    '''
    Returns an xml diff node, suitable for converting from
    original_node to modified_node. Expects Fill_Node_IDs
    to have been run on the original_node, and node_ids to have
    been originally carried into modified_node.

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
        replace_node.append(modified_node)
        patch_node.append(replace_node)

    else:
        # Note: it is possible to do a non-diff patch if just adding nodes
        #  to the original, but that case is almost as easy with a diff
        #  patch and series of adds, so just always diff for now.
        
        # Make a copy of the original.
        # To make xpath generation easier/robust, as patches are generated
        #  the (copied) original xml will be edited with the changes, so
        #  that they are reflected in following xpaths.
        original_copy = deepcopy(original_node)
        
        # Ensure the modified_node is fully filled in with node ids,
        #  since they are important when the nodes get inserted into
        #  the original_copy. (New nodes added since it was forked
        #  from the original would otherwise have no id.)
        Fill_Node_IDs(modified_node)

        # Get a list of op elements.
        patch_op_list = _Get_Patch_Ops_Recursive(original_copy, modified_node)

        # Construct the diff patch with these as children.
        patch_node = ET.Element('diff')
        patch_node.extend(patch_op_list)

    # Verify the patch appears to work okay.
    if verify and not Verify_Patch(original_node, modified_node, patch_node):
        raise XML_Patch_Exception('XML generated patch verification failed')
    return patch_node


def _Patch_Node_Constructor(
        op,
        type,
        target,
        name         = None,
        value        = None,
        pos          = None
    ):
    '''
    Small support function for creating patch operation.
    Returns a single Element.
    The patch operation is applied automatically to the target node.

    * op
      - String, one of ['add','remove','replace'].
    * type
      - String, one of ['text','attrib','node'].
    * target
      - The node being edited (added to, removed, or replaced).
    * name
      - For 'attrib', the attribute name being changed.
    * value
      - For 'attrib' and 'text', the new value to use (string).
      - For 'node', a list of elements to add or replace with.
    * pos
      - For 'node'/'add', the 'pos' value to use.
      - One of ['prepend','before','after'].
    '''
    # Start with the base xpath.
    xpath = _Get_Xpath_Recursive(target)

    # Suffix for attrib or text.
    if type == 'text':
        # Expect this to always target the normal text, which is
        # apparently offset 1. Other offsets might include tail
        # or similar.
        xpath += '/text()[1]'
    elif type == 'attrib' and op != 'add':
        # Target the attribute's name.
        xpath += '/@' + name

    # Create the initial node, where op is the tag.
    op_node = ET.Element(op, attrib = {'sel': xpath})

    # When adding attributes, need to use the 'type' node property
    #  to provide the attribute name.
    if type == 'attrib' and op == 'add':
        op_node.set('type', '@'+name)

    # Add another attribute for the insertion index if needed.
    if pos != None:
        op_node.set('pos', pos)

    # Handle value add/replace.
    if value != None:
        # Nodes are added as children.
        if type == 'node':
            if isinstance(value, (list, tuple)):
                op_node.extend(value)
            else:
                op_node.append(value)
        # Test and attributes go into the text field.
        else:
            op_node.text = value

    # Run this patch on the original xml node to keep it updated.
    error_message = _Apply_Patch_Op(op_node, target, type)
    if error_message:
        raise XML_Patch_Exception('Patch generation error, message: {}'.format(
            error_message))
    return op_node


def _Get_Patch_Ops_Recursive(original_node, modified_node):
    '''
    Recursive function which will return a list of patch operation elements
    to convert from the original_node to the modified_node.
    Returns a list of elements (add, remove, or replace).
    Input nodes are expected to have the same tail property.
    The original_node will be edited according to the patch op as this
    progresses, to ensure xpaths update accordingly mid patching.
    '''
    # As a rule, the inputs will have the same tail, and
    # the recursive function will only be called when this is true.
    assert original_node.tail == modified_node.tail

    patch_nodes = []

    # Look for attribute changes.
    # Search the original node attributes to find removals and replacements.
    attrib_ops = []
    for name, value in original_node.items():

        if name not in modified_node.keys():
            # Attribute was removed.
            patch_nodes.append(_Patch_Node_Constructor(
                op     = 'remove', type = 'attrib',
                target = original_node,
                name   = name))            

        elif value != modified_node.get(name):
            # Attribute was changed.
            patch_nodes.append(_Patch_Node_Constructor(
                op     = 'replace', type = 'attrib',
                target = original_node,
                name   = name,
                value  = modified_node.get(name) ))

    # Search the modified_node for additions.
    for name, value in modified_node.items():
        if name not in original_node.keys():
            # Attribute was added.
            patch_nodes.append(_Patch_Node_Constructor(
                op     = 'add', type = 'attrib',
                target = original_node,
                name   = name,
                value  = modified_node.get(name) ))
            

    # Look for text changes.
    if original_node.text != None and modified_node.text == None:
        # Text removed.
        patch_nodes.append(_Patch_Node_Constructor(
            op     = 'remove', type = 'text',
            target = original_node ))
        
    elif original_node.text != modified_node.text:
        # Text added or changed; both will use a replace.
        patch_nodes.append(_Patch_Node_Constructor(
            op     = 'replace', type = 'text',
            target = original_node,
            value  = modified_node.text ))


    # Look for child node changes.
    # The approach will be to use a running walk between both child
    #  lists, matching up node ids; when there is a mismatch, can
    #  check if one side's node is present in the other side's list,
    #  indicating what happened (add or remove).
    # Each time a patch is made, the original_node will be updated with
    #  the change, meaning this search can be restarted and will make
    #  it at least one step further. Enough loops will get through it.

    # Loop until the original_node children stop being modified.
    # When all loops are done, children lists will match.
    change_occurred = True
    while change_occurred:
        change_occurred = False

        # Loop through both children lists; keep going if one of them ends.
        for orig_child, mod_child in zip_longest(
                                        original_node.getchildren(),
                                        modified_node.getchildren()):

            # If there are no more orig_child nodes, then the mod_child
            #  was appended.
            if orig_child == None:
                patch_nodes.append(_Patch_Node_Constructor(
                    op     = 'add', type = 'node',
                    # Append to the end of the original_node.
                    target = original_node,
                    # Be sure to copy this to avoid xml node confusion,
                    # since this gets put in the patch tree.
                    value  = deepcopy(mod_child) ))
                change_occurred = True
                break
            
            # If ther are no more mod_child nodes, then the orig_child
            #  was removed.
            if mod_child == None:
                patch_nodes.append(_Patch_Node_Constructor(
                    op     = 'remove', type = 'node',
                    target = orig_child ))
                change_occurred = True
                break


            # Something went wrong if both have None for node ids.
            if orig_child.tail == None and mod_child.tail == None:
                raise XML_Patch_Exception('node ids not filled in well enough')


            # Check for a difference.
            if orig_child.tail != mod_child.tail:

                # Want to know what happened.
                # Check if the mod_child is elsewhere in the original.
                mod_child_in_orig = any(mod_child.tail == x.tail 
                                        for x in original_node.getchildren())
                # Check if the orig_child is elsewhere in the child.
                orig_child_in_mod = any(orig_child.tail == x.tail 
                                        for x in modified_node.getchildren())

                if mod_child_in_orig == True and orig_child_in_mod == False:
                    # This case suggests a node was removed.
                    patch_nodes.append(_Patch_Node_Constructor(
                        op     = 'remove', type = 'node',
                        target = orig_child ))
                    change_occurred = True
                    break
            
                elif mod_child_in_orig == False and orig_child_in_mod == True:
                    # This case suggests a node was added.
                    patch_nodes.append(_Patch_Node_Constructor(
                        op     = 'add', type = 'node',
                        # Insert after the original.
                        target = orig_child,
                        pos = 'after',
                        value  = deepcopy(mod_child) ))
                    change_occurred = True
                    break

                elif mod_child_in_orig == False and orig_child_in_mod == False:
                    # Neither node is in the other; can handle this with
                    #  a replacement.
                    patch_nodes.append(_Patch_Node_Constructor(
                        op     = 'replace', type = 'node',
                        target = orig_child,
                        value  = deepcopy(mod_child) ))
                    change_occurred = True
                    break

                else:
                    # Something weird happened; nodes somehow got reordered.
                    # There is no diff operation for reordering, so as a backup
                    # just delete the original node (later passes will put it
                    # back in later in the list).
                    patch_nodes.append(_Patch_Node_Constructor(
                        op     = 'remove', type = 'node',
                        target = orig_child ))
                    change_occurred = True
                    break

            # If here, then the nodes appear to be the same, superficially.
            # Still need to handle deeper changes, so recurse and pick out
            #  lower level patches.
            patch_nodes += _Get_Patch_Ops_Recursive(orig_child, mod_child)

    return patch_nodes


def _Get_Xpath_Recursive(node):
    '''
    Construct and return an xpath to select the given node.
    Recursively gets called on parent nodes, using their xpaths
    as prefixes.
    '''
    # If there is no parent then this is the top node, but still needs
    #  to include itself since X4 has a fake node above it.
    parent = node.getparent()
    if parent == None:
        return '/{}'.format(node.tag)

    # Initially, this can just use child indexing to work through the
    #  whole tree.
    # Note: it was discovered that lxml experiences drastic slowdown
    #  when dealing with indexed xpaths, suggesting it can only omit
    #  deadends on attributes or child tags, not on bad indexes,
    #  hence a bit of a rubbish implementation in this aspect.
    # So, it is extremely important that this xpath creator use
    #  attributes to clarify searches whenever possible.

    # TODO: swap over to node tag and some attributes when they
    #  are sufficient for unique lookup, either within a child list
    #  or globally (with a prefix '//' to shorten the path).

    # The xpath is just the path to the parent, combined with the tag
    #  of the child node and its attributes, and the index among 
    #  nodes with that tag and attributes (as a backup).
    # To reduce fluff, a first check will just use the tag, and if
    #  there are multiple matches, a loop will add attributes iteratively
    #  until a single node matches.
    # (This could just start with all attributes, but they are often
    #  not needed and clutter up the output diff patch.)
    xpath = node.tag
    # Get elements with the same tag.
    similar_tag_elements = parent.findall(xpath)
    # Store this into a temp var; want to use the same-tag version later.
    similar_elements = similar_tag_elements
    # Loop while there is more than 1 similar element (want just self).
    if len(similar_elements) > 1:
        # Add attributes.
        for key, value in node.items():
            # Note: the xpath will itself be an attribute in double
            # quotes, so to avoid nested double quotes (which get
            # output as &quot; in the xml, which xpath then can't
            # deal with reliably), just use single quotes for this
            # inner term.
            xpath += '''[@{}='{}']'''.format(key, value)
            # Check element matches again.
            similar_elements = parent.findall(xpath)
            # If just one match, done.
            if len(similar_elements):
                break

    # Verify this node was matched with the current xpath.
    assert len(similar_elements) >= 1


    # Flesh out the xpath with the parent prefix.
    xpath = _Get_Xpath_Recursive(parent) + '/' + xpath

    # If there were multiple element matches, add a suffix.
    # Note: the xpath index is relative to other nodes with the same tag,
    #  ignoring attributes.
    if len(similar_elements) > 1:
        # Get the index of this node relative to other same-tag nodes.
        # Note: xpath is 1-based indexing.
        index = similar_tag_elements.index(node) + 1
        xpath += '[{}]'.format(index)

    return xpath


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
    original_node_patched_lines = Print(original_node_patched, encoding = 'unicode').splitlines()
    modified_node_lines         = Print(modified_node        , encoding = 'unicode').splitlines()

    # Compare by line, out to the longest line list.
    success = True
    for line_number, (patched_line, mod_line) in enumerate(
            zip_longest(original_node_patched_lines, modified_node_lines)):

        if patched_line != mod_line:
            # If it was succesful up to this point, print a message.
            if success:
                Print('Patch test failed on line {}.'.format(line_number))
                # For checking, dump all of the xml to files.
                # This is mainly intended for use by the unit test.
                # TODO: attach to an input arg.
                if 1:
                    with open('test_original_node.xml', 'w') as file:
                        file.write(Print(original_node, encoding = 'unicode'))
                    with open('test_modified_node.xml', 'w') as file:
                        file.write(Print(modified_node, encoding = 'unicode'))
                    with open('test_patch_node.xml', 'w') as file:
                        file.write(Print(patch_node, encoding = 'unicode'))
                    with open('test_original_node_patched.xml', 'w') as file:
                        file.write(Print(original_node_patched, encoding = 'unicode'))
                    # Pause; allow time to peek at files or ctrl-C.
                    input('Press enter to continue testing.')
                    
            # Flag as a failure.
            success = False
            break
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
    # Make sure the input is annotated with node ids.
    Fill_Node_IDs(test_node)

    test_number = 0
    while test_number < num_tests:
        test_number += 1

        # Copy the test node, for a modifiable copy.
        modified_node = deepcopy(test_node)

        # Get a flattened list of all non-comment nodes.
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
                except Exception:
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
                except Exception:
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
        try:
            test_patch = Make_Patch(
                test_node, 
                modified_node, 
                maximal = False,
                verify = True)
            Print('Test {} passed'.format(test_number))
        except XML_Patch_Exception as ex:
            Print('Test {} failed; message: {}'.format(test_number, ex))
    return

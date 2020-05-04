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

    Update: when an lxml element is appended to using addnext(),
    it transfers its tail to the appended element, breaking node ids.
    TODO: think of a workaround. For now, disallow addnext().
    (TODO: think of how to disallow addnext.)

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
'''
Note on lxml and xpath bugginess:
    When using indexed lookups (/a/b[5]), lxml tends to bog down
    horribly in larger files.  For the wares file, it was 1/1000 speed.

    Further, lxml evaluates expressions with a parameter and an index
    incorrectly when using find or findall.
    Example:
        /a/b[@c="d"][5]

        By the xpath docs, this should be the 5th child of 'a' that
        is of tag 'b' and has attribute 'c=d'.

        lxml gets this wrong, and looks for a child of 'a' that is
        the 5th child and also has attribue 'c=d'.

    In the python docs, buried toward the end of the xpath section,
    is this: "position predicates must be preceded by a tag name".
    lxml copies this behavior.

    However, lxml also has an 'xpath' method that will act like findall
    except with correct evaluation. Use that always.
'''
'''
Note on namespaces:
    In short, they are a mess.
    Original xml uses namespace prefixes on eg. attribute names, eg. "xsi:bla".
    Lxml replaces these with the namespace base, eg. "{stuff}bla".
    Xpath applied to original xml needs to use the prefixed version.
    Xpath applied to the lxml nodes needs to use the expanded version.

    For now, this code will mostly punt on namespaces, outside of changing
    basic attributes, eg. the schema path in the root node.
'''
from lxml import etree as ET
from copy import deepcopy
from itertools import zip_longest
import random
import time # Used for some profiling.

from ..Common import Plugin_Log
from ..Common import Print as Print_Log
from ..Common.Exceptions import XML_Patch_Exception


# Note: multiprocessing is used to speed up ware parsing,
# but it doesn't work as-is with lxml because multiprocessing wants to pickle
# the elements to copy between threads, which lxml does not support.
# The copyreg package can be used to define pickling/depickling functions
# for arbitrary objects, and will pipe xml to/from a string.
import copyreg

def LXML_Element_Pickler(element):
    'Pickle an lxml element.'
    xml_string = ET.tostring(element, encoding = 'unicode')
    # Return format is a little funky; based on documentation.
    return LXML_Element_Depickler, (xml_string,)

def LXML_Element_Depickler(xml_string):
    'Depickle an lxml element.'
    # Note: the node ids were attached to tails, but lxml bugs up
    #  when parsing a top element that has a tail.
    # As a workaround, manually remove the tail text, and reapply
    #  it at the end. It needs to be preserved since the copied
    #  node may be from inside a tree.
    xml_bulk, tail = xml_string.rsplit('>',1)
    xml_bulk += '>'
    element = ET.fromstring(xml_bulk)
    element.tail = tail
    return element

# Set up the pickler with copyreg.
copyreg.pickle(ET._Element, LXML_Element_Pickler, LXML_Element_Depickler)


# Statically track the number of node id values assigned, and just
# keep incrementing this.
_running_id = 0
def Fill_Node_IDs(xml_node):
    '''
    For all elements, fill their tail property with a unique integer
    node_id. Values remain unique throughput the python session.
    Ids are unique across xml documents annotated.
    If an id string is already in the tail, it will be left unchanged,
    so it should be safe to call this on already annotated xml to
    fill out ids for new nodes.
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


# Fixed namespaces; assume unchanged.
namespaces = {'xsi':'http://www.w3.org/2001/XMLSchema-instance'}
# Version of the above representing how the terms appear in code.
# Keys are followed by a colon, values enclosed in braces.
namespaces_lxml = { k+':' : '{'+v+'}' for k,v in namespaces.items()}

def Is_NS_Attribute(term):
    'Returns True if this lxml attribute uses a namespace.'
    return any(x in term for x in namespaces_lxml.values())

def NS_unqualify(term):
    '''
    Unqualify (eg. re-encode) namespaces in the term, since the normal
    xpath() search function cannot handle qualified names.
    '''
    for k, v in namespaces_lxml.items():
        term = term.replace(v, k)
    return term

def NS_qualify(term):
    '''
    Qualify a name using namespace replacement (eg. expand it), suitable
    for use with lxml attributes.
    '''
    for k, v in namespaces_lxml.items():
        term = term.replace(k, v)
    return term

def NS_xpath(node, xpath):
    '''
    Returns result of an xpath() lookup on the given node, after unqualifying
    the provided xpath string.
    '''
    return node.xpath(NS_unqualify(xpath), namespaces=namespaces)


def Apply_Patch(original_node, patch_node, error_prefix = None):
    '''
    Apply a diff patch to the target xml node.
    Returns the modified node, a changed-in-place original_node, or
    possibly a fully replaced original_node.

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
            # Side note: this was observed with a bad t/0001.xml diff
            # patch attempt on a file that doesn't exist from some
            # satellite mod. (Normally x4 won't load non-existent files
            # since it has no reference to them, but the extension
            # checker here will try it.)
            Plugin_Log.Print(
                '{}Error: Root tags differ: {} vs {}; skipping patch'.format(
                    error_prefix,
                    original_node.tag,
                    patch_node.tag ))
            return original_node

        # Move over the children.
        original_node.extend(patch_node.getchildren())

        # TODO: maybe do error detection on adding a node with
        # an "id" or "name" attribute that matches an existing node, since
        # x4 prints such errors in some cases (maybe all?).
        # Would need to see if it can be done blindly for all files,
        # or if it should be specialized to macros/components/wares/etc.

    else:
        # Small convenience function for printing errors in various
        # conditions.
        # TODO: note which extensions the files come from.
        # TODO: maybe respect a "silent" attribute to suppress errors,
        #  or maybe just suppress when checking extensions (done elsewhere).
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
            # Note: the xpath search can continue past the ref,
            #  eg. "@ref[.='scenario_combat_arg_destroyer']" in split dlc,
            #  so for replacements the full path needs to be kept.
            if '/@' in xpath:
                type = 'attrib'
                if xpath.count('/@') != 1:
                    Print_Error('multiple "/@"')
                    continue

            # Check for attribute additions.
            # These have a normal xpath, with a 'type' member holding
            #  the attribute name prefixed with @, eg. type="@id".
            elif op_node.get('type'):
                type = 'attrib'

            # The remaining xpath should hopefully work.
            # Note: when switching from findall to xpath(), a
            # prefixed '.' was needed to get this to work.
            # Note: if the xpath is malformed, this will throw an exception.
            # Note: this will support namespacing the xpath to some extent,
            # just to enable modifying the schema path.
            try:
                matched_nodes = NS_xpath(temp_tree, '.' + xpath)
            except Exception as ex:
                Print_Error('xpath exception: {}'.format(ex))
                continue

            # On match failure, skip the operation similar to how
            # X4 would skip it.
            if not matched_nodes:
                Print_Error('no xpath match found')
                continue
                    
            # Only one node should be returned, as per diff patch reqs.
            if len(matched_nodes) > 1:
                Print_Error('multiple xpath matches found')
                continue

            # If a string attribute was returned (which happens for
            # attribute replacement paths), get the parent node.
            matched_node = matched_nodes[0]
            if isinstance(matched_node, ET._ElementUnicodeResult):
                matched_node = matched_node.getparent()

            # Apply the patch op.
            error_message = _Apply_Patch_Op(op_node, matched_node, type)
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
            # There may be more xpath stuff after the actual wanted name,
            # eg. "/@ref[.='scenario_combat_arg_destroyer']".
            # TODO: full xml syntax to figure out the name.
            # For now, just tackle the above situation.
            if '[' in attrib_name:
                attrib_name = attrib_name.split('[')[0]

        # Qualify the attribute name based on namespaces in the target node.
        # TODO: maybe remove if dropping namespace support.
        attrib_name = NS_qualify(attrib_name)

        # Handle add and replace the same way.
        if op_node.tag in ('add', 'replace'):
            assert op_node.text != None
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
                    # Note: lxml might move tails when using addnext.
                    # Fix them here.
                    target_tail = target_node.tail
                    child_tail = child.tail
                    target_node.addnext(child)
                    target_node.tail = target_tail
                    child.tail = child_tail
            else:
                return 'pos {} not understood'.format(pos)

        if op_node.tag == 'remove':
            # Remove from the parent.
            parent.remove(target_node)
                    
        if op_node.tag == 'replace':
            # Essentially a mix of remove and add, replacing with the
            # op_node children (can be multiple).

            # Copy children for safety.
            op_node_children = deepcopy(op_node.getchildren())

            # Need to insert one child at a time, at the right location.
            # Do this before removing the target node, so these can
            # be inserted before it.
            for child in op_node_children:
                target_node.addprevious(child)
            # Can now remove the target.
            parent.remove(target_node)

    return

# Global holding the list of forced attributes.
# Put here to avoid passing in function calls, due to so many calls.
forced_attributes = None

def Make_Patch(
    original_node,
    modified_node, 
    forced_attributes = None,
    verify = True, 
    maximal = True
   ):
    '''
    Returns an xml diff node, suitable for converting from
    original_node to modified_node. Expects Fill_Node_IDs
    to have been run on the original_node, and node_ids to have
    been originally carried into modified_node.

    * forced_attributes
      - String or list of strings, optional, list of attributes (comma
        separated if string) which will always be included in the xpath
        for elements which have them.
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
        # Set up a config dict.
        # This was added just for holding forced_attributes in a slightly
        # cleaner way. Short name for easier passing (since passes often).
        cfg = {
            'forced_attributes' : [],
            }

        # Break up forced attributes strings into a list.
        if forced_attributes and isinstance(forced_attributes, str):
            cfg['forced_attributes'] = forced_attributes.split(',')
        # Lists and tuples pass through normally.
        elif isinstance(forced_attributes, (list, tuple)):
            cfg['forced_attributes'] = forced_attributes

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
        # Prune out Nones.
        patch_op_list = _Get_Patch_Ops_Recursive(original_copy, modified_node, cfg)

        # Construct the diff patch with these as children.
        patch_node = ET.Element('diff')
        patch_node.extend([x for x in patch_op_list if x != None])

    # Verify the patch appears to work okay.
    if verify and not Verify_Patch(original_node, modified_node, patch_node):
        raise XML_Patch_Exception('XML generated patch verification failed')
    return patch_node


def _Patch_Node_Constructor(
        op,
        type,
        target,
        cfg,
        name         = None,
        value        = None,
        pos          = None,
    ):
    '''
    Small support function for creating patch operation.
    Returns a single Element, or None if the patch is rejected
    due to namespace usage.
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
    xpath = _Get_Xpath_Recursive(target, cfg)

    # Test: trim the xpath down with // syntax as much as can be
    # done. This code will be a little messy, since throwaway
    # added to test loading times.
    # Note on test results: 35s load time with maximal diffs,
    # 36s with full xpaths, 39s with these shortened xpaths,
    # so never use this in practice. (With test xpaths mostly
    # coming from adjusting ware price spread.)
    if 0:
        top_node = target
        while top_node.getparent() != None:
            top_node = top_node.getparent()
        # Start picking off xpath terms, left to right.
        new_xpath = xpath
        while 1:
            # Stop if there are no extra tags.
            if '/' not in new_xpath:
                break
            # Pick off the first term
            throwaway, test_xpath = new_xpath.split('/',1)
            # Test it, with a preceeding //.
            test_nodes = top_node.xpath('//' + test_xpath)
            # If
            if len(test_nodes) == 1 and test_nodes[0] is target:
                #print('shortened to {}'.format(test_xpath))
                new_xpath = test_xpath
            else:
                break
        # If it was truncated, put the '//' prefix on and overwrite
        # the original xpath.
        if new_xpath != xpath:
            xpath = '//' + new_xpath
            #print('final path: {}'.format(xpath))

    # Suffix for attrib or text.
    if type == 'text':
        # Expect this to always target the normal text, which is
        # apparently offset 1. Other offsets might include tail
        # or similar.
        xpath += '/text()[1]'

    elif type == 'attrib' and op != 'add':
        # Target the attribute's name.
        # Note: x4 cannot handle namespaced attributes: if given the
        # qualified name, it chokes on the xpath; if given the unqualified
        # name (with prefix), it replaces it with the qualified name
        # and chokes anyway.
        # As such, if this attribute is one of the namespace ones, just
        # skip this whole patch.
        if Is_NS_Attribute(name):
            return

        #name = NS_unqualify(name)
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

        # Text and attributes go into the text field.
        else:
            op_node.text = value

    # Run this patch on the original xml node to keep it updated.
    error_message = _Apply_Patch_Op(op_node, target, type)
    if error_message:
        raise XML_Patch_Exception('Patch generation error, message: {}'.format(
            error_message))
    return op_node


def _Get_Patch_Ops_Recursive(original_node, modified_node, cfg):
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
                name   = name,
                cfg    = cfg))            

        elif value != modified_node.get(name):
            # Attribute was changed.
            patch_nodes.append(_Patch_Node_Constructor(
                op     = 'replace', type = 'attrib',
                target = original_node,
                name   = name,
                value  = modified_node.get(name),
                cfg    = cfg ))

    # Search the modified_node for additions.
    for name, value in modified_node.items():
        if name not in original_node.keys():
            # Attribute was added.
            patch_nodes.append(_Patch_Node_Constructor(
                op     = 'add', type = 'attrib',
                target = original_node,
                name   = name,
                value  = modified_node.get(name),
                cfg    = cfg ))
            

    # Look for text changes.
    if original_node.text != None and modified_node.text == None:
        # Don't expect this for comments.
        assert not modified_node.tag is ET.Comment
        # Text removed.
        patch_nodes.append(_Patch_Node_Constructor(
            op     = 'remove', type = 'text',
            target = original_node,
            cfg    = cfg ))
        
    elif original_node.text != modified_node.text:
        # This should have been handled earlier for comments.
        assert not modified_node.tag is ET.Comment
        # Text added or changed; both will use a replace.
        patch_nodes.append(_Patch_Node_Constructor(
            op     = 'replace', type = 'text',
            target = original_node,
            value  = modified_node.text,
            cfg    = cfg ))


    # Look for child node changes.
    # The approach will be to use a running walk between both child
    #  lists, matching up node ids; when there is a mismatch, can
    #  check if one side's node is present in the other side's list,
    #  indicating what happened (add or remove).
    # Each time a patch is made, the original_node will be updated with
    #  the change, meaning this search can be restarted and will make
    #  it at least one step further. Enough loops will get through it.
    # Note: full recursions that go through the child lists again from
    #  start will be slow, particularly for large lists (eg. wares),
    #  so the below code is designed to do all updates in one pass.

    # Grab the child lists.
    orig_children = [x for x in original_node.iterchildren()]
    mod_children  = [x for x in modified_node.iterchildren()]
        
    # Loop while nodes remain in both lists.
    # Once one runs out, there are no more matches.
    while orig_children or mod_children:
            
        # Sample elements from both lists; don't remove yet.
        orig_child = orig_children[0] if orig_children else None
        mod_child  = mod_children[0]  if mod_children  else None
        

        # If there are no more orig_child nodes, then the mod_child
        #  was appended.
        if orig_child == None:
            patch_nodes.append(_Patch_Node_Constructor(
                op     = 'add', type = 'node',
                # Append to the end of the original_node.
                target = original_node,
                # Be sure to copy this to avoid xml node confusion,
                # since this gets put in the patch tree.
                # Note: this copies over the node id, so the patched
                # orig child will now match at this position.
                value  = deepcopy(mod_child),
                cfg    = cfg ))

            mod_children.remove(mod_child)
            continue
            
        # If there are no more mod_child nodes, then the orig_child
        #  was removed.
        if mod_child == None:
            # Remove from the original node.
            patch_nodes.append(_Patch_Node_Constructor(
                op     = 'remove', type = 'node',
                target = orig_child,
                cfg    = cfg ))
            
            orig_children.remove(orig_child)
            continue
            
        # Something went wrong if both have None for node ids.
        if orig_child.tail == None and mod_child.tail == None:
            raise XML_Patch_Exception('node ids not filled in well enough')


        # Check for a difference.
        if orig_child.tail != mod_child.tail:

            # Want to know what happened.
            # Check if the mod_child is elsewhere later in the original.
            mod_child_in_orig = any(mod_child.tail == x.tail 
                                    for x in orig_children[1:])
            # Check if the orig_child is elsewhere in the child.
            orig_child_in_mod = any(orig_child.tail == x.tail 
                                    for x in mod_children[1:])

            if mod_child_in_orig == True and orig_child_in_mod == False:

                # This case suggests the orig node was removed.
                patch_nodes.append(_Patch_Node_Constructor(
                    op     = 'remove', type = 'node',
                    target = orig_child,
                    cfg    = cfg ))

                orig_children.remove(orig_child)
                continue
            
            elif mod_child_in_orig == False and orig_child_in_mod == True:

                # This case suggests a node was added.
                patch_nodes.append(_Patch_Node_Constructor(
                    op     = 'add', type = 'node',
                    # Insert before the original.
                    target = orig_child,
                    pos = 'before',
                    value  = deepcopy(mod_child),
                    cfg    = cfg ))

                mod_children.remove(mod_child)
                continue

            elif mod_child_in_orig == False and orig_child_in_mod == False:

                # Neither node is in the other; can handle this with
                #  a replacement.
                patch_nodes.append(_Patch_Node_Constructor(
                    op     = 'replace', type = 'node',
                    target = orig_child,
                    value  = deepcopy(mod_child),
                    cfg    = cfg ))

                orig_children.remove(orig_child)
                mod_children.remove(mod_child)
                continue

            else:
                # Something weird happened; nodes somehow got reordered.
                # There is no diff operation for reordering, so as a backup
                # just delete the original node (later passes will put it
                # back in later in the list).
                patch_nodes.append(_Patch_Node_Constructor(
                    op     = 'remove', type = 'node',
                    target = orig_child,
                    cfg    = cfg ))
                
                orig_children.remove(orig_child)
                continue

        else:
            # Quick error check: if tails match, tags must match,
            # else something weird happened.
            if orig_child.tag != mod_child.tag:
                raise Exception('Node pair found with same id but mismatched tags')


        # Comments may have had their text changed.
        # Since diff patching these requires a full node replacement,
        # handle it here instead of by modifying the existing node.
        if (orig_child.tag is ET.Comment 
        and orig_child.text != mod_child.text):
            # Pack the text in a Comment node.
            new_comment = ET.Comment(mod_child.text)
            # Copy over the node id, else the next loop pass will
            # replace it again. TODO: maybe unnecessary now that
            # children aren't reiterated.
            new_comment.tail = orig_child.tail
            patch_nodes.append(_Patch_Node_Constructor(
                op     = 'replace', type = 'node',
                target = orig_child,
                value  = new_comment,
                cfg    = cfg ))
            
            orig_children.remove(orig_child)
            mod_children.remove(mod_child)
            continue


        # If here, then the nodes appear to be the same, superficially.
        # Still need to handle deeper changes, so recurse and pick out
        #  lower level patches.
        patch_nodes += _Get_Patch_Ops_Recursive(orig_child, mod_child, cfg)
        orig_children.remove(orig_child)
        mod_children.remove(mod_child)

    return patch_nodes


def _Get_Xpath_Recursive(node, cfg):
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

    # If this is a comment, it has no attributes, so skip some of this 
    # code. Comments are found using <parent_path>/comment()[#].
    if node.tag is ET.Comment:
        xpath = 'comment()'
        similar_elements = parent.xpath(xpath)

    else:
        # The xpath is just the path to the parent, combined with the tag
        #  of the child node and its attributes, and the index among 
        #  nodes with that tag and attributes (as a backup).
        # To reduce fluff, a first check will just use the tag, and if
        #  there are multiple matches, a loop will add attributes iteratively
        #  until a single node matches.
        # (This could just start with all attributes, but they are often
        #  not needed and clutter up the output diff patch.)
        xpath = node.tag

        # Add forced attributes.
        forced_attr_added = False
        for key in cfg['forced_attributes']:
            value = node.get(key)
            # Often nodes will not have the attribute; skip those cases.
            if value == None:
                continue
            # Skip anything with quotes (see comments below on why).
            if '"' in value or "'" in value:
                continue
            xpath += '''[@{}='{}']'''.format(key, value)
            forced_attr_added = True

        # If the parent has a large number of children, eg. for
        # the top level of the wares file or similar cases, then the xpath
        # is expected to initially match everything. To save some time,
        # these cases can skip to the first attribute addition (eg. "id").
        # The check can be for something like num_children > 30, though
        # even 500 should catch the worst cases.
        # Ensure the node has at least one attribute to add, and skip
        # this shortcut if a forced attribute was already added.
        # (In quick tests on some larger files, this saves ~10%.)
        if len(parent) > 50 and len(node.attrib) >= 1 and not forced_attr_added:
            # Give a couple dummy entries to trigger node addition.
            similar_elements = [None, None]
        else:
            # Get elements with the same tag.
            similar_elements = parent.xpath(xpath)

        # Add attributes if there is more than 1 similar element.
        if len(similar_elements) > 1:

            # To make the generated xpaths more human pleasing, attributes
            # will be selected based on some priority rules that should
            # be suitable to general X4 files. This also increases the
            # chances of hitting on a unique attribute.
            attribute_names = Sort_Attributes(node.keys())

            # Add attributes.
            for key in attribute_names:
                # Skip if this was a forced attribute, already added.
                if key in cfg['forced_attributes']:
                    continue

                value = node.get(key)

                # Note: the xpath will itself be an attribute in double
                # quotes, so to avoid nested double quotes (which get
                # output as &quot; in the xml, which xpath then can't
                # deal with reliably; other attempts at escaping also failed),
                # just use single quotes for this inner term.
                # If the value has quotes, nothing googled has worked, so
                # consider that an impossible match.
                if '"' in value or "'" in value:
                    continue
                xpath += '''[@{}='{}']'''.format(key, value)

                # Check element matches again.
                similar_elements = parent.xpath(xpath)
                # If just one match, done.
                if len(similar_elements) == 1:
                    break

        # Verify this node was matched with the current xpath.
        assert len(similar_elements) >= 1


    # Flesh out the xpath with the parent prefix.
    xpath = _Get_Xpath_Recursive(parent, cfg) + '/' + xpath

    # If there are still multiple element matches, add a suffix.
    # Note: the xpath index is relative to other nodes matched with
    # the same attributes (which differs from find/findall if there
    # were preceeding attributes).
    # Note: comments in documentation always show up with a bracket as well.
    if len(similar_elements) > 1 or node.tag is ET.Comment:
        # Note: xpath is 1-based indexing.
        index = similar_elements.index(node) + 1
        xpath += '[{}]'.format(index)
        
    return xpath


def Sort_Attributes(attr_names):
    '''
    Sort attribute names, placing the highest priority first, to aid
    in making more human-pleasing diff xpaths.
    '''
    ret_list = []
    low_prio_list = []

    # High priority attributes.
    # id is normally unique. 
    # Name is often unique, possibly a text lookup.
    # Ware can be a ware name.
    # ref is a connection name.
    # macro is often a name.
    # start is for sound library.
    # sinceversion for aiscript patches.
    # By request, include method (for wares).
    for name in ['id','name','ware','ref','macro','sinceversion','start','method']:
        if name in attr_names:
            attr_names.remove(name)
            ret_list.append(name)

    # Low priority attributes.
    # chance is common in md scripts debug nodes.
    # weight is often the same value.
    for name in ['chance','weight']:
        if name in attr_names:
            attr_names.remove(name)
            low_prio_list.append(name)

    # Everything else can be prioritized by length of the attribute.
    # Too short and it may not be unique, but too long and it is just
    # ugly to look at.  Center priority around ~10 characters.
    for name in sorted(attr_names, key = lambda x: max(0, (10 - len(x))) + max(0, (len(x) - 10))):
        ret_list.append(name)

    return ret_list + low_prio_list


def Verify_Patch(original_node, modified_node, patch_node):
    '''
    Verify that the patch applied to the original recreates the modified
    xml node. Returns True on success, False on failure.
    '''
    # Copy the original, to do the patching without changing the input.
    original_node_patched = deepcopy(original_node)
    original_node_patched = Apply_Patch(original_node_patched, patch_node)
    
    # Line comparison works poorly if the attributes are out of
    # order, which can happen since the diff patch adds attributes to
    # the end of a dict that may have been earlier in the original.
    # As such, since lxml has no way to order attributes on printout,
    # this comparison needs to be done in a way that allows ordering
    # differences.
    original_elements = [x for x in original_node_patched.iter()]
    modified_elements = [x for x in modified_node.iter()]

    success = True
    # Compare by node, out to the longest list.
    for orig, mod in zip_longest(original_elements, modified_elements):
    
        # Filter the attributes to remove namespaced ones, which will
        # be allowed to mismatch.
        orig_attr = {k:v for k,v in orig.attrib.items() if not Is_NS_Attribute(k)}
        mod_attr  = {k:v for k,v in mod.attrib.items()  if not Is_NS_Attribute(k)}

        # Look at tag, attributes, text.
        if orig.tag != mod.tag or orig_attr != mod_attr or orig.text != mod.text:
            # If it was succesful up to this point, print a message.
            if success:
                Print_Log('Patch test failed on line {}.'.format(orig.sourceline))
            # Flag as a failure.
            success = False
            break

    
    # For checking, dump all of the xml to files.
    # This is mainly intended for use by the unit test.
    # TODO: attach to an input arg.
    if 0:
        if not success:
            from pathlib import Path
            cwd = Path.cwd()
            with open('test_original_node.xml', 'w') as file:
                file.write(Print(original_node, encoding = 'unicode'))
            with open('test_modified_node.xml', 'w') as file:
                file.write(Print(modified_node, encoding = 'unicode'))
            with open('test_patch_node.xml', 'w') as file:
                file.write(Print(patch_node, encoding = 'unicode'))
            with open('test_original_node_patched.xml', 'w') as file:
                file.write(Print(original_node_patched, encoding = 'unicode'))
            # Pause; allow time to peek at files or ctrl-C.
            #input('Press enter to continue testing.')

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
        node_list = modified_node.xpath('.//*')

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
            Print_Log('Test {} passed'.format(test_number))
        except XML_Patch_Exception as ex:
            Print_Log('Test {} failed; message: {}'.format(test_number, ex))
    return

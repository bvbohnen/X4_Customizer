
import xml.etree.ElementTree as ET
from xml.dom import minidom

def XML_Find_All_Matches(base_node, match_node):
    '''
    Searches an xml node's contents to find a match to a given reference
    node. Will match node type, all attributes, and all children
    recursively. Returns a list of matching child nodes of base_node,
    possibly empty with no matches.
    '''
    # Start with a pre-filtering that does not check ref_node children,
    #  only type and attributes.
    # Use xpath './/' to search all children recursively of the parent.
    xpath = './/{}'.format(match_node.tag)

    # Add all of the ref_node attributes.
    for name, value in match_node.items():
        xpath += '[@{}="{}"]'.format(name, value)

    # Can add simple child node type checks without getting too messy.
    # This just checks that the matched node has a child node of the
    #  appropriate type name; it doesn't filter out having extra
    #  children or similar.
    # ET is unintuitive about this, but to work through children this
    #  needs to to an unqualified iteration (which intuitively would
    #  should give attribute names, to match up with .items(), but
    #  whatever).
    for child in match_node:
        xpath += '[{}]'.format(child.tag)

    # Get the initial matches.
    found_nodes = base_node.findall(xpath)

    # Filter out those without the right number of children.
    found_nodes = [x for x in found_nodes 
                   if len(x) == len(match_node)]

    # Now work through children checks.
    # This can potentially be simplified by stripping off fluff text (eg.
    #  tail and such), converting nodes to text strings, and comparing those
    #  text strings. That would handle all recursive aspects in one step,
    #  and shouldn't have to much overhead if the pre-filter did a good
    #  job trimming down the problem space. Use a support function for this.
    match_text = XML_To_Unformatted_String(match_node)
    found_nodes = [x for x in found_nodes 
                   if XML_To_Unformatted_String(x) == match_text]

    return found_nodes


def XML_Find_Match(base_node, match_node):
    '''
    Searches an xml node's contents to find a match to a given reference
    node. Will match node type, all attributes, and all children
    recursively. Returns the corresponding child of base_node if found,
    else returns None. Error if there are 0 or multiple matches.
    '''
    found_nodes = XML_Find_All_Matches(base_node, match_node)
    
    # Error if there isn't a single match.
    found_count = len(found_nodes)
    if found_count == 0:
        raise Exception('XML_Find_Match failed to find a match')
    elif found_count > 1:
        raise Exception('XML_Find_Match found {} matches'.format(found_count))

    # Return a single node.
    return found_nodes[0]


def XML_To_Unformatted_String(node):
    '''
    Convert an xml node (with attributes, children, etc.) to a string,
    omitting whitespace from the 'text' and 'tail' fields. Attributes
    are sorted. 
    '''
    # Possible approaches:
    # 1) Deepcopy the node, edit all text/tail members to
    #    strip() them, and use the normal xml tostring method.
    # 2) Manually stride through text/attributes/tail constructing a
    #    string, then recursively append strings from each child to
    #    it.
    # The former is easier, but clumsy for nodes with a lot of content
    #  in them.  Try out (2).

    # Strip the text and tail here. If None, make an empty string.
    text = node.text.strip() if node.text else ''
    tail = node.tail.strip() if node.tail else ''

    # This will always use "<tag >" for the node definition, with "</tag>" to
    #  then close the node (eg. no "<tag />"), for simpler logic.
    text = '<{}{}{}{}{}>{}{}{}{}</{}>'.format(
        # Opener.
        node.tag,

        # Text field, with preceeding space if present.
        ' ' if text else '',
        text,

        # Collect attributes together, with preceeding space if present.
        ' ' if node.items() else '',
        ' '.join(['{}="{}"'.format(key, value) 
                  for key, value in sorted(node.items())]),
        
        # Tail. Don't need space on this, since after the >.
        tail,
        
        # Extra final newline if there are children.
        '\n' if node else '',
        # Append all children.
        # Note: newline separators are unnecessary, but may make debug
        #  viewing easier.
        '\n'.join([XML_To_Unformatted_String(child) for child in node]),
        # Extra final newline if there are children.
        '\n' if node else '',
        
        # Closer.
        node.tag,
        )
    #print(text)
    return text


def XML_Replace_Node(parent_node, old_node, new_node):
    '''
    Replace a child node of the parent.
    '''
    index = list(parent_node).index(old_node)
    parent.remove(old_node)
    parent_node.insert(index, new_node)
    return

def XML_Insert_After(parent_node, old_node, new_node):
    '''
    Insert a new node after an old child node under the parent.
    '''
    index = list(parent_node).index(old_node)
    parent_node.insert(index + 1, new_node)
    return


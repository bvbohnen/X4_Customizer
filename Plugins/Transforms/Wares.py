'''
Transforms to wares.
'''
from Framework.Documentation import Doc_Category_Default
_doc_category = Doc_Category_Default('Transforms')

from fnmatch import fnmatch
from Framework import Transform_Wrapper, Load_File
from .Support import *

# Shared documentation.
doc_matching_rules = '''
    Ware transforms will commonly use a group of matching rules
    to determine which wares get modified, and by how much.    

    * Matching rules:
      - These are tuples pairing a matching rule (string) with transform
        defined args, eg. ("key  value", arg0, arg1, ...).
      - The "key" specifies the ware field to look up, which will
        be checked for a match with "value".
      - If a ware matches multiple rules, the first match is used.
      - Supported keys:
        - 'id'        : Name of the ware entry; supports wildcards.
        - 'group'     : The ware group category.
        - 'container' : The ware container type.
        - 'tags'      : One or more tags, space separated.
          - See Print_Wares output for tag listings.
        - '*'         : Matches all wares; takes no value term.

    Examples:
    <code>
        Adjust_Ware_Price_Spread(0.5)
        Adjust_Ware_Price_Spread(
            ('id        energycells'       , 2  ),
            ('group     shiptech'          , 0.8),
            ('container ship'              , 1.5),
            ('tags      crafting'          , 0.2),
            ('*'                           , 0.5) )
    </code>
    '''

@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Ware_Price_Spread(
        # Allow multipliers to be given as a loose list of args.
        *match_rule_multipliers
    ):
    '''
    Adjusts ware min to max price spreads. This primarily impacts
    trading profit. Spread will be limited to ensure 10 credits
    from min to max, to avoid impairing AI decision making.

    * match_rule_multipliers:
      - Series of matching rules paired with the spread multipliers to use.
    '''
    wares_file = Load_File('libraries/wares.xml')
    xml_root = wares_file.Get_Root()

    # Get wars paired with multipliers.
    for ware, multiplier in Gen_Wares_Matched_To_Args(xml_root, match_rule_multipliers):
        
        # Look up the existing spread.
        price_node = ware.find('./price')
        price_min  = int(price_node.get('min'))
        price_avg  = int(price_node.get('average'))
        price_max  = int(price_node.get('max'))

        # If price is 0 or 1, just skip.
        if price_avg in [0,1]:
            continue

        # Can individually adjust the min and max separations from average.
        new_min = round(price_avg - (price_avg - price_min) * multiplier)
        new_max = round(price_avg + (price_max - price_avg) * multiplier)

        # Limit to a spread of 10 credits or more from min to max,
        # or 5 from average.
        if new_min > price_avg - 5:
            new_min = price_avg - 5
        if new_max < price_avg + 5:
            new_max = price_avg + 5

        # If min dropped to 0, bump it back to 1.
        if new_min <= 0:
            new_min = 1
            # Adjust max to have the same spread from average.
            new_max = price_avg + (price_avg - new_min)

        # Put them back.
        price_node.set('min', str(int(new_min)))
        price_node.set('max', str(int(new_max)))

    wares_file.Update_Root(xml_root)
    return


@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Ware_Prices(
        # Allow multipliers to be given as a loose list of args.
        *match_rule_multipliers
    ):
    '''
    Adjusts ware prices. This should be used with care when selecting
    production chain related wares.
    
    * match_rule_multipliers:
      - Series of matching rules paired with the spread multipliers to use.
    '''
    wares_file = Load_File('libraries/wares.xml')
    xml_root = wares_file.Get_Root()

    # Get wars paired with multipliers.
    for ware, multiplier in Gen_Wares_Matched_To_Args(xml_root, match_rule_multipliers):
        
        # Adjust everything in the price subnode.
        price = ware.find('price')
        for name, value in price.items():
            XML_Multiply_Int_Attribute(price, name, multiplier)
            
    wares_file.Update_Root(xml_root)
    return



##############################################################################
# Support functions.

def Gen_Wares_Matched_To_Args(ware_xml_root, match_rule_args):
    '''
    Generator that yields tuples of (ware node, args), where args are selected
    based on the weapon matching a rule in match_rule_args.
    The args may be a single value or a list of values.
    '''
    # Put matching rules in standard form.
    rules = Standardize_Match_Rules(match_rule_args)
    
    # Loop over the ware nodes; only first level children.
    for ware in ware_xml_root.findall('./ware'):
        
        # Look up the tags and a couple other properties of interest.
        ware_id     = ware.get('id')
        group       = ware.get('group')
        container   = ware.get('transport')
        tags        = ware.get('tags', '')
        
        # Check the matching rules.
        match_args = None
        for key, value, *args in rules:
            if((key == '*')
            or (key == 'id' and fnmatch(ware_id, value))
            or (key == 'group' and group == value)
            or (key == 'container' and container == value)
            # Check all tags, space separated.
            or (key == 'tags' and all(x in tags for x in value.split(' ')))
            ):
                match_args = args
                break
        # Skip if no match.
        if match_args == None:
            continue
        
        # Isolate a single arg out of the list.
        if len(match_args) == 1:
            match_args = match_args[0]
        yield ware, match_args
    return
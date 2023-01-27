from collections import defaultdict
from fnmatch import fnmatch
import math
from ..Classes import *
from Framework import Transform_Wrapper, File_System, Print
from .Support import Fill_Defaults, Group_Objects_To_Rules, Convert_Old_Match_To_New

__all__ = ['Adjust_Shields']

doc_matching_rules = '''
    * Matching rules:
      - These are tuples pairing a matching rule (string) with transform
        defined args, eg. ("key  value", arg0, arg1, ...).
      - The "key" specifies the xml field to look up, which will
        be checked for a match with "value".
      - If a target object matches multiple rules, the first match is used.
      - Supported keys for shields:
        - 'name'    : Internal name of the shield macro; supports wildcards.
        - 'tag'    : One or more tags, space separated. (e.g. 'medium shield component standard')
        - 'mark'    : The shield mark. (e.g. 1, 2 or 3)
        - 'maker'   : The maker race of the shield. List of makers (if more exist, e.g. boron from expansion or other mods, they can also be used):
          - 'argon'
          - 'paranid'
          - 'split'
          - 'teladi'
          - 'terran'
          - 'xenon'
        - '*'       : Matches all ships; takes no value term.

    Examples:
    <code>
        #buff all shields capacity by 1.5
        Adjust_Shields(
            {'match_any' : ['*'],  
            'property' : 'recharge', 'attribute' : 'max', 'operation' : '*', 'value' : 1.5}
            )
        #set all argon medium shields to 0 recharge delay
        Adjust_Shields(
            {'match_all' : ['tags medium shield standard','maker argon'],  
            'property' : 'recharge', 'attribute' : 'delay', 'operation' : '=', 'value' : 0}
            )
    </code>

    Properties and attributes:
    Property    Attribute
    =====================
    recharge    max
    recharge    rate
    recharge    delay
    hull        max
    hull        integrated
    '''

@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Shields(
        *rules,
    ):
    '''
    Adjusts shield values.
        
    Args are one or more dictionaries with these fields, where matching
    rules are applied in order, with a shield being grouped by the first
    rule it matches:

    * value
    - Float, value to be used for the adjustment.
    * operation
    - String, determines which operation to use with the value
    - operations: '=', '*', '-'
    * property
    - String, the xml property to change
    * attribute
    - String, the xml attribute to change on the property
    * match_any, match_all, match_none
    - Lists of matching rules. Shield is selected if matching nothing
        from match_none, and anything from match_any or everything from
        match_all.        
    * skip
    - Optional, bool, if True then this group is not edited.
    '''    
    if not rules:
        return

    # Shared rule/database prep.
    rules, database = Prep_Rules_And_Database(rules)

    for rule in rules:
        if rule['skip']:
            continue
        shield_macros = rule['matches']
        value  = rule['value']
        operation = rule['operation']        
        property = rule['property']
        attribute = rule['attribute']

        #make the changes
        for shield_macro in shield_macros:
            shield_macro.Set_Float_Property(property, attribute, value, operation)

    # Apply the xml changes.
    database.Update_XML()
    return            

'''
For reference, paths/attributes of interest.

'./properties/recharge'                , 'max'  
'./properties/recharge'                , 'rate'  
'./properties/recharge'                , 'delay'  

'./properties/hull'                  , 'max'      
'./properties/hull'                  , 'integrated'

'''

##############################################################################
# Support functions.
def Prep_Rules_And_Database(rules, defaults = {}):
    '''
    Shared code to prepare the rules and load a database.
    Returns a tuple of (rules, database).
    '''    

    # Polish the rules with defaults.
    Fill_Defaults(rules, defaults)

    # Load the shields
    database = Database()
    shield_macros = database.Get_Macros('*', class_names = ['shieldgenerator'])

    # Group according to rules.
    Group_Objects_To_Rules(shield_macros, rules, Is_Match)
    return (rules, database)

    
def Is_Match(shield, match_none, match_all, match_any, **kwargs):
    '''
    Checks a ship macro against the given rules, and returns True if a match,
    else False.

    * shield
      - Shield macro object.
    * match_all
      - List of match rules (tuple of key, value) that must all match.
    * match_any
      - List of match rules of which any need to match.
    * match_none
      - List of match rules that must all mismatch.
    '''
    # Look up properties of interest.
    component = shield.Get_Component()
    name = component.name
    tags = component.Get_Connection_Tags()
    maker = shield.Get('./properties/identification', 'makerrace')
    mark = shield.Get('./properties/identification', 'mk')
    
    # Check the matching rules.
    # match_none failures first, then match_all failures, then match_any
    # successes.
    for rules in [match_none, match_all, match_any]:
        # Skip if not given.
        if not rules:
            continue
        
        for rule in rules:
            if rule == '*':
                key = rule
                value = None
            else:
                key, value = rule.split(' ', 1)
            
            if((key == '*')
            or (key == 'name' and fnmatch(name, value))
            or (key == 'tags' and all(x in tags for x in value.split(' ')))
            or (key == 'maker' and maker == value)
            or (key == 'mark' and mark == value)):
                # If match_none, fail.
                if rules is match_none:
                    return False
                # If match_any, direct pass.
                elif rules is match_any:
                    return True
            else:
                # If match_all, direct fail on a mismatch.
                if rules is match_all:
                    return False

    # If here, assuming no match_any was given, assume match, else mismatch.
    if match_any:
        return False
    return True

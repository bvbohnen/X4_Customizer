from collections import defaultdict
from fnmatch import fnmatch
import math
from ..Classes import *
from Framework import Transform_Wrapper, File_System, Print
from .Support import Fill_Defaults, Group_Objects_To_Rules, Convert_Old_Match_To_New

__all__ = ['Adjust_Engines']

doc_matching_rules = '''
    * Matching rules:
      - These are tuples pairing a matching rule (string) with transform
        defined args, eg. ("key  value", arg0, arg1, ...).
      - The "key" specifies the xml field to look up, which will
        be checked for a match with "value".
      - If a target object matches multiple rules, the first match is used.
      - Supported keys for engines:
        - 'name'    : Internal name of the engine macro; supports wildcards.
        - 'tag'    : One or more tags, space separated. (e.g. 'medium engine component standard')
        - 'mark'    : The engine mark. (e.g. 1, 2 or 3)
        - 'maker'   : The maker race of the engine. List of makers (if more exist, e.g. boron from expansion or other mods, they can also be used):
          - 'argon'
          - 'paranid'
          - 'split'
          - 'teladi'
          - 'terran'
          - 'xenon'
        - '*'       : Matches all ships; takes no value term.

    Examples:
    <code>
        #buff all engines forward thrust by 1.5
        Adjust_Engines(
            {'match_any' : ['*'],  
            'property' : 'thrust', 'attribute' : 'forward', 'operation' : '*', 'value' : 1.5}
            )
        #set all xenon extra large engines to 0 travel thrust!
        Adjust_Engines(
            {'match_all' : ['tags engine extralarge component standard','maker xenon'],  
            'property' : 'recharge', 'attribute' : 'delay', 'operation' : '=', 'value' : 0}
            )
    </code>

    Properties and attributes:
    Property    Attribute
    =====================
    thrust      forward
    thrust      reverse
    thrust      strafe
    thrust      pitch
    thrust      yaw
    thrust      roll

    boost       duration
    boost       thrust
    boost       attack
    boost       release

    travel      charge
    travel      thrust
    travel      attack
    travel      release

    hull        max
    hull        threshold
    '''

@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Engines(
        *rules,
    ):
    '''
    Adjusts engine values.
        
    Args are one or more dictionaries with these fields, where matching
    rules are applied in order, with an engine being grouped by the first
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
    - Lists of matching rules. Engine is selected if matching nothing
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
        engine_macros = rule['matches']
        value  = rule['value']
        operation = rule['operation']        
        property = rule['property']
        attribute = rule['attribute']

        #make the changes
        for engine_macro in engine_macros:
            engine_macro.Set_Float_Property(property, attribute, value, operation)

    # Apply the xml changes.
    database.Update_XML()
    return            

'''
For reference, paths/attributes of interest.

    './properties/thrust'                , 'forward'  
    './properties/thrust'                , 'reverse'  

    './properties/thrust'                , 'strafe'   
    './properties/thrust'                , 'pitch'    
    './properties/thrust'                , 'yaw'      
    './properties/thrust'                , 'roll'     

    './properties/boost'                 , 'duration' 
    './properties/boost'                 , 'thrust'   
    './properties/boost'                 , 'attack'   
    './properties/boost'                 , 'release'  

    './properties/travel'                , 'charge'   
    './properties/travel'                , 'thrust'   
    './properties/travel'                , 'attack'   
    './properties/travel'                , 'release'  

    './properties/hull'                  , 'max'      
    './properties/hull'                  , 'threshold'

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

    # Load the engines
    database = Database()
    engine_macros = database.Get_Macros('*', class_names = ['engine'])

    # Group according to rules.
    Group_Objects_To_Rules(engine_macros, rules, Is_Match)
    return (rules, database)

    
def Is_Match(engine, match_none, match_all, match_any, **kwargs):
    '''
    Checks a ship macro against the given rules, and returns True if a match,
    else False.

    * engine
      - engine macro object.
    * match_all
      - List of match rules (tuple of key, value) that must all match.
    * match_any
      - List of match rules of which any need to match.
    * match_none
      - List of match rules that must all mismatch.
    '''
    # Look up properties of interest.
    component = engine.Get_Component()
    name = component.name
    tags = component.Get_Connection_Tags()
    maker = engine.Get('./properties/identification', 'makerrace')
    mark = engine.Get('./properties/identification', 'mk')
    
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

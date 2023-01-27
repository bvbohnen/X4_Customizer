from collections import defaultdict
from fnmatch import fnmatch
import math
from ..Classes import *
from Framework import Transform_Wrapper, File_System, Print
from .Support import Fill_Defaults, Group_Objects_To_Rules, Convert_Old_Match_To_New

__all__ = ['Adjust_Ships']

doc_matching_rules = '''
    * Matching rules:
      - These are tuples pairing a matching rule (string) with transform
        defined args, eg. ("key  value", arg0, arg1, ...).
      - The "key" specifies the xml field to look up, which will
        be checked for a match with "value".
      - If a target object matches multiple rules, the first match is used.
      - Supported keys for Ships:
        - 'name'    : Internal name of the ship macro; supports wildcards.
        - 'purpose' : The primary role of the ship. List of purposes:
          - mine
          - trade
          - build
          - fight
        - 'type'    : The ship type. List of types:
          - courier, resupplier, transporter, freighter, miner,
            largeminer, builder
          - scout, interceptor, fighter, heavyfighter
          - gunboat, corvette, frigate, scavenger
          - destroyer, carrier, battleship
          - xsdrone, smalldrone, police, personalvehicle,
            escapepod, lasertower
        - 'class'   : The class of ship. List of classes:
          - 'ship_xs'
          - 'ship_s'
          - 'ship_m'
          - 'ship_l'
          - 'ship_xl'
          - 'spacesuit'
        - '*'       : Matches all ships; takes no value term.

    Examples:
    <code>
        #buff all ships missile capacity by +50
        Adjust_Ships(
            {'match_any' : ['*'],  
            'property' : 'storage', 'attribute' : 'missile', 'operation' : '+', 'value' : 50}
            )
        #remove explosion damage from large and extralarge ships
        Adjust_Ships(
            {'match_all' : ['tags Ship extralarge component standard','maker xenon'],  
            'property' : 'recharge', 'attribute' : 'delay', 'operation' : '=', 'value' : 0}
            )
    </code>

    Properties and attributes:
    Property            Attribute
    =============================
    hull                max

    secrecy             level

    people              capacity

    explosiondamage     value

    storage             missile
    storage             unit

    physics             mass

    physics/inertia     pitch
    physics/inertia     yaw
    physics/inertia     roll

    physics/drag        forward
    physics/drag        reverse
    physics/drag        horizontal
    physics/drag        vertical
    physics/drag        pitch
    physics/drag        yaw
    physics/drag        roll
    '''

@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Ships(
        *rules,
    ):
    '''
    Adjusts Ship values.
        
    Args are one or more dictionaries with these fields, where matching
    rules are applied in order, with a ship being grouped by the first
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
    - Lists of matching rules. Ship is selected if matching nothing
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
        ship_macros = rule['matches']
        value  = rule['value']
        operation = rule['operation']        
        property = rule['property']
        attribute = rule['attribute']

        #make the changes
        for ship_macro in ship_macros:
            ship_macro.Set_Float_Property(property, attribute, value, operation)

    # Apply the xml changes.
    database.Update_XML()
    return            

##############################################################################
# Support functions.
def Prep_Rules_And_Database(rules, defaults = {}):
    '''
    Shared code to prepare the rules and load a database.
    Returns a tuple of (rules, database).
    '''    

    # Polish the rules with defaults.
    Fill_Defaults(rules, defaults)

    # Load the Ships
    database = Database()
    ship_macros = database.Get_Ship_Macros()

    # Group according to rules.
    Group_Objects_To_Rules(ship_macros, rules, Is_Match)
    return (rules, database)

    
def Is_Match(ship, match_none, match_all, match_any, **kwargs):
    '''
    Checks a ship macro against the given rules, and returns True if a match,
    else False.

    * Ship
      - Ship macro object.
    * match_all
      - List of match rules (tuple of key, value) that must all match.
    * match_any
      - List of match rules of which any need to match.
    * match_none
      - List of match rules that must all mismatch.
    '''
    # Look up properties of interest.
    name = ship.name
    class_name = ship.class_name
    type = ship.Get('./properties/ship', 'type')
    purpose = ship.Get('./properties/purpose', 'primary')
    
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
            or (key == 'name'    and fnmatch(name, value))
            or (key == 'class'   and class_name == value)
            or (key == 'type'    and type == value)
            or (key == 'purpose' and purpose == value)):
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


from fnmatch import fnmatch
from Framework import Transform_Wrapper, Load_File, File_System
from .Support import Standardize_Match_Rules
from .Support import XML_Multiply_Int_Attribute
from .Support import XML_Multiply_Float_Attribute
from ..Analyses.Shared import Get_Ship_Macro_Files

__all__ = [
    'Adjust_Ship_Speed',
    'Adjust_Ship_Turning',
    'Adjust_Ship_Hull',
    'Adjust_Ship_Crew_Capacity',
    'Adjust_Ship_Drone_Storage',
    'Adjust_Ship_Missile_Storage',
    ]

doc_matching_rules = '''
    Ship transforms will commonly use a group of matching rules
    to determine which ships get modified, and by how much.   

    * Matching rules:
      - These are tuples pairing a matching rule (string) with transform
        defined args, eg. ("key  value", arg0, arg1, ...).
      - The "key" specifies the xml field to look up, which will
        be checked for a match with "value".
      - If a target object matches multiple rules, the first match is used.
      - Supported keys for ships:
        - 'name'    : Internal name of the ship macro; supports wildcards.
        - 'purpose' : The general role of the ship. List of purposes:
          - mine
          - trade
          - build
          - fight
        - 'type'    : The ship type. List of types:
          - courier, resupplier, transporter, freighter, miner,
            largeminer, builder
          - scout, interceptor, fighter, heavyfighter
          - bomber, corvette, frigate, scavenger
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
        Adjust_Ship_Speed(1.5)
        Adjust_Ship_Speed(
            ('name ship_xen_xl_carrier_01_a*', 1.2),
            ('class ship_s'                  , 2.0),
            ('type corvette'                 , 1.5),
            ('purpose fight'                 , 1.2),
            ('*'                             , 1.1) )
    </code>
    '''


# TODO:
'''
- explosion damage
- maybe default/compatible software

Complex speed adjustment that retuns ship classes relative to each other,
eg. making scouts > fighters > heavy fighters > corvettes > ...
(This might be joint changed alongside thrusters.)

Other fields will require editing the connected ship components,
which may be shared across multiple ships.

Note: from a perusal of a saved game, connected components are saved as
part of the ship, and not regenerated from the base ship macro.
Eg. if the ship macro connects to "dockarea_arg_s_ship_03_macro", that
latter macro will be referenced in the save.

Component changes could either work like weapon bullets (edit based on the
first one found), or the components could be made unique per-ship, in
which case all of these fields become unique but may only apply
to newly constructed ships.
'''

@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Ship_Speed(
        *match_rule_multipliers
    ):
    '''
    Adjusts the speed and acceleration of ships, in each direction.

    * match_rule_multipliers:
      - Series of matching rules paired with the multipliers to use.
    '''
    def Node_Update(ship_macro, multiplier):
        # These will all work on the inverted multiplier, since
        # they reduce speed/acceleration.
        inv_mult = 1/multiplier

        # The fields to change are scattered under the physics node.
        physics_node = ship_macro.find('./properties/physics')
        drag_node = physics_node.find('./drag')
        inertia_node = physics_node.find('./inertia')

        XML_Multiply_Float_Attribute(physics_node, 'mass', inv_mult)
        for drag_field in ['forward', 'reverse', 'horizontal', 'vertical']:
            XML_Multiply_Float_Attribute(drag_node, drag_field, inv_mult)
        return True

    # Hand off to shared code to run updates.
    Update_Nodes_By_Rules(match_rule_multipliers, Node_Update)
    return


@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Ship_Turning(
        *match_rule_multipliers
    ):
    '''
    Adjusts the turning rate of ships, in each direction.

    * match_rule_multipliers:
      - Series of matching rules paired with the multipliers to use.
    '''
    def Node_Update(ship_macro, multiplier):
        # These will all work on the inverted multiplier, since
        # they reduce speed/acceleration.
        inv_mult = 1/multiplier

        # The fields to change are scattered under the physics node.
        physics_node = ship_macro.find('./properties/physics')
        drag_node = physics_node.find('./drag')
        inertia_node = physics_node.find('./inertia')

        for drag_field in ['pitch', 'yaw', 'roll']:
            # Terms show up under inertia and drag.
            # Presumably, intertia is roughly equivelent to mass for raw
            # speed, determining the acceleration.
            XML_Multiply_Float_Attribute(drag_node, drag_field, inv_mult)
            XML_Multiply_Float_Attribute(inertia_node, drag_field, inv_mult)
        return True

    # Hand off to shared code to run updates.
    Update_Nodes_By_Rules(match_rule_multipliers, Node_Update)
    return


@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Ship_Hull(
        *match_rule_multipliers
    ):
    '''
    Adjusts the hull values of ships.

    * match_rule_multipliers:
      - Series of matching rules paired with the multipliers to use.
    '''
    def Node_Update(ship_macro, multiplier):
        # These are in the 'hull' node, 'max' attribute.
        hull_node = ship_macro.find('./properties/hull')
        XML_Multiply_Int_Attribute(hull_node, 'max', multiplier)
        return True

    # Hand off to shared code to run updates.
    Update_Nodes_By_Rules(match_rule_multipliers, Node_Update)
    return


@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Ship_Missile_Storage(
        *match_rule_multipliers
    ):
    '''
    Adjusts the missile storage of ships.

    * match_rule_multipliers:
      - Series of matching rules paired with the multipliers to use.
    '''
    def Node_Update(ship_macro, multiplier):
        # These are in the 'storage' node, 'missile' attribute.
        storage = ship_macro.find('./properties/storage')
        # Some ships don't have storage.
        if storage != None and storage.get('missile'):
            XML_Multiply_Int_Attribute(storage, 'missile', multiplier)
            return True
        return False

    # Hand off to shared code to run updates.
    Update_Nodes_By_Rules(match_rule_multipliers, Node_Update)
    return


@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Ship_Drone_Storage(
        *match_rule_multipliers
    ):
    '''
    Adjusts the drone ("unit") storage of ships.

    * match_rule_multipliers:
      - Series of matching rules paired with the multipliers to use.
    '''
    def Node_Update(ship_macro, multiplier):
        # These are in the 'storage' node, 'unit' attribute.
        storage = ship_macro.find('./properties/storage')
        # Some ships don't have storage.
        if storage != None and storage.get('unit'):
            XML_Multiply_Int_Attribute(storage, 'unit', multiplier)
            return True
        return False

    # Hand off to shared code to run updates.
    Update_Nodes_By_Rules(match_rule_multipliers, Node_Update)
    return


@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Ship_Crew_Capacity(
        *match_rule_multipliers
    ):
    '''
    Adjusts the crew capacities of ships. Note: crewmen contributions to
    ship combined skill appears to adjust downward based on max capacity,
    so increasing capacity can lead to a ship performing worse (unverified).

    * match_rule_multipliers:
      - Series of matching rules paired with the multipliers to use.
    '''
    def Node_Update(ship_macro, multiplier):
        people = ship_macro.find('./properties/people')
        if people != None and people.get('capacity'):
            XML_Multiply_Int_Attribute(people, 'capacity', multiplier)
            return True
        return False
    # Hand off to shared code to run updates.
    Update_Nodes_By_Rules(match_rule_multipliers, Node_Update)
    return



##############################################################################
# Support functions.

def Update_Nodes_By_Rules(
    match_rules,
    update_function,
    ):
    '''
    Shared function which will check all ships for rules matches, and pass
    the corresponding args for the rule to an update function.

    * match_rules
      - User provided list of rules, before Standardize_Match_Rules.
    * update_function
      - Function will takes (ship_macro_element, *args), and does 
        any necessary xml edits. This should return change_occurred,
        a boolean True on change and False or None on no change.
    '''
    # Put matching rules in standard form.
    rules = Standardize_Match_Rules(match_rules)
           
    # Switch to shared function that finds more mod ships.
    #game_files = File_System.Get_All_Indexed_Files('macros','ship_*')
    game_files = Get_Ship_Macro_Files()

    for game_file in game_files:
        xml_root = game_file.Get_Root()
        # There may be multiple macros in a file (though generally
        # this isn't expected).
        ship_macros = xml_root.findall('./macro')

        change_occurred = False
        for ship_macro in ship_macros:
            args = Get_Match_Rule_Args(ship_macro, rules)
            if not args:
                continue

            change_occurred |= update_function(ship_macro, args)
                
        if change_occurred:
            # Put the changes back.
            game_file.Update_Root(xml_root)
    return
    

def Get_Match_Rule_Args(ship_macro_xml, rules):
    '''
    Checks a ship macro against the given rules, and returns args from
    the first matched rule (as a tuple of there is more than 1 arg).
    On no match, returns None.

    * ship_macro_xml
      - The xml node with the specific ship macro.
    '''
    assert ship_macro_xml.tag == 'macro'

    # Look up properties of interest.
    name = ship_macro_xml.get('name')
    class_name = ship_macro_xml.get('class')

    # Not all ships have a type or purpose (mainly just spacesuits don't).
    try:
        type = ship_macro_xml.find('./properties/ship').get('type')
    except Exception:
        type = None
    try:
        purpose = ship_macro_xml.find('./properties/purpose').get('primary')
    except Exception:
        purpose = None

    # Check the matching rules.
    for key, value, *args in rules:
        if((key == '*')
        or (key == 'name'    and fnmatch(name, value))
        or (key == 'class'   and class_name == value)
        or (key == 'type'    and type == value)
        or (key == 'purpose' and purpose == value)
        ):
            # Want to return 1 item is there are 1 arg, else a tuple
            # or list of them. Python has no clean syntax for this
            # that is obvious.
            if len(args) == 1:
                return args[0]
            return args
    return None
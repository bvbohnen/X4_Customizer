
__all__ = [
    'Adjust_Ship_Speed',
    'Adjust_Ship_Turning',
    'Adjust_Ship_Hull',
    'Adjust_Ship_Crew_Capacity',
    'Adjust_Ship_Drone_Storage',
    'Adjust_Ship_Missile_Storage',
    'Set_Default_Radar_Ranges',
    'Set_Ship_Radar_Ranges',
    ]

from fnmatch import fnmatch
from lxml.etree import Element
from Framework import Transform_Wrapper, Load_File, File_System, Plugin_Log
from ..Support import Standardize_Match_Rules
from ..Support import XML_Multiply_Int_Attribute
from ..Support import XML_Multiply_Float_Attribute
#from ...Analyses.Shared import Get_Ship_Macro_Files
from ...Classes import *
from .Shared import *

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
'''
Maybe switch to using class repacking of the xml to do edits; though that
has overhead, it should be quick, and standardizes changes.
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
            # Note: some CoH xs ships don't have every field.
            # Skip if field is missing.
            if drag_node.get(drag_field) != None:
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
            # Presumably, inertia is roughly equivelent to mass for raw
            # speed, determining the acceleration.
            # Note: some CoH xs ships are missing nodes/attributes.
            if drag_node != None and drag_node.get(drag_field) != None:
                XML_Multiply_Float_Attribute(drag_node, drag_field, inv_mult)
            if inertia_node != None and inertia_node.get(drag_field) != None:
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
def Adjust_Shields(
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



@Transform_Wrapper(shared_docs = doc_matching_rules)
def Set_Default_Radar_Ranges(
        **class_distances
    ):
    '''
    Sets default radar ranges.  Granularity is station, type of satellite,
    or per ship size.  Ranges are in km, eg. 40 for vanilla game
    defaults of non-satellites. Note: ranges below 40km will affect
    when an unidentified object becomes identified, but objects
    will still show up out to 40km.
        
    Supported arguments:
    * ship_s
    * ship_m
    * ship_l
    * ship_xl
    * spacesuit
    * station
    * satellite
    * adv_satellite
    ''' 
    '''
    Test on 20k ships save above trinity sanctum, multiplying radar ranges:
    5/4    : 35 fps   (50km)
    1/1    : 37 fps   (40km, vanilla, fresh retest)
    3/4    : 39 fps   (30km, same as x3 triplex)
    1/2    : 42 fps   (20km, same as x3 duplex)
    1/4    : 46 fps   (10km, probably too short)

    Satellites:
        eq_arg_satellite_01_macro - 30k
        eq_arg_satellite_02_macro - 75k

    Ships:
        Defined in libraries/defaults.xml per ship class.
        Note: there is a basic radar node, and a max/radar node, which
        presumably is related to ship mods.
        Radars are normally 40k, maxing at 48k.
    '''
    # Start with defaults.
    defaults_file = Load_File('libraries/defaults.xml')
    defaults_root = defaults_file.Get_Root()
    
    # Scale ranges to meters.
    for class_name, new_range in class_distances.items():
        class_distances[class_name] = new_range * 1000

    # Look for each specified class. This will skip satellites.
    for class_name, new_range in class_distances.items():
        dataset = defaults_root.find(f"./dataset[@class='{class_name}']")
        if dataset == None:
            continue

        # Update range directly.
        radar_node = dataset.find('./properties/radar')
        if radar_node == None:
            continue
        radar_node.set('range', str(new_range))

        # Check if there is a max range.
        max_radar_node = dataset.find('./properties/statistics/max/radar')
        if max_radar_node == None:
            continue
        # Set this at +20%, similar to vanilla.
        new_max = new_range * 1.2
        max_radar_node.set('range', str(f'{new_max:.0f}'))

    defaults_file.Update_Root(defaults_root)


    # Now look for satellites.
    for class_name, new_range in class_distances.items():

        if class_name == 'satellite':
            macro_name = 'eq_arg_satellite_01_macro'
        elif class_name == 'adv_satellite':
            macro_name = 'eq_arg_satellite_02_macro'
        else:
            continue

        # Load the game file and xml.
        sat_file = Load_File(f'assets/props/equipment/satelite/macros/{macro_name}.xml')
        sat_root = sat_file.Get_Root()
        radar_node = sat_root.find(f'./macro[@name="{macro_name}"]/properties/radar')
        radar_node.set('range', str(new_range))        
        sat_file.Update_Root(sat_root)

    return



@Transform_Wrapper(shared_docs = doc_matching_rules)
def Set_Ship_Radar_Ranges(
        *ship_match_rule_ranges,
    ):
    '''
    Sets radar ranges. Defaults are changed per object class. Note: ranges
    below 40km will affect when an unidentified object becomes identified,
    but objects will still show up out to 40km.
        
    * ship_match_rule_ranges:
      - Series of matching rules paired with the new ranges to apply for
        individual ships.
      - Ranges are in km.
    '''
    def Node_Update(ship_macro, new_range):

        # Scale range to meters.
        new_range = new_range * 1000


        # Unclear on how this works.
        # Assuming the ship macro format should match the defaults format,
        # then can try to lay out nodes in the same structure.
        # For safety, add to existing nodes if found.
        prop_node = ship_macro.find('./properties')
        
        range_str = str(new_range)
        radar_node = prop_node.find('./radar')
        if radar_node == None:
            radar_node = Element('radar', range = range_str)
            prop_node.append(radar_node)
            assert radar_node.tail == None, "Radar issue"
        else:
            radar_node.set('range', range_str)

        # Also set up the max radar.
        new_max = new_range * 1.2
        new_max_str = f'{new_max:.0f}'

        stats_node = prop_node.find('./statistics')
        if stats_node == None:
            stats_node = Element('statistics')
            prop_node.append(stats_node)
            
        max_node = stats_node.find('./max')
        if max_node == None:
            max_node = Element('max')
            stats_node.append(max_node)

        max_radar_node = max_node.find('./radar')
        if max_radar_node == None:
            max_radar_node = Element('radar', range = new_max_str)
            max_node.append(max_radar_node)
        else:
            max_radar_node.set('range', new_max_str)
        return True

    # Hand off to shared code to run updates.
    Update_Nodes_By_Rules(ship_match_rule_ranges, Node_Update)
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
           
    database = Database()
    ship_macros = database.Get_Ship_Macros()

    for ship_macro in ship_macros:
        args = Get_Match_Rule_Args(ship_macro, rules)
        if not args:
            continue    
        
        change_occurred = False
        change_occurred |= update_function(ship_macro.xml_node, args)            

        if change_occurred:
            ship_macro.modified = True
            database.Set_Object_Writable(ship_macro)
            
    database.Update_XML()

    return

def Get_Match_Rule_Args(ship_macro, rules):
    '''
    Checks a ship macro against the given rules, and returns args from
    the first matched rule (as a tuple of there is more than 1 arg).
    On no match, returns None.

    * ship_macro
      - The ship macro.
    '''
    # Not all ships have a type or purpose (mainly just spacesuits don't).
    name = ship_macro.name
    class_name = ship_macro.class_name
    type = ship_macro.Get('./properties/ship', 'type')
    purpose = ship_macro.Get('./properties/purpose', 'primary')

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

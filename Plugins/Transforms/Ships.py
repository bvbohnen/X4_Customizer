
from fnmatch import fnmatch
from Framework import Transform_Wrapper, Load_File, File_System
from .Support import Standardize_Match_Rules
from .Support import XML_Multiply_Int_Attribute
from .Support import XML_Multiply_Float_Attribute

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
Ships can only be directly, easily edited for a few fields.
- Speed/turning (by adjusting mass/inertia/drag)
- Crew #
- Missile storage #
- hull
- explosion damage
- maybe default/compatible software

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
    # Put matching rules in standard form.
    rules = Standardize_Match_Rules(match_rule_multipliers)
           
    game_files = File_System.Get_All_Indexed_Files('macros','ship_*')
    for game_file in game_files:
        xml_root = game_file.Get_Root()
        # There may be multiple macros in a file (though generally
        # this isn't expected).
        ship_macros = xml_root.findall('./macro')

        for ship_macro in ship_macros:
            multiplier = Get_Match_Rule_Args(ship_macro, rules)
            if multiplier == None:
                continue

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
                
        # Put the changes back.
        game_file.Update_Root(xml_root)

    return


    
##############################################################################
# Support functions.

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
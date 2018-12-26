'''
Transforms to weapons.

Note: 
Weapon "class" values:
    ['weapon','missilelauncher','turret','missileturret','bomblauncher']
Bullet "class" values:
    ['bullet','missile','bomb','mine','countermeasure']

Notes on reload times:
    There are two basic weapon styles: single shot and burst.
    For single shot weapons:
        fire_rate = 1 / reload_time
    For burst weapons:
        Behavior is tracked in the ammo fields, where the weapon has a
        concept of loading ammo at ammo_reload intervals up to a ammo_max,
        then bursting it out at reload_rate.
        Ammo has to hit max before it can burst, and does a full burst,
        so the overall result is:
        burst_rate = 1 / (ammo_reload_time + 1/reload_rate * (ammo_max-1))

        If ammo_max == 1, then there is no reload_rate contribution
        since there is no time between burst shots, so the result
        is just:
        burst_rate = 1 / ammo_reload_time

        However, the in-game encylopedia seems to mess this up, using
        instead:
        burst_rate = 1 / (ammo_reload_time + 1/(reload_rate * (ammo_max-1)))
        This doesn't make any sense as-is, so consider it a bug.
        -Ingame testing verifies this is a bug.

        
'''
from fnmatch import fnmatch
from Framework import Transform_Wrapper, Load_File, File_System
from .Support import *

doc_matching_rules = '''
    Weapon transforms will commonly use a group of matching rules
    to determine which weapons get modified, and by how much.   

    * Matching rules:
      - These are tuples pairing a matching rule (string) with transform
        defined args, eg. ("key  value", arg0, arg1, ...).
      - The "key" specifies the xml field to look up, which will
        be checked for a match with "value".
      - If a target object matches multiple rules, the first match is used.
      - If a bullet or missile is shared across multiple weapons, only the
        first matched weapon will modify it.
      - Supported keys for weapons:
        - 'name'  : Internal name of the weapon component; supports wildcards.
        - 'class' : The component class.
          - One of: weapon, missilelauncher, turret, missileturret, bomblauncher
          - These are often redundant with tag options.
        - 'tags'  : One or more tags for this weapon, space separated.
          - See Print_Weapon_Stats output for tag listings.
        - '*'     : Matches all wares; takes no value term.

    Examples:
    <code>
        Adjust_Weapon_Range(1.5)
        Adjust_Weapon_Fire_Rate(
            ('name *_mk1', 1.1) )
        Adjust_Weapon_Damage(
            ('name weapon_tel_l_beam_01_mk1', 1.2),
            ('tags large standard turret'   , 1.5),
            ('tags medium missile weapon'   , 1.4),
            ('class bomblauncher'           , 4),
            ('*'                            , 1.1) )
    </code>
    '''

@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Weapon_Damage(
        # Allow multipliers to be given as a loose list of args.
        *match_rule_multipliers
    ):
    '''
    Adjusts damage done by weapons.  If multiple weapons use the same
    bullet or missile, it will be modified for only the first weapon matched.

    * match_rule_multipliers:
      - Series of matching rules paired with the damage multipliers to use.
    '''
    # Iterate through weapons that had matches.
    for weapon, multiplier in Gen_Weapons_Matched_To_Args(match_rule_multipliers):

        # Grab the bullet to be edited.
        bullet_root = weapon.bullet_file.Get_Root()
        Adjust_Bullet_Damage(bullet_root, multiplier)
        
        ## Quick test of fire rates.
        #if bullet_root.find('.//macro').get('name') == 'bullet_gen_s_laser_01_mk1_macro':
        #    ammo_node = bullet_root.find('.//ammunition')
        #    ammo_node.set('value', '14')
        #    print('testing basic laser ammo max upscale')

        # Put the changes back.
        weapon.bullet_file.Update_Root(bullet_root)
    return



@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Weapon_Range(
        # Allow multipliers to be given as a loose list of args.
        *match_rule_multipliers
    ):
    '''
    Adjusts weapon range. Shot speed is unchanged.

    * match_rule_multipliers:
      - Series of matching rules paired with the range multipliers to use.
    '''
    # Iterate through weapons that had matches.
    for weapon, multiplier in Gen_Weapons_Matched_To_Args(match_rule_multipliers):

        # Grab the bullet to be edited.
        bullet_root = weapon.bullet_file.Get_Root()

        # Note: range works somewhat differently for different bullet
        # types.
        # - Beams have range, lifetime, and speed; perhaps lifetime is
        #   just beam minimum duration, and range can be edited directly.
        # - Missiles have range and lifetime; edit range.
        # - Others have lifetime and speed; need to adjust lifetime.

        # Look into the missile or bullet node.
        for tag in ['bullet','missile']:
            node = bullet_root.find('.//'+tag)
            if node == None:
                continue

            # If it has range, edit that.
            if node.get('range') != None:
                XML_Multiply_Float_Attribute(node, 'range', multiplier)
            # Otherwise, edit lifetime.
            elif node.get('lifetime') != None:
                XML_Multiply_Float_Attribute(node, 'lifetime', multiplier)
                
        # Put the changes back.
        weapon.bullet_file.Update_Root(bullet_root)
    return


@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Weapon_Shot_Speed(
        # Allow multipliers to be given as a loose list of args.
        *match_rule_multipliers
    ):
    '''
    Adjusts weapon projectile speed. Range is unchanged.

    * match_rule_multipliers:
      - Series of matching rules paired with the speed multipliers to use.
    '''
    # Iterate through weapons that had matches.
    for weapon, multiplier in Gen_Weapons_Matched_To_Args(match_rule_multipliers):

        # Grab the bullet to be edited.
        bullet_root = weapon.bullet_file.Get_Root()

        # Note: range works somewhat differently for different bullet
        # types.
        # - Beams have range, lifetime, and speed; edit just speed.
        # - Missiles have range and lifetime; edit lifetime?
        # - Others have lifetime and speed; edit speed and adjust lifetime.

        # Look into the missile or bullet node.
        for tag in ['bullet','missile']:
            node = bullet_root.find('.//'+tag)
            if node == None:
                continue

            # Check for all 3 fields.
            if all(x in node.attrib for x in ['range','lifetime','speed']):
                # Edit just speed.
                XML_Multiply_Float_Attribute(node, 'speed', multiplier)

            # Check for range and lifetime.
            elif all(x in node.attrib for x in ['range','lifetime']):
                # Edit just lifetime, reducing it.
                # TODO: test if this works out in game; it's unclear on
                #  how else missile speed is set, unless they have
                #  fixed thrust and uncapped speed and accelerate
                #  based on mass.
                XML_Multiply_Float_Attribute(node, 'lifetime', 1/multiplier)
                
            # Check for speed and lifetime.
            elif all(x in node.attrib for x in ['speed','lifetime']):
                # Bump speed, decrease lifetime.
                XML_Multiply_Float_Attribute(node, 'speed', multiplier)
                XML_Multiply_Float_Attribute(node, 'lifetime', 1/multiplier)
                                
        # Put the changes back.
        weapon.bullet_file.Update_Root(bullet_root)
    return


@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Weapon_Fire_Rate(
        # Allow multipliers to be given as a loose list of args.
        *match_rule_multipliers
    ):
    '''
    Adjusts weapon rate of fire. DPS remains constant.

    * match_rule_multipliers:
      - Series of matching rules paired with the RoF multipliers to use.
    '''
    # Iterate through weapons that had matches.
    for weapon, multiplier in Gen_Weapons_Matched_To_Args(match_rule_multipliers):

        # Grab the bullet to be edited.
        bullet_root = weapon.bullet_file.Get_Root()

        # See notes above on rate of fire calculation.
        # In short, need to edit the 'reload rate', 'reload time',
        # and 'ammunition reload' fields to cover both normal weapons
        # and burst weapons (where bursting rate is a combination of
        # ammo reload and reload rate).

        ammo_node   = bullet_root.find('.//ammunition')
        reload_node = bullet_root.find('.//reload')

        if ammo_node != None and ammo_node.get('reload'):
            # Invert the multiplier to reduce reload time.
            XML_Multiply_Float_Attribute(ammo_node, 'reload', 1/multiplier)

        if reload_node != None and reload_node.get('time'):
            # Invert the multiplier to reduce reload time.
            XML_Multiply_Float_Attribute(reload_node, 'time', 1/multiplier)

        if reload_node != None and reload_node.get('rate'):
            # Keep multiplier as-is.
            XML_Multiply_Float_Attribute(reload_node, 'rate', multiplier)

        # Reduce the damage to compensate.
        Adjust_Bullet_Damage(bullet_root, 1/multiplier)
                                
        # Put the changes back.
        weapon.bullet_file.Update_Root(bullet_root)
    return



# TODO: missile specific transforms that work on missile name instead
# of weapon name.

##############################################################################
# Support functions.


def Adjust_Bullet_Damage(bullet_root, multiplier):
    '''
    Shared function for adjusting a bullet's damage.
    Returns nothing; edits the bullet xml directly.
    '''
    # For damage editing, look for either the damage or explosion_damage
    # node (depending on if normal bullet or missile/mine/bomb).
    for tag in ['damage','explosiondamage']:
        node = bullet_root.find('.//'+tag)
        if node == None:
            continue

        # Adjust all damage attributes (value, hull, shield, repair).
        # Note: these are floats.
        for name in node.keys():
            XML_Multiply_Float_Attribute(node, name, multiplier)
    return


def Gen_Weapons_Matched_To_Args(match_rule_args):
    '''
    Generator that yields tuples of (weapon, args), where args are selected
    based on the weapon matching a rule in match_rule_args.
    The args may be a single value or a list of values.
    A weapon will only be returned if it's bullet hasn't been used by
    by a prior returned weapon.
    Unmatched weapons are not returned.
    '''
    # Track which bullets were seen, to avoid repeats.
    bullets_seen = set()
    # Put matching rules in standard form.
    rules = Standardize_Match_Rules(match_rule_args)

    # Loop over weapons.
    for weapon in Get_All_Weapons():
        # Skip if the bullet seen before.
        if weapon.bullet_file in bullets_seen:
            continue

        args = Get_Match_Rule_Args(weapon, rules)
        # Skip if no match.
        if args == None:
            continue
        
        # Record the bullet. Only do this when a modification will occur.
        bullets_seen.add(weapon.bullet_file)
        yield weapon, args
    return
    

def Get_Match_Rule_Args(weapon, rules):
    '''
    Checks a weapon against the given rules, and returns args from
    the first matched rule (as a tuple of there is more than 1 arg).
    On no match, returns None.
    '''
    # Look up the weapon tags and a couple other properties of interest.
    #weapon_root = weapon.weapon_file.Get_Root_Readonly()
    component_root = weapon.component_file.Get_Root_Readonly()
    name           = component_root[0].get('name')
    class_name     = component_root[0].get('class')
    tags           = weapon.Get_Tags()

    # Check the matching rules.
    for key, value, *args in rules:
        if((key == '*')
        or (key == 'name' and fnmatch(name, value))
        or (key == 'tags' and all(x in tags for x in value.split(' ')))
        or (key == 'class' and class_name == value)):
            # Want to return 1 item is there are 1 arg, else a tuple
            # or list of them. Python has no clean syntax for this
            # that is obvious.
            if len(args) == 1:
                return args[0]
            return args
    return None


class Weapon:
    '''
    Wrapper class which will wrap up basic weapon macro, the related
    bullet macro (missile, mine, etc.), and the related component
    macro (with connection tags). Initializes from the weapon macro
    file.

    Attributes:
    * weapon_file
      - Weapon macro file.
    * bullet_file
      - Bullet macro file.
    * component_file
      - Component file for the weapon.
      - Note: the bullet also has a component, but it isn't of interest
        for now.
    '''
    def __init__(self, weapon_file):
        self.weapon_file = weapon_file

        # Grab the root node.
        root = weapon_file.Get_Root_Readonly()

        # Look up the bullet and component connections.
        bullet_name    = root.find('.//bullet').get('class')
        component_name = root.find('.//component').get('ref')

        self.bullet_file    = File_System.Get_Asset_File(bullet_name)
        self.component_file = File_System.Get_Asset_File(component_name)
        return


    def Get_Tags_Xpath(self):
        '''
        Returns an xpath to the "connection" node holding the main weapon
        "tags" attribute.  If none found, returns None.
        '''
        # Note: this connection doesn't have a standard name, but can
        # be identified by a "component" term in the tags.
        root = self.component_file.Get_Root_Readonly()
        xpath = './/connection[@tags]'
        for connection in root.findall(xpath):
            if 'component' in connection.get('tags'):
                # Add the name of the connection to the xpath to
                # uniquify it.
                name = connection.get('name')
                xpath += '[@name="{}"]'.format(name)
                # Verify it.
                assert root.findall(xpath)[0] is connection
                return xpath
        return None


    def Get_Tags(self):
        '''
        Finds and returns a list of strings holding the primary tags
        for this weapon, or an empty list if tags are not found.
        Pulled from a connection node the component_file.
        If the tags are not found, returns an empty list.
        '''
        xpath = self.Get_Tags_Xpath()
        if xpath == None:
            return []
        root = self.component_file.Get_Root_Readonly()
        connection = root.find(xpath)
        tags_str = connection.get('tags')

        # These appear to always be space separated.
        # Some tag lists have brackets and commas; verify that
        #  isn't the case here.
        assert '[' not in tags_str
        assert ',' not in tags_str
        # Remove any blanks due to excess spaces.
        return [x for x in tags_str.split(' ') if x]

        ## Note: this connection doesn't have a standard name, but can
        ## be identified by a "component" term in the tags.
        #root = self.component_file.Get_Root_Readonly()
        #for connection in root.findall('.//connection[@tags]'):
        #    if 'component' in connection.get('tags'):
        #        tags_str = connection.get('tags')
        #        # These appear to always be space separated.
        #        # Some tag lists have brackets and commas; verify that
        #        #  isn't the case here.
        #        assert '[' not in tags_str
        #        assert ',' not in tags_str
        #        # Remove any blanks due to excess spaces.
        #        return [x for x in tags_str.split(' ') if x]
        #return []


def Get_All_Weapons():
    '''
    Returns a list of Weapon objects, for all discovered weapons.
    Loads files from expected locations.
    Includes various weapon classes: weapon, turret, missileturret, etc.
    '''
    # TODO: consider reading  components.xml and macros.xml for all
    # macro and comp locations, since it pairs names with virtual path.
    # That still leaves open the issue of picking which macros to
    # load initially, and just simplifies bullet and component lookups
    # after the weapon is found.

    # Ensure the related files are loaded in.
    # Weapons/missiles are in one spot, bullets another.
    # Want to load in components as well as macros; most of the
    #  wanted info is in macros, but they can link back to a
    #  component with some tags of interest.
    File_System.Load_Files('assets/props/WeaponSystems/*.xml')
    File_System.Load_Files('assets/fx/weaponFx/*.xml')

    # Grab the weapon macros.
    weapon_files = File_System.Get_Asset_Files_By_Class('macros',
                    'weapon','missilelauncher','turret',
                    'missileturret',
                    'bomblauncher')
    # Wrap into Weapon class objects to fill in links to other xml.
    return [Weapon(x) for x in weapon_files]


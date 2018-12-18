'''
Transforms to weapons.

Note: 
Weapon "class" values:
    ['weapon','missilelauncher','turret','missileturret','bomblauncher']
Bullet "class" values:
    ['bullet','missile','bomb','mine','countermeasure']
'''
from fnmatch import fnmatch
from Framework import Transform_Wrapper, Load_File, File_System, XML_Misc

# TODO: add pattern matching criteria.
'''
What are likely to be the typical cases for customizing damage?
    - globally
    - per weapon, by name
    - all turrets? - use tags
    - by weapon size? - use tags
    - mk1 vs mk2?
While maybe overkill, the Jobs style of matching rules might work
out here.
Note: often times the weapon class (weapon, missileturret, etc.) somewhat
overlaps with the tags (weapon, missile, turret, etc.), but this is
not always true, such as for mines ("mine" class, but no tags).
'''
@Transform_Wrapper()
def Adjust_Weapon_Damage(
        # Allow multipliers to be given as a loose list of args.
        *weapon_multipliers
    ):
    '''
    Adjusts damage done by weapons.  If multiple weapons use the same
    bullet, it will be modified for only the first weapon found.
    Input is a list of matching rules, determining which weapons get adjusted.

    * weapon_multipliers:
      - Tuples holding the matching rules and damage multipliers,
        ("key  value", multiplier).
      - The "key" specifies the job field to look up, which will
        be checked for a match with "value".
      - If a weapon matches multiple entries, the first match is used.
      - Supported keys:
        - 'name'  : Internal name of the weapon component; supports wildcards.
        - 'class' : The component class.
        - 'tags'  : One or more tags for this weapon, space separated.

    Example:
    <code>
        Adjust_Weapon_Damage(
            ('name weapon_tel_l_beam_01_mk1', 1.2),
            ('tags large standard turret'   , 1.5),
            ('tags medium missile weapon'   , 1.4),
            ('class mine'                   , 4),
            ('*'                            , 1.1) )
    </code>
    '''
    # Track which bullets were seen, to avoid repeats.
    bullets_seen = set()
    # Loop over weapons.
    for weapon in Get_All_Weapons():
        if weapon.bullet_file in bullets_seen:
            continue
        bullets_seen.add(weapon.bullet_file)

        # Look up the weapon tags and a couple other properties of interest.
        #weapon_root = weapon.weapon_file.Get_Root_Readonly()
        component_root = weapon.component_file.Get_Root_Readonly()
        name        = component_root[0].get('name')
        class_name  = component_root[0].get('class')
        tags        = weapon.Get_Tags()

        # Check the matching rules.
        multiplier = None
        for rule in weapon_multipliers:
            try:
                key, value = rule[0].split(' ',1)
            except ValueError:
                key, value = rule[0], ''
            value = value.strip()

            if((key == '*')
            or (key == 'name' and fnmatch(name, value))
            or (key == 'tags' and all(x in tags for x in value.split(' ')))
            or (key == 'class' and class_name == value)):
                multiplier = rule[-1]
                break

        # Skip if no match.
        if multiplier == None:
            continue
    
        # Grab the bullet to be edited.
        root = weapon.bullet_file.Get_Root()
        # For damage editing, look for either the damage or explosion_damage
        # node (depending on if normal bullet or missile/mine/bomb).
        for tag in ['damage','explosiondamage']:
            damage = root.find('.//'+tag)

            # If not found for some reason, skip.
            # Normally either damage or explosiondamage will be skipped.
            if damage == None:
                continue

            # Adjust all damage attributes (value, hull, shield, repair).
            # Note: these are floats.
            for name in damage.keys():
                XML_Misc.Multiply_Float_Attribute(damage, name, multiplier)

        # Put the changes back.
        weapon.bullet_file.Update_Root(root)
    return




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

    def Get_Tags(self):
        '''
        Finds and returns a list of strings holding the primary tags
        for this weapon, or an empty list if tags are not found.
        Pulled from a connection node the component_file.
        '''
        # Note: this connection doesn't have a standard name, but can
        # be identified by a "component" term in the tags.
        root = self.component_file.Get_Root_Readonly()
        for connection in root.findall('.//connection[@tags]'):
            if 'component' in connection.get('tags'):
                tags_str = connection.get('tags')
                # These appear to always be space separated.
                # Some tag lists have brackets and commas; verify that
                #  isn't the case here.
                assert '[' not in tags_str
                assert ',' not in tags_str
                # Remove any blanks due to excess spaces.
                return [x for x in tags_str.split(' ') if x]
        return []


def Get_All_Weapons():
    '''
    Returns a list of Weapon objects, for all discovered weapons.
    Loads files from expected locations.
    Includes various weapon classes: weapon, turret, missileturret, etc.
    '''
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
                    'missileturret','bomblauncher')
    # Wrap into Weapon class objects to fill in links to other xml.
    return [Weapon(x) for x in weapon_files]


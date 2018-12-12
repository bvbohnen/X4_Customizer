
from lxml import etree as ET
from collections import defaultdict
from Framework import Analysis_Wrapper, File_System, Settings

@Analysis_Wrapper()
def Print_Weapon_Stats():
    '''
    Gather up all weapon statistics, and print them out.
    Currently only supports csv output.
    Will include changes from enabled extensions.
    '''
    weapons_dict = Collect_Weapons()

    # Categorize by type (eg. 'turret').
    type_weapons_dict_dict = defaultdict(dict)
    for name, weapon in weapons_dict.items():
        type_weapons_dict_dict[weapon.weapon_class][name] = weapon

    # Collect a list of tables (themselves lists of lists).
    table_list = []
    
    # Loop over the types.
    for weapon_type, weapons_dict in sorted(type_weapons_dict_dict.items()):

        # A list of lists will make up the table.
        # First entry is the weapon type.
        # Second entry is the column labels.
        table = []
        table_list.append(table)
        table.append(['weapon_type:',weapon_type])

        # Determine which fields are in use.
        attributes_used = set()
        for weapon in weapons_dict.values():
            for attr_name in dir(weapon):
                if attr_name.startswith('_'):
                    continue
                if getattr(weapon, attr_name) != None:
                    attributes_used.add(attr_name)


        # Pick a display order for the attributes.
        # Preorder a couple fields.
        attributes_list = ['t_name','name']
        # Grab the rest of the attributes in sorted order.
        for name in sorted(attributes_used):
            # Skip some attributes.
            if name in ['t_name_entry']:
                continue
            if name in attributes_list:
                continue
            attributes_list.append(name)
            
        # Record column labels.
        table.append([x for x in attributes_list])

        # Sort the weapons by name and record them.
        for name, weapon in sorted(weapons_dict.items()):
            line = []
            table.append(line)
            for attr_name in attributes_list:
                value = getattr(weapon, attr_name, None)
                # Swap 'none' entries to something nicer (and printable).
                if value == None:
                    value = 'N/A'
                line.append(value)


    # Now pick a format to print to.
    # CSV initially.
    with open(Settings.Get_Output_Folder() / 'weapon_stats.csv', 'w') as file:
        for table in table_list:
            for line in table:
                file.write(', '.join(line) + '\n')
            # Put extra space between tables.
            file.write('\n')

    return


def Collect_Weapons():
    '''
    Returns a dict of Weapon objects, keyed by name.
    '''
    weapon_dict     = {}
    projectile_dict = {}
    
    # Set file search patterns to use.
    # Weapons/missiles are in one spot, bullets another.
    # All of the ones of interest are the macros.
    for pattern in [
        'assets/props/WeaponSystems/*macro.xml',
        'assets/fx/weaponFx/macros/*macro.xml',
        ]:
        for virtual_path in File_System.Get_All_Virtual_Paths(pattern):

            # Load the xml file.
            xml_file = File_System.Load_File(virtual_path)
            # Grab the root node, possibly modified by prior transforms.
            root = xml_file.Get_Root_Readonly()

            # Look up what type of object it is.
            object_class = root.find('.//macro').get('class')
            name         = root.find('.//macro').get('name')

            # Parse it into a class object.
            if object_class in ['weapon','missilelauncher','turret',
                                'missileturret','bomblauncher']:
                weapon = Weapon(root)
                weapon_dict[name] = weapon
            elif object_class in ['bullet','missile','bomb',
                                  'mine','countermeasure']:
                projectile = Projectile(root)
                projectile_dict[name] = projectile
            else:
                # There are also 'effectobject' things; ignore for now.
                pass


    # Connect up the weapons with their projectiles.
    for weapon in weapon_dict.values():
        bullet = projectile_dict[weapon.bullet]

        # Overwrite the bullet field with the bullet name.
        weapon.bullet = bullet.name

        # Collect the bullet attributes into the weapon.
        for attr_name in dir(bullet):
            if attr_name.startswith('_'):
                continue
            # Skip the name.
            if attr_name in ['name']:
                continue
            # Copy over; don't worry about overwrite for now.
            setattr(weapon, attr_name, getattr(bullet, attr_name))


    # Look up the names.
    t_file = File_System.Load_File('t/0001-L044.xml')
    for weapon in weapon_dict.values():
        # Start with no name.
        weapon.t_name = None

        # If a weapon has no t_name_entry, skip it.
        if not hasattr(weapon, 't_name_entry'):
            continue
        # Let the file Read handle the lookup.
        weapon.t_name = t_file.Read(weapon.t_name_entry)

    return weapon_dict
    

def Parse_XML(object, xml_node, lookup_patterns):
    '''
    Parse some xml values into attributes for the object.

    * lookup_patterns
      - List of tuples of (object attribute, xpath, xml node attribute)
    '''
    for weapon_attr, xpath, xml_attr in lookup_patterns:
        node = xml_node.find(xpath)
        # Skip if node not found.
        if node == None:
            continue
        value = node.get(xml_attr)
        # Skip if values not found.
        if value == None:
            continue
        setattr(object, weapon_attr, value)
    return
    

class Weapon:
    '''
    Base class for weapons.    
    '''
    def __init__(self, xml_node):
        Parse_XML(self, xml_node, [
            ('name'          , './/macro'                , 'name'),
            ('weapon_class'  , './/macro'                , 'class'),
            ('t_name_entry'  , './/identification'       , 'name'),
            ('rotation_speed', './/rotationspeed'        , 'max'),
            ('bullet'        , './/bullet'               , 'class'),
            ('hull'          , './/hull'                 , 'max'),
            
            # Typical for lasers.
            ('rotation_acc'  , './/rotationacceleration' , 'max'),
            ('bullet'        , './/bullet'               , 'class'),
            ('overheat'      , './/heat'                 , 'overheat'),
            ('cooldelay'     , './/heat'                 , 'cooldelay'),
            ('coolrate'      , './/heat'                 , 'coolrate'),
            ('reenable'      , './/heat'                 , 'reenable'),

            # For turrets.
            ('reload_rate'   , './/reload'               , 'rate'),
            ('reload_time'   , './/reload'               , 'time'),
            
            # For missile turrets.
            ('ammunition'    , './/ammunition'           , 'tags'),
            ('storage'       , './/storage'              , 'capacity'),
            ])
        

class Projectile:
    '''
    Base class for bullets, missiles, bombs, etc.
    '''
    def __init__(self, xml_node):
        Parse_XML(self, xml_node, [
            # Typical for bullets.
            ('name'                 , './/macro'                , 'name'),
            ('ammunition_value'     , './/ammunition'           , 'value'),
            ('ammunition_reload'    , './/ammunition'           , 'reload'),
            ('speed'                , './/bullet'               , 'speed'),
            ('lifetime'             , './/bullet'               , 'lifetime'),
            ('bullet_amount'        , './/bullet'               , 'amount'),
            ('barrelamount'         , './/bullet'               , 'barrelamount'),
            ('timediff'             , './/bullet'               , 'timediff'),
            ('angle'                , './/bullet'               , 'angle'),
            ('maxhits'              , './/bullet'               , 'maxhits'),
            ('ricochet'             , './/bullet'               , 'ricochet'),
            ('scale'                , './/bullet'               , 'scale'),
            ('attach'               , './/bullet'               , 'attach'),
            ('heat'                 , './/heat'                 , 'value'),
            ('reload_rate'          , './/reload'               , 'rate'),
            ('damage'               , './/damage'               , 'value'),
            ('damage_shield'        , './/damage'               , 'shield'),
            ('damage_repair'        , './/damage'               , 'repair'),
            ('damage_hull'          , './/damage'               , 'hull'),
            
            # Typical for missiles.          
            ('amount'               , './/missile'              , 'amount'),
            ('barrelamount'         , './/missile'              , 'barrelamount'),
            ('lifetime'             , './/missile'              , 'lifetime'),
            ('range'                , './/missile'              , 'range'),
            ('guided'               , './/missile'              , 'guided'),
            ('retarget'             , './/missile'              , 'retarget'),            
            ('damage'               , './/explosiondamage'      , 'value'),
            ('damage_shield'        , './/explosiondamage'      , 'shield'),
            ('damage_hull'          , './/explosiondamage'      , 'hull'),
            ('reload_time'          , './/reload'               , 'time'),
            ('hull_missile'         , './/hull'                 , 'max'),
            ('lock_time'            , './/lock'                 , 'time'),
            ('lock_range'           , './/lock'                 , 'range'),
            ('lock_angle'           , './/lock'                 , 'angle'),
            ('anticounter'          , './/countermeasure'       , 'resilience'),

            # No new fields for bombs.
            # Mines have some stuff for trigger and more range fields;
            # ignore for now.
            ])

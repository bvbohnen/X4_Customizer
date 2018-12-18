
from collections import defaultdict, OrderedDict
from Framework import Analysis_Wrapper, File_System, Settings

from ..Transforms.Weapons import Get_All_Weapons
from .Write_Tables import Write_Tables

@Analysis_Wrapper()
def Print_Weapon_Stats(file_name = 'weapon_stats'):
    '''
    Gather up all weapon statistics, and print them out.
    Currently only supports csv output.
    Will include changes from enabled extensions.

    * file_name
      - String, name to use for generated files, without extension.
      - Defaults to "weapon_stats".
    '''
    weapons_list = Collect_Weapons()

    # Categorize by type (eg. 'turret').
    type_weapons_dict = defaultdict(list)
    for weapon in weapons_list:
        type_weapons_dict[weapon['weapon_class']].append(weapon)

    # Collect a list of tables (themselves lists of lists).
    # One table per weapon class.
    table_list = []
    
    # Loop over the types.
    for weapon_type, weapons_list in sorted(type_weapons_dict.items()):

        # A list of lists will make up the table.
        # First entry is the weapon type.
        # Second entry is the column labels.
        table = []
        table_list.append(table)
        #table.append(['weapon_type:',weapon_type])

        # Determine which fields are in use.
        # Treat '0' as not in use, since in some cases an attribute
        # is always None or 0.
        attributes_used = set()
        for weapon in weapons_list:
            for attr_name, value in weapon.items():
                if value not in [None, '0']:
                    attributes_used.add(attr_name)
        
        # Join the ordered list with the used attributes.
        attributes_to_print = [attr for attr in attribute_names_ordered_dict
                                if attr in attributes_used]
            
        # Record column labels.
        table.append([attribute_names_ordered_dict[x] 
                      for x in attributes_to_print])

        # Sort the weapons by name and record them.
        # TODO: better sorting style.
        for weapon in sorted(weapons_list, key = lambda x: x['t_name']):
            line = []
            table.append(line)
            for attr_name in attributes_to_print:
                # Just use blanks for unused entries.
                # Also, don't print 0's, to declutter the boolean columns.
                value = weapon.get(attr_name, None)
                if value in [None, '0']:
                    value = ''
                line.append(value)

    # Write results.
    Write_Tables(file_name, *table_list)
    return



def Collect_Weapons():
    '''
    Returns a dict of Weapon objects, keyed by name,
    holding various parsed field values of interest.
    '''
    t_file = File_System.Load_File('t/0001-L044.xml')
    
    weapon_fields_list = []
    for weapon in Get_All_Weapons():
        weapon_root = weapon.weapon_file.Get_Root_Readonly()
        bullet_root = weapon.bullet_file.Get_Root_Readonly()

        # Parse out fields of interest, and combine into a single dict.
        weapon_fields = Weapon_Fields(weapon_root)
        bullet_fields = Projectile_Fields(bullet_root)
        weapon_fields.update(bullet_fields)

        # Fill in the name, if there is one.
        if 't_name_entry' not in weapon_fields:
            # Default to the component name.
            weapon_fields['t_name'] = weapon_fields['component']
        else:
            # Let the t-file Read handle the lookup.
            weapon_fields['t_name'] = t_file.Read(weapon_fields['t_name_entry'])
        weapon_fields_list.append(weapon_fields)

    return weapon_fields_list



# TODO: change around the field filling code to be less complicated;
# it really doesn't need classes to hold things.

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
        object[weapon_attr] = value
    return
    

class Weapon_Fields(dict):
    '''
    Base class for weapons; subclassed from dict.
    '''
    def __init__(self, xml_node):
        Parse_XML(self, xml_node, [
            ('codename'             , './/macro'                , 'name'),
            ('weapon_class'         , './/macro'                , 'class'),
            ('t_name_entry'         , './/identification'       , 'name'),
            ('component'            , './/component'            , 'ref'),
            ('rotation_speed'       , './/rotationspeed'        , 'max'),
            ('bullet_codename'      , './/bullet'               , 'class'),
            ('hull'                 , './/hull'                 , 'max'),
            
            # Typical for lasers.
            ('rotation_acceleration', './/rotationacceleration' , 'max'),
            ('heat_overheat'        , './/heat'                 , 'overheat'),
            ('heat_cool_delay'      , './/heat'                 , 'cooldelay'),
            ('heat_cool_rate'       , './/heat'                 , 'coolrate'),
            ('heat_reenable'        , './/heat'                 , 'reenable'),

            # For turrets.
            ('reload_rate'          , './/reload'               , 'rate'),
            ('reload_time'          , './/reload'               , 'time'),
            
            # For missile turrets.
            ('ammunition'           , './/ammunition'           , 'tags'),
            ('storage_capacity'     , './/storage'              , 'capacity'),
            ])
        # TODO: WeaponCon_01 from the parent file (non-macro_ version) to
        # get weapon size.
        

class Projectile_Fields(dict):
    '''
    Base class for bullets, missiles, bombs, etc.
    '''
    def __init__(self, xml_node):
        Parse_XML(self, xml_node, [
            # Typical for bullets.
            ('bullet_codename'           , './/macro'                , 'name'),
            ('ammunition_value'          , './/ammunition'           , 'value'),
            ('ammunition_reload'         , './/ammunition'           , 'reload'),
            ('bullet_speed'              , './/bullet'               , 'speed'),
            ('bullet_lifetime'           , './/bullet'               , 'lifetime'),
            ('bullet_amount'             , './/bullet'               , 'amount'),
            ('bullet_barrel_amount'      , './/bullet'               , 'barrelamount'),
            ('bullet_timediff'           , './/bullet'               , 'timediff'),
            ('bullet_angle'              , './/bullet'               , 'angle'),
            ('bullet_max_hits'           , './/bullet'               , 'maxhits'),
            ('bullet_ricochet'           , './/bullet'               , 'ricochet'),
            ('bullet_scale'              , './/bullet'               , 'scale'),
            ('bullet_attach'             , './/bullet'               , 'attach'),
            ('heat'                      , './/heat'                 , 'value'),
            ('reload_rate'               , './/reload'               , 'rate'),
            ('damage'                    , './/damage'               , 'value'),
            ('damage_shield'             , './/damage'               , 'shield'),
            ('damage_hull'               , './/damage'               , 'hull'),
            ('damage_repair'             , './/damage'               , 'repair'),
            
            # typical for missiles.          
            ('missile_amount'            , './/missile'              , 'amount'),
            ('missile_barrel amount'     , './/missile'              , 'barrelamount'),
            ('missile_lifetime'          , './/missile'              , 'lifetime'),
            ('missile_range'             , './/missile'              , 'range'),
            ('missile_guided'            , './/missile'              , 'guided'),
            ('missile_retarget'          , './/missile'              , 'retarget'),            
            ('damage'                    , './/explosiondamage'      , 'value'),
            ('damage_shield'             , './/explosiondamage'      , 'shield'),
            ('damage_hull'               , './/explosiondamage'      , 'hull'),
            ('reload_time'               , './/reload'               , 'time'),
            ('missile_hull'              , './/hull'                 , 'max'),
            ('lock_time'                 , './/lock'                 , 'time'),
            ('lock_range'                , './/lock'                 , 'range'),
            ('lock_angle'                , './/lock'                 , 'angle'),
            ('counter_resilience'        , './/countermeasure'       , 'resilience'),
            
            # No new fields for bombs.
            # Mines have some stuff for trigger and more range fields;
            # ignore for now.
            ])


attribute_names_ordered_dict = OrderedDict((
    ('t_name'                    , 'Name'),
    ('weapon_class'              , 'Class'),

    #('t_name_entry'              , ''),

    ('reload_time'               , 'Reload Time'),
    ('reload_rate'               , 'Reload Rate'),

    # Ammo values aren't very useful.
    # For missiles, ammo is either dumbfire or guided, but that
    # is captured in missile_guided.
    # Ammo value is always 1 for missiles, None or 999 for weapons.
    # Reload is always 0 or None, except for bomb launcher where it is 2.
    #('ammunition'                , ''),
    #('ammunition_value'          , ''),
    ('ammunition_reload'         , 'Ammo Reload'),
        
    ('damage'                    , 'Damage'),
    ('damage_shield'             , '+Shield'),
    ('damage_hull'               , '+Hull'),
    ('damage_repair'             , '+Repair'),
    
    ('bullet_speed'              , 'Speed'),
    ('bullet_lifetime'           , 'Lifetime'),
    ('bullet_amount'             , 'Amount'),
    ('bullet_barrel_amount'      , 'Barrel Amount'),
    ('bullet_timediff'           , 'Time Diff'),
    ('bullet_angle'              , 'Angle'),
    ('bullet_max_hits'           , 'Max Hits'),
    ('bullet_ricochet'           , 'Ricochet'),
    ('bullet_scale'              , 'Scale'),
    ('bullet_attach'             , 'Attach'),

    ('missile_amount'            , 'Amount'),
    ('missile_barrel amount'     , 'Barrel Amount'),
    ('missile_lifetime'          , 'Lifetime'),
    ('missile_range'             , 'Range'),
    ('missile_guided'            , 'Guided'),
    ('missile_retarget'          , 'Retarget'),
    
    ('missile_hull'              , 'Hull(missile)'),
    ('lock_time'                 , 'Lock Time'),
    ('lock_range'                , 'Lock Range'),
    ('lock_angle'                , 'Lock Angle'),
    ('counter_resilience'        , 'Resiliance'),
    
    ('heat'                      , '+Heat'),
    ('heat_overheat'             , 'Overheat'),
    ('heat_cool_delay'           , 'Cool Delay'),
    ('heat_cool_rate'            , 'Cool Rate'),
    ('heat_reenable'             , 'Reenable'),
    
    ('rotation_speed'            , 'Rot. Speed'),
    ('rotation_acceleration'     , 'Rot. Accel.'),
    ('storage_capacity'          , 'Storage'),
    
    ('hull'                      , 'Hull'),
    ('codename'                  , 'Weapon Codename'),
    ('bullet_codename'           , 'Bullet Codename'),
))
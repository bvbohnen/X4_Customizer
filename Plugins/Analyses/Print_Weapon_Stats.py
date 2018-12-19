
from collections import defaultdict, OrderedDict
from Framework import Analysis_Wrapper, File_System, Settings

from ..Transforms.Weapons import Get_All_Weapons
from .Write_Tables import Write_Tables
from ..Transforms.Support import Float_to_String

@Analysis_Wrapper()
def Print_Weapon_Stats(file_name = 'weapon_stats'):
    '''
    Gather up all weapon statistics, and print them out.
    Produces csv and html output.
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
    
    # Loop over the types, in selective ordering.
    for weapon_class in ['weapon','turret','missilelauncher','missileturret','bomblauncher']:
        weapons_list = type_weapons_dict[weapon_class]

        # A list of lists will make up the table.
        # First entry is the weapon type.
        # Second entry is the column labels.
        table = []
        table_list.append(table)

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

        # Add in weapon tags specially.
        weapon_fields['tags'] = str(weapon.Get_Tags())

        # Fill in the name, if there is one.
        if 't_name_entry' not in weapon_fields:
            # Default to the component name.
            weapon_fields['t_name'] = weapon_fields['component']
        else:
            # Let the t-file Read handle the lookup.
            weapon_fields['t_name'] = t_file.Read(weapon_fields['t_name_entry'])
        weapon_fields_list.append(weapon_fields)


        # Calculations:

        # Start with filling out rate of fire.
        reload_rate      = weapon_fields.get('reload_rate')
        reload_time      = weapon_fields.get('reload_time')
        ammo_reload_time = weapon_fields.get('ammunition_reload')
        ammo_cap         = weapon_fields.get('ammunition_value')

        # If only reload_rate available, use it directly.
        if reload_rate and not reload_time and not ammo_reload_time:
            weapon_fields['fire_rate'] = reload_rate

        # If only reload_time available, invert it and use.
        if not reload_rate and reload_time and not ammo_reload_time:
            weapon_fields['fire_rate'] = Float_to_String(1/float(reload_time))

        # If reload_rate and ammo_reload_time available, mix them.
        if reload_rate and not reload_time and ammo_reload_time:
            # Note: game calculates this wrongly as of ~1.5, multiplying
            # the ammo_cap-1 by reload_rate instead of 1/reload_rate.
            # This will do it correctly.
            burst_time = 1/float(reload_rate) * (float(ammo_cap)-1)
            time = float(ammo_reload_time) + burst_time
            weapon_fields['fire_rate'] = Float_to_String(1/time)


        # Fill in range.
        if not weapon_fields.get('range'):
            # Can compute from lifetime and speed.
            lifetime = weapon_fields.get('lifetime')
            speed    = weapon_fields.get('speed')
            if lifetime and speed:
                weapon_fields['range'] = Float_to_String(float(lifetime) * float(speed))


        # Fill in burst dps.
        fire_rate     = weapon_fields.get('fire_rate')
        damage        = weapon_fields.get('damage')
        damage_s      = weapon_fields.get('damage_shield')
        damage_h      = weapon_fields.get('damage_hull')
        damage_r      = weapon_fields.get('damage_repair')
        bullet_amount = weapon_fields.get('amount')
        if fire_rate:
            multiplier = float(fire_rate)
            if bullet_amount:
                multiplier *= float(bullet_amount)
            if damage:
                weapon_fields['dps']   = Float_to_String(multiplier * float(damage))
            if damage_s:
                weapon_fields['dps_s'] = Float_to_String(multiplier * float(damage_s))
            if damage_h:
                weapon_fields['dps_h'] = Float_to_String(multiplier * float(damage_h))
            if damage_r:
                weapon_fields['dps_r'] = Float_to_String(multiplier * float(damage_r))


        # Compute heat limited dps.
        # TODO



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
            ('speed'                     , './/bullet'               , 'speed'),
            ('lifetime'                  , './/bullet'               , 'lifetime'),
            ('range'                     , './/bullet'               , 'range'),
            ('amount'                    , './/bullet'               , 'amount'),
            ('barrel_amount'             , './/bullet'               , 'barrelamount'),
            ('bullet_timediff'           , './/bullet'               , 'timediff'),
            ('bullet_angle'              , './/bullet'               , 'angle'),
            ('bullet_max_hits'           , './/bullet'               , 'maxhits'),
            ('bullet_ricochet'           , './/bullet'               , 'ricochet'),
            ('bullet_scale'              , './/bullet'               , 'scale'),
            ('bullet_attach'             , './/bullet'               , 'attach'),
            ('heat'                      , './/heat'                 , 'value'),
            ('reload_rate'               , './/reload'               , 'rate'),
            ('reload_time'               , './/reload'               , 'time'),
            ('damage'                    , './/damage'               , 'value'),
            ('damage_shield'             , './/damage'               , 'shield'),
            ('damage_hull'               , './/damage'               , 'hull'),
            ('damage_repair'             , './/damage'               , 'repair'),
            
            # typical for missiles.          
            ('amount'                    , './/missile'              , 'amount'),
            ('barrel_amount'             , './/missile'              , 'barrelamount'),
            ('lifetime'                  , './/missile'              , 'lifetime'),
            ('range'                     , './/missile'              , 'range'),
            ('missile_guided'            , './/missile'              , 'guided'),
            ('missile_retarget'          , './/missile'              , 'retarget'),
            ('damage'                    , './/explosiondamage'      , 'value'),
            ('damage_shield'             , './/explosiondamage'      , 'shield'),
            ('damage_hull'               , './/explosiondamage'      , 'hull'),
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

    #('t_name_entry'              , ''),

    ('dps'                       , 'DPS'),
    ('dps_s'                     , '+Shield'),
    ('dps_h'                     , '+Hull'),
    ('dps_r'                     , '+Repair'),


    # For missiles, ammo is either dumbfire or guided, but that
    # is captured in missile_guided.
    #('ammunition'                , ''),

        
    ('fire_rate'                 , 'Fire Rate'),    
    ('speed'                     , 'Speed'),
    ('range'                     , 'Range'),
    ('lifetime'                  , 'Lifetime'),
    
    ('damage'                    , 'Damage'),
    ('damage_shield'             , '+Shield'),
    ('damage_hull'               , '+Hull'),
    ('damage_repair'             , '+Repair'),

    ('reload_time'               , 'Reload Time'),
    ('reload_rate'               , 'Reload Rate'),
    ('ammunition_reload'         , 'Ammo Reload'),
    ('ammunition_value'          , 'Max Ammo'),

    ('amount'                    , 'Amount'),
    ('barrel_amount'             , 'Barrel Amount'),

    ('bullet_timediff'           , 'Time Diff'),
    ('bullet_angle'              , 'Angle'),
    ('bullet_max_hits'           , 'Max Hits'),
    ('bullet_ricochet'           , 'Ricochet'),
    ('bullet_scale'              , 'Scale'),
    ('bullet_attach'             , 'Attach'),

    # TODO: compute speed.
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
    ('weapon_class'              , 'Class'),
    ('codename'                  , 'Weapon Codename'),
    ('bullet_codename'           , 'Bullet Codename'),
    ('tags'                      , 'Tags'),
))

from itertools import chain
from collections import OrderedDict, defaultdict

from Framework import File_System, Settings
# Do a lazy import of classes from support.
from .Support import *
from ...Transforms.Weapons import Get_All_Weapons
from ...Transforms.Support import Float_to_String


def Get_Weapon_Bullet_Edit_Objects():
    '''
    Returns a list of Edit_Objects for all weapons.
    All created edit_objects for weapons and bullets are added to
    the Live_Editor.
    '''
    t_file = File_System.Load_File('t/0001-L044.xml')

    # Get the weapon collection objects, that hold the
    # file references to the weapon, its component, and its bullet.
    weapons = Get_All_Weapons()

    # First pass will just fill in bullet objects,
    # making them available during weapon lookups on the next pass.
    # Be careful to make each bullet once.
    for weapon in weapons:

        name = weapon.bullet_file.asset_name
        # Skip if the bullet already recorded.
        if Live_Editor.Get_Object(name) != None:
            continue

        # Create an Edit_Object for the bullet.
        # Use the asset name from the bullet file.
        bullet_edit_object = Edit_Object(name)

        # Fill in its edit items.
        bullet_edit_object.Make_Edit_Items(
            weapon.bullet_file,
            bullet_xpath_fields)

        # Fill in bullet specific display items.
        # These are ones that can be computed independent of the
        # weapon firing the bullet.
        bullet_edit_object.Make_Display_Items(
            bullet_display_fields)

        # Record it in the Live_Editor.
        Live_Editor.Add_Object(bullet_edit_object)


    # Now do a pass for the weapons themselves.
    weapon_edit_objects = []
    for weapon in weapons:
        
        name = weapon.weapon_file.asset_name

        # Reuse a prior version if the weapon already recorded.
        prior_object = Live_Editor.Get_Object(name) 
        if prior_object != None:            
            weapon_edit_objects.append(prior_object)
            continue

        # Create an Edit_Object for the weapon.
        weapon_edit_object = Edit_Object(name)

        # Fill in its normal edit items.
        weapon_edit_object.Make_Edit_Items(
            weapon.weapon_file,
            weapon_xpath_fields)


        # Also add extra bits from its components file.
        # These field lists need to fill in the connection node xpath term.
        connection_xpath = weapon.Get_Tags_Xpath()
        this_weapon_component_xpath_fields = []
        for entry in weapon_component_xpath_fields:
            this_entry = [x.replace('connection_xpath', connection_xpath)
                            if isinstance(x, str) else x 
                            for x in entry]
            this_weapon_component_xpath_fields.append(entry)
        
        weapon_edit_object.Make_Edit_Items(
            weapon.component_file,
            this_weapon_component_xpath_fields)


        # Look up the reference bullet file and link to it.
        weapon_edit_object.Add_Reference(
            Live_Editor.Get_Object(weapon.bullet_file.asset_name))

        # Fill in display items, that can pull from the weapon, bullet
        # or component.
        weapon_edit_object.Make_Display_Items(weapon_display_fields)

        # Record it, to the return list and the Live_Editor.
        weapon_edit_objects.append(weapon_edit_object)
        Live_Editor.Add_Object(weapon_edit_object)
        

    # Can now return the weapon edit objects.
    return weapon_edit_objects



# Various custom Display_Items.
# These will be organized as subclasses rather than groups of functions,
# since it is easier to track dependencies and collect display vs edit
# functions this way.

def Display_Update_Weapon_Name(
        t_name_entry,
        component
    ):
    # If no t_name_entry available, use the component name.
    if not t_name_entry:
        return component
    else:
        t_file = File_System.Load_File('t/0001-L044.xml')
        # Let the t-file Read handle the lookup.
        return t_file.Read(t_name_entry)


def Display_Update_Bullet_RoF(
        reload_rate, 
        reload_time,
        ammunition_reload_time,
        ammunition_rounds
    ):
    # If only reload_rate available, use it directly.
    if reload_rate and not reload_time and not ammunition_reload_time:
        return reload_rate

    # If only reload_time available, invert it and use.
    if not reload_rate and reload_time and not ammunition_reload_time:
        return Float_to_String(1/float(reload_time))

    # If reload_rate and ammunition_reload_time available, mix them.
    if reload_rate and not reload_time and ammunition_reload_time:
        # Note: game calculates this wrongly as of ~1.5, multiplying
        # the ammunition_rounds-1 by reload_rate instead of 1/reload_rate.
        # This will do it correctly.
        burst_time = 1/float(reload_rate) * (float(ammunition_rounds)-1)
        time = float(ammunition_reload_time) + burst_time
        return Float_to_String(1/time)

    # If here, it is unknown.
    return ''


def Display_Update_Bullet_Range(
        lifetime,
        speed
    ):
    if lifetime and speed:
        return Float_to_String(float(lifetime) * float(speed))
    return ''


def Display_Update_Bullet_Burst_DPS(
        fire_rate,
        damage,
        amount,
    ):
    if fire_rate and damage:
        multiplier = float(fire_rate)
        if amount:
            multiplier *= float(amount)
        return Float_to_String(multiplier * float(damage))
    return ''
    
def Display_Update_Bullet_Burst_DPS_Shield(
        fire_rate,
        damage_shield,
        amount,
    ):
    if fire_rate and damage_shield:
        multiplier = float(fire_rate)
        if amount:
            multiplier *= float(amount)
        return Float_to_String(multiplier * float(damage_shield))
    return ''

def Display_Update_Bullet_Burst_DPS_Hull(
        fire_rate,
        damage_hull,
        amount,
    ):
    if fire_rate and damage_hull:
        multiplier = float(fire_rate)
        if amount:
            multiplier *= float(amount)
        return Float_to_String(multiplier * float(damage_hull))
    return ''

def Display_Update_Bullet_Burst_DPS_Repair(
        fire_rate,
        damage_repair,
        amount,
    ):
    if fire_rate and damage_repair:
        multiplier = float(fire_rate)
        if amount:
            multiplier *= float(amount)
        return Float_to_String(multiplier * float(damage_repair))
    return ''



# Fields from the weapon macro file to look for and convert to Edit_Items.
# Given as (local name, xpath to node, attribute name, display name).
weapon_xpath_fields = [
    ('t_name_entry'         , './/identification'       , 'name'      ),
    ('codename'             , './macro'                 , 'name'      , {'read_only': True}),
    ('weapon_class'         , './macro'                 , 'class'     ),
    ('component'            , './/component'            , 'ref'       ),
    ('rotation_speed'       , './/rotationspeed'        , 'max'       ),
    ('bullet_codename'      , './/bullet'               , 'class'     , {'read_only': True}),
    ('hull'                 , './/hull'                 , 'max'       ),

    # Typical for lasers.
    ('rotation_acceleration', './/rotationacceleration' , 'max'       ),
    ('heat_overheat'        , './/heat'                 , 'overheat'  ),
    ('heat_cool_delay'      , './/heat'                 , 'cooldelay' ),
    ('heat_cool_rate'       , './/heat'                 , 'coolrate'  ),
    ('heat_reenable'        , './/heat'                 , 'reenable'  ),

    # For turrets.
    ('reload_rate'          , './/reload'               , 'rate'      ),
    ('reload_time'          , './/reload'               , 'time'      ),

    # For missile turrets.
    ('ammunition'           , './/ammunition'           , 'tags'      ),
    ('storage_capacity'     , './/storage'              , 'capacity'  ),
    ]


# Components will have a blank term in their xpath, needing
# to be filled in from parsing the weapon xml.
weapon_component_xpath_fields = [
    ('connection_name'       , 'connection_xpath'       , 'name'  , {'read_only': True}),
    ('connection_tags'       , 'connection_xpath'       , 'tags'  , {'read_only': True}),
    ]

# Fields that will be Display_Items, computing their value from other items.
weapon_display_fields = [
    ('name'           , Display_Update_Weapon_Name      ),
    ]

# Xpath and display fields for bullets/missiles/etc., taken from
# the bullet macro file.
bullet_xpath_fields = [
    # Typical for bullets.
    ('bullet_codename'           , './macro'            , 'name'         ),
    ('ammunition_rounds'         , './/ammunition'      , 'value'        ),
    ('ammunition_reload_time'    , './/ammunition'      , 'reload'       ),
    ('speed'                     , './/bullet'          , 'speed'        ),
    ('lifetime'                  , './/bullet'          , 'lifetime'     ),
    ('range'                     , './/bullet'          , 'range'        ),
    ('amount'                    , './/bullet'          , 'amount'       ),
    ('barrel_amount'             , './/bullet'          , 'barrelamount' ),
    ('bullet_timediff'           , './/bullet'          , 'timediff'     ),
    ('bullet_angle'              , './/bullet'          , 'angle'        ),
    ('bullet_max_hits'           , './/bullet'          , 'maxhits'      ),
    ('bullet_ricochet'           , './/bullet'          , 'ricochet'     ),
    ('bullet_scale'              , './/bullet'          , 'scale'        ),
    ('bullet_attach'             , './/bullet'          , 'attach'       ),
    ('heat'                      , './/heat'            , 'value'        ),
    ('reload_rate'               , './/reload'          , 'rate'         ),
    ('reload_time'               , './/reload'          , 'time'         ),
    ('damage'                    , './/damage'          , 'value'        ),
    ('damage_shield'             , './/damage'          , 'shield'       ),
    ('damage_hull'               , './/damage'          , 'hull'         ),
    ('damage_repair'             , './/damage'          , 'repair'       ),
            
    # typical for missiles.          
    ('amount'                    , './/missile'         , 'amount'       ),
    ('barrel_amount'             , './/missile'         , 'barrelamount' ),
    ('lifetime'                  , './/missile'         , 'lifetime'     ),
    ('range'                     , './/missile'         , 'range'        ),
    ('missile_guided'            , './/missile'         , 'guided'       ),
    ('missile_retarget'          , './/missile'         , 'retarget'     ),
    ('damage'                    , './/explosiondamage' , 'value'        ),
    ('damage_shield'             , './/explosiondamage' , 'shield'       ),
    ('damage_hull'               , './/explosiondamage' , 'hull'         ),
    ('missile_hull'              , './/hull'            , 'max'          ),
    ('lock_time'                 , './/lock'            , 'time'         ),
    ('lock_range'                , './/lock'            , 'range'        ),
    ('lock_angle'                , './/lock'            , 'angle'        ),
    ('counter_resilience'        , './/countermeasure'  , 'resilience'   ),
    ]

bullet_display_fields = [
    ('fire_rate'      , Display_Update_Bullet_RoF                ),
    ('range'          , Display_Update_Bullet_Range              ),
    ('dps_base'       , Display_Update_Bullet_Burst_DPS          ),
    ('dps_shield'     , Display_Update_Bullet_Burst_DPS_Shield   ),
    ('dps_hull'       , Display_Update_Bullet_Burst_DPS_Hull     ),
    ('dps_repair'     , Display_Update_Bullet_Burst_DPS_Repair   ),
    ]



def _Get_Weapon_Edit_Table_Group():
    '''
    Returns a new Edit_Table_Group holding the Edit_Tables for the
    different weapon types.  Intended for direct call from the Live_Editor;
    other users should get it from there.
    '''
    name = 'weapons'

    # Set up a new table and record it.
    edit_table_group = Edit_Table_Group('weapons')

    # Get all of the weapon objects.
    weapon_objects = Get_Weapon_Bullet_Edit_Objects()

    # Organize by weapon_class.
    class_objects_dict = defaultdict(list)
    for weapon_object in weapon_objects:
        # TODO: think about which value version to use, vanilla or
        # patched or edited. Go with 'current', which will start
        # the same as patched but swaps to edited or the post-transform
        # state after a script run.
        class_objects_dict[ weapon_object
                           .Get_Item('weapon_class')
                           .Get_Value('current') ] .append( weapon_object )

    # Create a table for each weapon class, alphabetical order for now.
    for weapon_class, weapon_objects in sorted(class_objects_dict.items()):

        # Set up a new table.
        edit_table = Edit_Table(weapon_class)
        edit_table_group.Add_Table(edit_table)

        # Give it all the weapon objects, sorted in name order.
        for weapon_object in sorted(
                weapon_objects, 
                key = lambda x: x.Get_Item('name').Get_Value('current')):
            edit_table.Add_Object(weapon_object)

        # Set the name ordering. This will be the same for all tables,
        # since the Edit_Table will trim out unused fields.

        # Lay out the display name ordering.
        edit_table.item_names_ordered_dict = OrderedDict([
            ('name'                      , 'Name'),
            ('t_name_entry'              , 'T Name Entry'),

            ('dps_base'                  , 'DPS'),
            ('dps_shield'                , '+Shield'),
            ('dps_hull'                  , '+Hull'),
            ('dps_repair'                , '+Repair'),


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
            ('ammunition_reload_time'    , 'Interburst Time'),
            ('ammunition_rounds'         , 'Burst Rounds'),

            ('amount'                    , 'Bullet Amount'),
            ('barrel_amount'             , 'Bullet Barrel Amount'),

            ('bullet_timediff'           , 'Bullet Time Diff'),
            ('bullet_angle'              , 'Bullet Angle'),
            ('bullet_max_hits'           , 'Bullet Max Hits'),
            ('bullet_ricochet'           , 'Bullet Ricochet'),
            ('bullet_scale'              , 'Bullet Scale'),
            ('bullet_attach'             , 'Bullet Attach'),

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
        ])

    return edit_table_group


# Register the builder function with the editor.
Live_Editor.Record_Table_Group_Builder(
    'weapons', _Get_Weapon_Edit_Table_Group)
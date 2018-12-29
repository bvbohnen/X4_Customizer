

from itertools import chain
from collections import OrderedDict, defaultdict

from Framework import File_System, Settings
from Framework.Live_Editor_Components import *

# Convenience macro renaming.
E = Edit_Item_Macro
D = Display_Item_Macro

# TODO: maybe remove dependency on the Weapons transform code.
from ...Transforms.Weapons import Get_All_Weapons
from ...Transforms.Support import Float_to_String


def _Build_Bullet_Objects():
    '''
    Generates Edit_Objects for all found bullets.
    Meant for calling from the Live_Editor.
    '''
    t_file = File_System.Load_File('t/0001-L044.xml')
    
    # Look up bullet files.
    # These can be in two locations.
    File_System.Load_Files('assets/props/WeaponSystems/*.xml')
    File_System.Load_Files('assets/fx/weaponFx/*.xml')
    bullet_files = File_System.Get_Asset_Files_By_Class('macros',
                    'bullet','missile','bomb','mine','countermeasure')
    
    for bullet_file in bullet_files:
        name = bullet_file.asset_name

        # Create an Edit_Object for the bullet.
        # Use the asset name from the bullet file.
        bullet_edit_object = Edit_Object(name)

        # Fill in its edit items.
        bullet_edit_object.Make_Items(bullet_file, bullet_item_macros)
        
        # Send it back to the live editor for recording.
        yield bullet_edit_object
    return


def _Build_Weapon_Objects():
    '''
    Generates Edit_Objects for all found weapons.
    Meant for calling from the Live_Editor.
    '''
    t_file = File_System.Load_File('t/0001-L044.xml')
    
    # Get the weapon collection objects, that hold the
    # file references to the weapon, its component, and its bullet.
    # Note: bullet links may get outdated, so this is mostly used
    # for the weapon/component link logic.
    # TODO: localize the wanted logic.
    weapons = Get_All_Weapons()

    # Make sure the bullets are created, so they can be referenced.
    Live_Editor.Get_Category_Objects('bullets')

    for weapon in weapons:        
        name = weapon.weapon_file.asset_name
        
        # Create an Edit_Object for the weapon.
        weapon_edit_object = Edit_Object(name)

        # Fill in its normal edit items.
        weapon_edit_object.Make_Items(weapon.weapon_file, weapon_item_macros)
               
        # Also add extra bits from its components file.
        # These macros need to fill in the connection node xpath term.
        weapon_edit_object.Make_Items(
            weapon.component_file,
            weapon_component_item_macros, 
            xpath_replacements = {'connection_xpath' : weapon.Get_Tags_Xpath()})
        
        ## Look up the reference bullet file and link to it.
        ## TODO: update this to be version specific, or just to let some
        ## special Edit_Ref_Item objects handle it somehow automatically.
        #bullet_object = Live_Editor.Get_Object('bullets', weapon.bullet_file.asset_name)
        #for version in ['vanilla','patched','current','edited']:
        #    weapon_edit_object.Add_Reference(version, bullet_object)
            
        # Send it back to the live editor for recording.
        yield weapon_edit_object

    return


# Various custom Display_Items.
# These will be organized as subclasses rather than groups of functions,
# since it is easier to track dependencies and collect display vs edit
# functions this way.

def Display_Update_Weapon_Name(
        t_name_entry,
        component
    ):
    'Look up weapon name.'
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
    'Calculate rate of fire. TODO: turret weapon fire rate terms.'
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
        bullet_lifetime,
        bullet_speed,
        bullet_range
    ):
    'Update range. TODO: missile range.'
    # Use bullet range if given, else compute.
    if bullet_range:
        return bullet_range
    if bullet_lifetime and bullet_speed:
        return Float_to_String(float(bullet_lifetime) * float(bullet_speed))
    return ''


def _Merge(a,b):
    'Pick either of two values that is not empty, if possible.'
    return a if a else b if b else ''

def Display_Update_Bullet_Merged_Damage( damage, explosion_damage ):
    'Merge bullet and explosion damage, for later compute.'
    return _Merge(damage, explosion_damage)

def Display_Update_Bullet_Merged_Damage_Shield( damage_shield, explosion_damage_shield ):
    'Merge bullet and explosion damage, for later compute.'
    return _Merge(damage_shield, explosion_damage_shield)

def Display_Update_Bullet_Merged_Damage_Hull( damage_hull, explosion_damage_hull ):
    'Merge bullet and explosion damage, for later compute.'
    return _Merge(damage_hull, explosion_damage_hull)

def Display_Update_Bullet_Merged_Amount( amount, missile_amount ):
    'Merge bullet and missile amount, for later compute.'
    return _Merge(amount, missile_amount)


def _Calc_Dps(fire_rate, damage, amount):
    'Shared dps calculation code.'
    if fire_rate and damage:
        multiplier = float(fire_rate)
        if amount:
            multiplier *= float(amount)
        return Float_to_String(multiplier * float(damage))
    return ''


def Display_Update_Bullet_Burst_DPS(
        fire_rate,
        merge_damage,
        damage_repair,
        merge_amount,
    ):
    'Calculate burst dps (ignoring heat).'
    # No damage if this is a repair weapon.
    return '' if damage_repair == '1' else _Calc_Dps(fire_rate, merge_damage, merge_amount)

def Display_Update_Bullet_Burst_DPS_Shield(
        fire_rate,
        merge_damage_shield,
        damage_repair,
        merge_amount,
    ):
    'Calculate burst shield dps (ignoring heat).'
    return '' if damage_repair == '1' else _Calc_Dps(fire_rate, merge_damage_shield, merge_amount)

def Display_Update_Bullet_Burst_DPS_Hull(
        fire_rate,
        merge_damage_hull,
        damage_repair,
        merge_amount,
    ):
    'Calculate burst hull dps (ignoring heat).'
    return '' if damage_repair == '1' else _Calc_Dps(fire_rate, merge_damage_hull, merge_amount)

def Display_Update_Bullet_Repair_Rate(
        fire_rate,
        merge_damage_hull,
        damage_repair,
        merge_amount,
    ):
    'Calculate burst repair rate (ignoring heat).'
    # Use the hull damage field for repair amount.
    return '' if damage_repair != '1' else _Calc_Dps(fire_rate, merge_damage_hull, merge_amount)



# Fields from the weapon macro file to look for and convert to Edit_Items.
weapon_item_macros = [
    D('name'                 , Display_Update_Weapon_Name                 , 'Name', ''),
    E('t_name_entry'         , './/identification'       , 'name'         , 'T Name Entry', ''),
    E('codename'             , './macro'                 , 'name'         , 'Weapon Codename', '', read_only = True),
    E('weapon_class'         , './macro'                 , 'class'        , 'Class', '', read_only = True),
    # TODO: should this be treated as a reference, and component files
    # parsed as separate objects?
    E('component'            , './/component'            , 'ref'          , 'Component', '', read_only = True, hidden = True),
    E('rotation_speed'       , './/rotationspeed'        , 'max'          , 'Rot. Speed', ''),
    E('rotation_acceleration', './/rotationacceleration' , 'max'          , 'Rot. Accel.', ''),

    E('heat_overheat'        , './/heat'                 , 'overheat'     , 'Overheat', 'Max heat before firing stops'),
    E('heat_cool_delay'      , './/heat'                 , 'cooldelay'    , 'Cool Delay', ''),
    E('heat_cool_rate'       , './/heat'                 , 'coolrate'     , 'Cool Rate', ''),
    E('heat_reenable'        , './/heat'                 , 'reenable'     , 'Reenable', 'Time to start firing again after overheating'),

    E('reload_rate'          , './/reload'               , 'rate'         , 'Reload Rate', ''),
    E('reload_time'          , './/reload'               , 'time'         , 'Reload Time', ''),

    E('hull'                 , './/hull'                 , 'max'          , 'Hull', ''),
    E('ammunition_tags'      , './/ammunition'           , 'tags'         , 'Ammo Tags', ''),
    E('storage_capacity'     , './/storage'              , 'capacity'     , 'Storage', ''),

    E('bullet_codename'      , './/bullet'               , 'class'        , 'Bullet Codename (ref)', '',  is_reference = True),
    ]


# Components will have a blank term in their xpath, needing
# to be filled in from parsing the weapon xml.
weapon_component_item_macros = [
    E('connection_name'       , 'connection_xpath'       , 'name'         , 'Connection Name', ''  , read_only = True),
    E('connection_tags'       , 'connection_xpath'       , 'tags'         , 'Connection Tags', ''  , read_only = True),
    ]

bullet_item_macros = [
    D('dps_base'                  , Display_Update_Bullet_Burst_DPS       , 'DPS', ''),
    D('dps_shield'                , Display_Update_Bullet_Burst_DPS_Shield, '+Shield', ''),
    D('dps_hull'                  , Display_Update_Bullet_Burst_DPS_Hull  , '+Hull', ''),
    D('repair_rate'               , Display_Update_Bullet_Repair_Rate     , 'Repair Rate', ''),
    D('fire_rate'                 , Display_Update_Bullet_RoF             , 'Rate of Fire', ''),
    D('range'                     , Display_Update_Bullet_Range           , 'Range', ''),

    E('damage'                    , './/damage'          , 'value'        , 'Damage', ''),
    E('damage_shield'             , './/damage'          , 'shield'       , '+Shield', ''),
    E('damage_hull'               , './/damage'          , 'hull'         , '+Hull', ''),
    E('damage_repair'             , './/damage'          , 'repair'       , 'Repair', 'Set to 1 to flip to repairing.'),
    E('reload_rate'               , './/reload'          , 'rate'         , 'Reload Rate', 'For burst weapons, time between shots in the burst'),
    E('reload_time'               , './/reload'          , 'time'         , 'Reload Time', 'For non-burst weapons, time between shots'),
    E('ammunition_rounds'         , './/ammunition'      , 'value'        , 'Burst Rounds', 'For burst weapons, number of shots per burst.'),
    E('ammunition_reload_time'    , './/ammunition'      , 'reload'       , 'Interburst Time', 'For burst weapons, time from the end of a burst to the start of the next.'),
    E('bullet_speed'              , './/bullet'          , 'speed'        , 'Bullet Speed', ''),
    E('bullet_lifetime'           , './/bullet'          , 'lifetime'     , 'Bullet Lifetime', ''),
    E('bullet_range'              , './/bullet'          , 'range'        , 'Bullet Range', ''),

    E('heat'                      , './/heat'            , 'value'        , '+Heat', 'Heat added per bullet (or burst of bullets)'),
    E('bullet_amount'             , './/bullet'          , 'amount'       , 'Bullet Amount', ''),
    E('barrel_amount'             , './/bullet'          , 'barrelamount' , 'Bullet Barrel Amount', ''),
    E('bullet_timediff'           , './/bullet'          , 'timediff'     , 'Bullet Time Diff', ''),
    E('bullet_angle'              , './/bullet'          , 'angle'        , 'Bullet Angle', ''),
    E('bullet_max_hits'           , './/bullet'          , 'maxhits'      , 'Bullet Max Hits', ''),
    E('bullet_ricochet'           , './/bullet'          , 'ricochet'     , 'Bullet Ricochet', ''),
    E('bullet_scale'              , './/bullet'          , 'scale'        , 'Bullet Scale', ''),
    E('bullet_attach'             , './/bullet'          , 'attach'       , 'Bullet Attach', ''),

    E('explosion_damage'          , './/explosiondamage' , 'value'        , 'Explosion Damage', ''),
    E('explosion_damage_shield'   , './/explosiondamage' , 'shield'       , 'Explosion +Shield', ''),
    E('explosion_damage_hull'     , './/explosiondamage' , 'hull'         , 'Explosion +Hull', ''),
    E('missile_amount'            , './/missile'         , 'amount'       , 'Missile Amount', ''),
    E('missile_barrel_amount'     , './/missile'         , 'barrelamount' , 'Missile Barrel Amount', ''),
    E('missile_lifetime'          , './/missile'         , 'lifetime'     , 'Missile Lifetime', ''),
    E('missile_range'             , './/missile'         , 'range'        , 'Missile Missile Range', ''),
    E('missile_guided'            , './/missile'         , 'guided'       , 'Missile Guided', ''),
    E('missile_retarget'          , './/missile'         , 'retarget'     , 'Missile Retarget', ''),
    E('missile_hull'              , './/hull'            , 'max'          , 'Missile Hull', ''),
    E('lock_time'                 , './/lock'            , 'time'         , 'Missile Lock Time', ''),
    E('lock_range'                , './/lock'            , 'range'        , 'Missile Lock Range', ''),
    E('lock_angle'                , './/lock'            , 'angle'        , 'Missile Lock Angle', ''),
    E('counter_resilience'        , './/countermeasure'  , 'resilience'   , 'Missile Resiliance', 'Missile resiliance against countermeasures'),

    E('bullet_codename'           , './macro'            , 'name'         , 'Bullet Codename', '' , read_only = True),
    
    # Hidden compute terms.
    D('merge_damage'              , Display_Update_Bullet_Merged_Damage        , hidden = True),
    D('merge_damage_shield'       , Display_Update_Bullet_Merged_Damage_Shield , hidden = True),
    D('merge_damage_hull'         , Display_Update_Bullet_Merged_Damage_Hull   , hidden = True),
    D('merge_amount'              , Display_Update_Bullet_Merged_Amount        , hidden = True),
    
    ]



def _Build_Weapon_Object_Tree_View():
    '''
    Constructs an Edit_Tree_View object for use in displaying
    weapon data.
    '''
    # Set up a new table.
    object_tree_view = Edit_Tree_View('weapons')

    # Get all of the weapon objects.
    weapon_objects = Live_Editor.Get_Category_Objects('weapons')

    # Organize top level by weapon_class.
    # TODO: maybe nice labels for these.
    class_objects_dict = defaultdict(list)
    for weapon_object in weapon_objects:
        # TODO: think about which value version to use, vanilla or
        # patched or edited. Go with 'current', which will start
        # the same as patched but swaps to edited or the post-transform
        # state after a script run.
        class_objects_dict[ weapon_object
                           .Get_Item('weapon_class')
                           .Get_Value('current') ] .append( weapon_object )

    # TODO: nested organization by size.

    def Get_Name(weapon_object):
        'Returns the current "name" of the object.'
        return weapon_object.Get_Item('name').Get_Value('current')

    # Create a nesting for each weapon class, alphabetical order for now.
    for weapon_class, weapon_objects in sorted(class_objects_dict.items()):
        # Create the tree node.
        this_node = OrderedDict()
        object_tree_view.tree[weapon_class] = this_node

        # Give it all the weapon objects, sorted in name order.
        for weapon_object in sorted( weapon_objects, key = lambda x: Get_Name(x)):

            # Pack into an object viewer; assign no labels just yet.
            label = Get_Name(weapon_object)
            object_view = Object_View(label, weapon_object)
            this_node[label] = object_view

        # For all objects at this node, apply a filtered set of labels.
        # -Switching to relying on object built-in names.
        object_tree_view.Apply_Filtered_Labels(this_node)#, weapon_item_names_ordered_dict)

    return object_tree_view



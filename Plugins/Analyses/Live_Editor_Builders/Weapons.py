'''
Build weapon and bullet objects.
TODO: maybe add more analysis functions to weapons, and split to
a separate file.
'''
from Framework import File_System
from Framework.Live_Editor_Components import *
# Convenience macro renaming.
E = Edit_Item_Macro
D = Display_Item_Macro

from .Support import Create_Objects_From_Asset_Files
from ...Transforms.Support import Float_to_String


##############################################################################

@Live_Editor_Object_Builder('bullets')
def _Build_Bullet_Objects():
    '''
    Returns a list of Edit_Objects for all found bullets.
    Meant for calling from the Live_Editor.
    ''' 
    # Look up bullet files.
    # These can be in two locations.
    File_System.Load_Files('assets/props/WeaponSystems/*.xml')
    File_System.Load_Files('assets/fx/weaponFx/*.xml')
    game_files = File_System.Get_Asset_Files_By_Class('macros',
                    'bullet','missile','bomb','mine','countermeasure')
    return Create_Objects_From_Asset_Files(game_files, bullet_item_macros)


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


    # If this is set up for bursting but only 1 shot per burst,
    #  it may not have a reload_rate; default reload_rate to 1
    #  in this case so something can be computed easily below.
    if ammunition_rounds == '1' and not reload_rate:
        reload_rate = '1'

    # If reload_rate and ammunition_reload_time available, mix them
    # for a burst weapon.
    if (reload_rate and not reload_time 
        and ammunition_reload_time and ammunition_rounds):
        # Note: game calculates this wrongly as of ~1.5, multiplying
        # the ammunition_rounds-1 by reload_rate instead of 1/reload_rate.
        # This will do it correctly (hopefully).
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


##############################################################################

@Live_Editor_Object_Builder('weapons')
def _Build_Weapon_Objects():
    '''
    Returns a list of Edit_Objects for all found weapons.
    Meant for calling from the Live_Editor.
    '''
    # Make sure the bullets are created, so they can be referenced.
    Live_Editor.Get_Category_Objects('bullets')
    game_files = File_System.Get_Asset_Files_By_Class('macros',
                    'weapon','missilelauncher','turret',
                    'missileturret', 'bomblauncher')
    return Create_Objects_From_Asset_Files(game_files, weapon_item_macros)


# Fields from the weapon macro file to look for and convert to Edit_Items.
# Switch to full xpaths to hopefully speed up lxml processing time.
weapon_item_macros = [
    E('rotation_speed'       , './macro/properties/rotationspeed'        , 'max'          , 'Rot. Speed', ''),
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


##############################################################################
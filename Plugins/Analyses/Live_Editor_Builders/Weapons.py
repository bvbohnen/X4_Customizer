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
from .Support import physics_item_macros
from .Support import connection_item_macros
from ...Transforms.Support import Float_to_String


##############################################################################
# Bullets and missiles; these will share some signficiant chunks.
@Live_Editor_Object_Builder('bullets')
def _Build_Bullet_Objects():
    '''
    Returns a list of Edit_Objects for all found bullets.
    Meant for calling from the Live_Editor.
    '''
    # Make sure engines are loaded for the missiles.
    Live_Editor.Get_Category_Objects('engines')

    # Look up bullet files.
    # These can be in two locations.
    File_System.Load_Files('*assets/props/WeaponSystems/*.xml')
    File_System.Load_Files('*assets/fx/weaponFx/*.xml')

    # Split out proper bullets from missiles and similar.
    bullet_game_files = File_System.Get_Asset_Files_By_Class('macros','bullet')
    missile_game_files = File_System.Get_Asset_Files_By_Class('macros',
                    'missile','bomb','mine','countermeasure')
    objects = []
    objects += Create_Objects_From_Asset_Files(bullet_game_files, bullet_item_macros)
    objects += Create_Objects_From_Asset_Files(missile_game_files, missile_item_macros)
    return objects




def Display_Update_RoF(
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

    # Weapon may have reload_time instead of reload_rate; swap to
    # rate to standardize.
    reload_rate_fl = None
    if reload_time and not reload_rate:
        reload_rate_fl = 1 / float(reload_time)
    elif reload_rate:
        reload_rate_fl = float(reload_rate)

    # If reload_rate and ammunition_reload_time available, mix them
    # for a burst weapon.
    if (reload_rate_fl 
        and ammunition_reload_time and ammunition_rounds):
        # Note: game calculates this wrongly as of ~1.5, multiplying
        # the ammunition_rounds-1 by reload_rate instead of 1/reload_rate.
        # This will do it correctly (hopefully).
        # Update: in 3.0 game computes ammo_rounds/reload_rate instead of
        # subtracting one round; is that correct?
        # Test: 1 round burst, 1 reload_rate, 1 reload_time => 1 round/sec, enc says 1.
        # Test: 2 round burst, 1 reload_rate, 2 reload_time => 2 round/3 sec, enc says 0.5
        # So, this calc is correct, enc is wrong (in latter case).
        burst_time = 1/reload_rate_fl * (float(ammunition_rounds)-1)
        time = float(ammunition_reload_time) + burst_time
        return Float_to_String(float(ammunition_rounds)/time)

    # If here, it is unknown.
    return ''


# Shared item types between bullets and missiles.
reload_macros = [
    D('fire_rate'                 , Display_Update_RoF                    , 'Rate of Fire', ''),
    E('reload_rate'               , './/reload'          , 'rate'         , 'Reload Rate', 'For burst weapons, inverse of time between shots in the burst'),
    E('reload_time'               , './/reload'          , 'time'         , 'Reload Time', 'For non-burst weapons, time between shots'),
    E('ammunition_rounds'         , './/ammunition'      , 'value'        , 'Burst Rounds', 'For burst weapons, number of shots per burst.'),
    E('ammunition_reload_time'    , './/ammunition'      , 'reload'       , 'Interburst Time', 'For burst weapons, time from the end of a burst to the start of the next.'),
    ]


def _Calc_Dps(fire_rate, damage, amount):
    'Shared dps calculation code.'
    if fire_rate and damage:
        multiplier = float(fire_rate)
        if amount:
            multiplier *= float(amount)
        return Float_to_String(multiplier * float(damage))
    return ''


def Display_Update_Bullet_Range(
        bullet_lifetime,
        bullet_speed,
        bullet_range
    ):
    'Update range.'
    # Use bullet range if given, else compute.
    if bullet_range:
        return bullet_range
    if bullet_lifetime and bullet_speed:
        return Float_to_String(float(bullet_lifetime) * float(bullet_speed))
    return ''


def Display_Update_Bullet_Burst_DPS(
        fire_rate,
        damage,
        damage_repair,
        bullet_amount,
    ):
    'Calculate burst dps (ignoring heat).'
    # No damage if this is a repair weapon.
    return '' if damage_repair == '1' else _Calc_Dps(fire_rate, damage, bullet_amount)

def Display_Update_Bullet_Burst_DPS_Shield(
        fire_rate,
        damage_shield,
        damage_repair,
        bullet_amount,
    ):
    'Calculate burst shield dps (ignoring heat).'
    return '' if damage_repair == '1' else _Calc_Dps(fire_rate, damage_shield, bullet_amount)

def Display_Update_Bullet_Burst_DPS_Hull(
        fire_rate,
        damage_hull,
        damage_repair,
        bullet_amount,
    ):
    'Calculate burst hull dps (ignoring heat).'
    return '' if damage_repair == '1' else _Calc_Dps(fire_rate, damage_hull, bullet_amount)

def Display_Update_Bullet_Repair_Rate(
        fire_rate,
        damage_hull,
        damage_repair,
        bullet_amount,
    ):
    'Calculate burst repair rate (ignoring heat).'
    # Use the hull damage field for repair amount.
    return '' if damage_repair != '1' else _Calc_Dps(fire_rate, damage_hull, bullet_amount)


bullet_item_macros = [
    D('dps_base'                  , Display_Update_Bullet_Burst_DPS       , 'DPS', ''),
    D('dps_shield'                , Display_Update_Bullet_Burst_DPS_Shield, '+Shield', ''),
    D('dps_hull'                  , Display_Update_Bullet_Burst_DPS_Hull  , '+Hull', ''),
    D('repair_rate'               , Display_Update_Bullet_Repair_Rate     , 'Repair Rate', ''),
    D('range'                     , Display_Update_Bullet_Range           , 'Range', ''),

    *reload_macros,

    E('damage'                    , './/damage'          , 'value'        , 'Damage', ''),
    E('damage_shield'             , './/damage'          , 'shield'       , '+Shield', ''),
    E('damage_hull'               , './/damage'          , 'hull'         , '+Hull', ''),
    E('damage_repair'             , './/damage'          , 'repair'       , 'Repair', 'Set to 1 to flip to repairing.'),

    E('bullet_speed'              , './/bullet'          , 'speed'        , 'Bullet Speed', ''),
    E('bullet_lifetime'           , './/bullet'          , 'lifetime'     , 'Bullet Lifetime', ''),
    E('bullet_range'              , './/bullet'          , 'range'        , 'Bullet Range', ''),
    E('bullet_amount'             , './/bullet'          , 'amount'       , 'Bullet Amount', ''),
    E('barrel_amount'             , './/bullet'          , 'barrelamount' , 'Bullet Barrel Amount', ''),
    E('bullet_timediff'           , './/bullet'          , 'timediff'     , 'Bullet Time Diff', ''),
    E('bullet_angle'              , './/bullet'          , 'angle'        , 'Bullet Angle', ''),
    E('bullet_max_hits'           , './/bullet'          , 'maxhits'      , 'Bullet Max Hits', ''),
    E('bullet_ricochet'           , './/bullet'          , 'ricochet'     , 'Bullet Ricochet', ''),
    E('bullet_scale'              , './/bullet'          , 'scale'        , 'Bullet Scale', ''),
    E('bullet_attach'             , './/bullet'          , 'attach'       , 'Bullet Attach', ''),
    E('bullet_sticktime'          , './/bullet'          , 'sticktime'    , 'Bullet Stick Time', ''),

    E('heat'                      , './/heat'            , 'value'        , '+Heat', 'Heat added per bullet (or burst of bullets)'),
    ]


def Display_Update_Missile_Speed(
        thrust_forward,
        physics_drag_forward,
    ):
    'Calculate speed.'
    return Float_to_String(float(thrust_forward) / float(physics_drag_forward))


def Display_Update_Missile_Range(
        speed,
        missile_lifetime,
    ):
    'Calculate range.'
    return Float_to_String(float(speed) * float(missile_lifetime))


def Display_Update_Missile_DPS(
        fire_rate,
        explosion_damage,
        missile_amount,
    ):
    'Calculate dps.'
    return _Calc_Dps(fire_rate, explosion_damage, missile_amount)

def Display_Update_Missile_DPS_Shield(
        fire_rate,
        explosion_damage_shield,
        missile_amount,
    ):
    'Calculate shield dps.'
    return _Calc_Dps(fire_rate, explosion_damage_shield, missile_amount)

def Display_Update_Missile_DPS_Hull(
        fire_rate,
        explosion_damage_hull,
        missile_amount,
    ):
    'Calculate hull dps.'
    return _Calc_Dps(fire_rate, explosion_damage_hull, missile_amount)


missile_item_macros = [
    # No heat on these, so don't bother with burst dps for now.
    D('dps_base'                  , Display_Update_Missile_DPS             , 'DPS', ''),
    D('dps_shield'                , Display_Update_Missile_DPS_Shield      , '+Shield', ''),
    D('dps_hull'                  , Display_Update_Missile_DPS_Hull        , '+Hull', ''),
    D('speed'                     , Display_Update_Missile_Speed           , 'Speed', ''),
    D('effective_range'           , Display_Update_Missile_Range           , 'Effective Range', ''),

    *reload_macros,
    
    E('weapon_system'             , './/weapon'          , 'system'       , 'Weapon System'        , ''),
    E('explosion_damage'          , './/explosiondamage' , 'value'        , 'Explosion Damage'     , ''),
    E('explosion_damage_shield'   , './/explosiondamage' , 'shield'       , 'Explosion +Shield'    , ''),
    E('explosion_damage_hull'     , './/explosiondamage' , 'hull'         , 'Explosion +Hull'      , ''),
    E('missile_amount'            , './/missile'         , 'amount'       , 'Amount'               , ''),
    E('missile_barrel_amount'     , './/missile'         , 'barrelamount' , 'Barrel Amount'        , ''),
    E('missile_lifetime'          , './/missile'         , 'lifetime'     , 'Lifetime'             , ''),
    E('missile_range'             , './/missile'         , 'range'        , 'Range'                , ''),
    E('missile_guided'            , './/missile'         , 'guided'       , 'Guided'               , ''),
    E('missile_retarget'          , './/missile'         , 'retarget'     , 'Retarget'             , ''),
    E('missile_hull'              , './/hull'            , 'max'          , 'Hull'                 , ''),
    E('lock_time'                 , './/lock'            , 'time'         , 'Lock Time'            , ''),
    E('lock_range'                , './/lock'            , 'range'        , 'Lock Range'           , ''),
    E('lock_angle'                , './/lock'            , 'angle'        , 'Lock Angle'           , ''),
    E('counter_resilience'        , './/countermeasure'  , 'resilience'   , 'Counter Resiliance'   , 'Missile resiliance against countermeasures'),
    
    E('longrangescan'             , './/longrangescan'   , 'minlevel'     , 'Long Range Scan'      , ''),
    
    *physics_item_macros,
    *connection_item_macros,
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
# TODO: Switch to full xpaths to hopefully speed up lxml processing time.
weapon_item_macros = [
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


##############################################################################

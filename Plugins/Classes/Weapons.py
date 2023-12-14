
from Framework.Documentation import Doc_Category_Default
_doc_category = Doc_Category_Default('Classes')

from .Macro import Macro
from .Connection import Connection
from .Component  import Component
from Framework import File_System
from .Shared import Physics_Properties

__all__ = [
    'Weapon_System',
    'Bullet',
    'Missile',
    'Bomb',
    'Mine',
    ]

class Weapon_System(Macro):
    '''
    Weapon system, linking to a bullet. Defines model, rotation speed, etc.
    Most weapon properties are part of the bullet.
    
    * class_name
      - String, one of: bomblauncher, missilelauncher, missileturret, turret,
        weapon.
    '''
    def __init__(self, xml_node, *args, **kwargs):
        super().__init__(xml_node, *args, **kwargs)

        # Every weapon links to a bullet (laser or missile) that has most
        # of the interesting info.
        self.bullet_macro_name = self.Get('./properties/bullet', 'class')
        return

    def Get_Bullet(self):
        '''
        Returns the bullet macro.
        '''
        if not hasattr(self, '_bullet_macro'):
            self._bullet_macro = self.database.Get_Macro(self.bullet_macro_name)
        return self._bullet_macro

    # TODO: fields of interest.


class Generic_Bullet(Macro):
    '''
    Parent class for bullet, missile, bomb.
    '''
    def Get_Ammo_Reload_Time(self):
        value = self.Get('./properties/ammunition','reload')
        return float(value) if value else None
    def Get_Ammo_Rounds(self):
        value = self.Get('./properties/ammunition','value')
        return float(value) if value else None
    def Get_Reload_Time(self):
        value = self.Get('./properties/reload','time')
        return float(value) if value else None
    def Get_Reload_Rate(self):
        value = self.Get('./properties/reload','rate')
        return float(value) if value else None
    
    def Set_Ammo_Reload_Time(self, value):
        self.Set('./properties/ammunition','reload', f'{value:.3f}')
    def Set_Reload_Time(self, value):
        self.Set('./properties/reload','time', f'{value:.3f}')
    def Set_Reload_Rate(self, value):
        self.Set('./properties/reload','rate', f'{value:.3f}')

    def Get_Rate_Of_Fire(self):
        '''
        Returns the rate of fire, in shots per second.
        '''
        ammo_reload_time = self.Get_Ammo_Reload_Time()
        ammo_rounds = self.Get_Ammo_Rounds()
        reload_time = self.Get_Reload_Time()
        reload_rate = self.Get_Reload_Rate()

        # Reload rate and time seem to be alternatives to each other.
        # Standardize to rate.
        if reload_time and not reload_rate:
            reload_rate = 1 / reload_time

        # If not an ammo weapon, use the above.
        if not ammo_reload_time:
            return reload_rate
        
        # If this is set up for bursting but only 1 shot per burst,
        #  it may not have a reload_rate; default reload_rate to 1
        #  in this case so something can be computed easily below.
        if ammo_rounds == 1 and not reload_rate:
            reload_rate = 1

        # If reload_rate and ammo_reload_time available, mix them
        # for a burst weapon.
        if (reload_rate and ammo_reload_time and ammo_rounds):
            # Note: game calculates this wrongly as of ~1.5, multiplying
            # the ammo_rounds-1 by reload_rate instead of 1/reload_rate.
            # This will do it correctly (hopefully).
            # Update: in 3.0 game computes ammo_rounds/reload_rate instead of
            # subtracting one round, again incorrect.
            # Test: 1 round burst, 1 reload_rate, 1 reload_time => 1 round/sec, enc says 1.
            # Test: 2 round burst, 1 reload_rate, 2 reload_time => 2 round/3 sec, enc says 0.5
            # So, this calc is correct, enc is wrong (in latter case).
            burst_time = 1/reload_rate * (ammo_rounds -1)
            time = ammo_reload_time + burst_time
            return ammo_rounds / time

        raise Exception()

        
    def Set_Rate_Of_Fire(self, new_rof):
        '''
        Set the rate of fire, in shots per second.
        '''
        old_rof = self.Get_Rate_Of_Fire()
        multiplier = new_rof / old_rof
                
        # See notes above on rate of fire calculation.
        # In short, need to edit the 'reload rate', 'reload time',
        # and 'ammunition reload' fields to cover both normal weapons
        # and burst weapons (where bursting rate is a combination of
        # ammo reload and reload rate).
        
        ammo_reload_time = self.Get_Ammo_Reload_Time()
        reload_time = self.Get_Reload_Time()
        reload_rate = self.Get_Reload_Rate()

        if ammo_reload_time:
            # Invert the multiplier to reduce reload time.
            self.Set_Ammo_Reload_Time(ammo_reload_time / multiplier)
            
        if reload_time:
            # Invert the multiplier to reduce reload time.
            self.Set_Reload_Time(reload_time / multiplier)
            
        if reload_rate:
            # Keep multiplier as-is.
            self.Set_Reload_Rate(reload_rate * multiplier)
        return

    # TODO: should this method be split for bullets/missiles?
    # May lead to redundancy between missiles/bombs/mines, unless broken
    # out into a separate shared class.
    def Adjust_Damage(self, multiplier):
        'Adjust all types of bullet damage.'

        # Bullet fields. Missiles won't use these.
        for field in ['value', 'shield', 'hull', 'repair']:
            value = self.Get('./properties/damage', field)
            if not value:
                continue
            value = float(value)
            new_value = value * multiplier
            self.Set('./properties/damage', field, f'{new_value:.3f}')
        
        # Missile fields. Also for bombs/mines.
        # Possible bullets might use these?  Unknown.
        for field in ['value', 'shield', 'hull']:
            value = self.Get('./properties/explosiondamage', field)
            if not value:
                continue
            value = float(value)
            new_value = value * multiplier
            self.Set('./properties/explosiondamage', field, f'{new_value:.3f}')

        return

    # TODO: should this method be only for bullets?
    def Adjust_Heat(self, multiplier):
        'Adjust heat produced.'
        value = self.Get('./properties/heat', 'value')
        if not value:
            return
        value = float(value)
        new_value = value * multiplier
        self.Set('./properties/heat', 'value', f'{new_value:.3f}')

        
    def Adjust_Range(self, multiplier):
        'Change weapon range.'
        # Note: range works somewhat differently for different bullet
        # types.
        # - Beams have range, lifetime, and speed; edit just speed.
        # - Missiles have range and lifetime; edit lifetime?
        # - Others have lifetime and speed; edit speed and adjust lifetime.
        for tag in ['bullet','missile']:
            range    = self.Get(f'./properties/{tag}', 'range')
            lifetime = self.Get(f'./properties/{tag}', 'lifetime')

            # If it has range, edit that.
            if range:
                value = float(range)
                new_value = value * multiplier
                self.Set(f'./properties/{tag}', 'range', f'{new_value:.3f}')

            # Otherwise, edit lifetime.
            elif lifetime:
                value = float(lifetime)
                new_value = value * multiplier
                self.Set(f'./properties/{tag}', 'lifetime', f'{new_value:.3f}')
        return
    


class Bullet(Generic_Bullet):
    '''
    Bullet macro, such as shot from a laser. Not a missle/bomb.
    '''    
    def Adjust_Speed(self, multiplier):
        'Change bullet speed.'
        #range    = self.Get('./properties/bullet', 'range')
        lifetime = self.Get('./properties/bullet', 'lifetime')
        # Note: missiles are more complex, with a thrust and such; TODO
        speed    = self.Get('./properties/bullet', 'speed')

        # Check for speed and lifetime, indicating a beam.
        if speed and lifetime:
            speed = float(speed)
            lifetime = float(lifetime)
            # Bump speed, decrease lifetime, beam shoots out faster
            # but for same range.
            self.Set(f'./properties/bullet', 'speed', f'{speed * multiplier:.3f}')
            self.Set(f'./properties/bullet', 'lifetime', f'{lifetime / multiplier:.3f}')

        elif speed:
            speed = float(speed)
            # Edit just speed.
            self.Set(f'./properties/bullet', 'speed', f'{speed * multiplier:.3f}')
        else:
            assert False

    
class Missile(Generic_Bullet, Physics_Properties):
    '''
    Missile macro.
    '''
    # Speed adjustment comes from physics properties.
        
        
class Bomb(Generic_Bullet, Physics_Properties):
    '''
    Bomb macro. Only used by spacesuit bombs.
    '''

class Mine(Macro, Physics_Properties):
    '''
    Mine macro.  TODO: add engines/etc.
    '''
    # Tracker mines have physics, though others don't.
    def Adjust_Speed(self, multiplier):
        # Skip if no physics, else use physics method.
        if not self.xml_node.xpath('./properties/physics'):
            return
        Physics_Properties.Adjust_Speed(self, multiplier)


'''
Fields of interest (copied from live editor):

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
    

# Shared item types between bullets and missiles.
reload_macros = [
    D('fire_rate'                 , Display_Update_RoF                    , 'Rate of Fire', ''),
    E('reload_rate'               , './/reload'          , 'rate'         , 'Reload Rate', 'For burst weapons, inverse of time between shots in the burst'),
    E('reload_time'               , './/reload'          , 'time'         , 'Reload Time', 'For non-burst weapons, time between shots'),
    E('ammunition_rounds'         , './/ammunition'      , 'value'        , 'Burst Rounds', 'For burst weapons, number of shots per burst.'),
    E('ammunition_reload_time'    , './/ammunition'      , 'reload'       , 'Interburst Time', 'For burst weapons, time from the end of a burst to the start of the next.'),
    ]

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
'''

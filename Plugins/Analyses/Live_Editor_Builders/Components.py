'''
Build misc ship component objects in 'assets/props/'.
'''

from Framework import File_System
from Framework.Live_Editor_Components import *

# Convenience macro renaming.
E = Edit_Item_Macro
D = Display_Item_Macro


from .Support import Create_Objects_From_Asset_Files
from ...Transforms.Support import Float_to_String


##############################################################################

@Live_Editor_Object_Builder('shields')
def _Build_Shield_Objects():   
    File_System.Load_Files('assets/props/SurfaceElements/*.xml')
    game_files = File_System.Get_Asset_Files_By_Class('macros','shieldgenerator')
    return Create_Objects_From_Asset_Files(game_files, shield_item_macros)


def Calc_Recharge_Time(
        recharge_max,
        recharge_rate
    ):
    'Simple calc of time to recharge from 0 to 100%.'
    if recharge_max and recharge_rate:
        time = float(recharge_max) / float(recharge_rate)
        return Float_to_String(time)

    
shield_item_macros = [
    E('makerrace'            , './/identification'       , 'makerrace'    , 'Maker', ''),
    E('mk'                   , './/identification'       , 'mk'           , 'Mark', ''),

    E('recharge_max'         , './/recharge'             , 'max'          , 'Strength', ''),
    E('recharge_rate'        , './/recharge'             , 'rate'         , 'Recharge Rate', ''),
    E('recharge_delay'       , './/recharge'             , 'delay'        , 'Recharge Delay', ''),
    D('recharge_time'        , Calc_Recharge_Time                         , 'Recharge Time', 'Seconds to recharge from 0 to 100%.'),

    E('hull'                 , './/hull'                 , 'max'          , 'Hull', ''),
    E('hull_threshold'       , './/hull'                 , 'threshold'    , 'Hull Thr.', 'Hull Threshold'),
    ]


##############################################################################

@Live_Editor_Object_Builder('scanners')
def _Build_Scanner_Objects():
    File_System.Load_Files('assets/props/SurfaceElements/*.xml')
    game_files = File_System.Get_Asset_Files_By_Class('macros','scanner')
    return Create_Objects_From_Asset_Files(game_files, scanner_item_macros)

scanner_item_macros = [
    E('scan_level'           , './/scan'                 , 'maxlevel'     , 'Scan Level', ''),
    ]


##############################################################################

@Live_Editor_Object_Builder('dockingbays')
def _Build_DockingBay_Objects():
    File_System.Load_Files('assets/props/SurfaceElements/*.xml')
    game_files = File_System.Get_Asset_Files_By_Class('macros','dockingbay')
    return Create_Objects_From_Asset_Files(game_files, dockingbay_item_macros)

dockingbay_item_macros = [
    E('dock_capacity'        , './/dock'                 , 'capacity'     , 'Capacity', ''),
    E('dock_external'        , './/dock'                 , 'external'     , 'External', ''),
    E('dock_storage'         , './/dock'                 , 'storage'      , 'Storage', ''),

    E('walkable'             , './/room'                 , 'walkable'     , 'Walkable', ''),
    E('dock_tags'            , './/docksize'             , 'tags'         , 'Dock Tags', ''),
    ]


##############################################################################

@Live_Editor_Object_Builder('storage')
def _Build_Storage_Objects():
    # These are a bit scattered, some in the units folder and
    # some in storagemodules. Use a name pattern match for this.
    game_files = File_System.Get_All_Indexed_Files('macros','storage_*')
    #File_System.Load_Files('assets/props/StorageModules/*.xml')
    #game_files = File_System.Get_Asset_Files_By_Class('macros','storage')
    return Create_Objects_From_Asset_Files(game_files, storage_item_macros)


# TODO: maybe lockboxes and/or collectablewares as well

storage_item_macros = [
    E('makerrace'            , './macro/properties/identification'        , 'makerrace'    , 'Maker', ''),
    #E('mk'                   , './macro/properties/identification'        , 'mk'           , 'Mark', ''),    

    E('cargo_max'            , './macro/properties/cargo'                 , 'max'          , 'Cargo Max', ''),
    E('cargo_tags'           , './macro/properties/cargo'                 , 'tags'         , 'Cargo Tags'  , ''),
    
    #E('hull'                 , './macro/properties/hull'                  , 'max'          , 'Hull', ''),
    E('hull_integrated'      , './macro/properties/hull'                  , 'integrated'   , 'Hull Integrated', ''),
    ]


##############################################################################


@Live_Editor_Object_Builder('engines')
def _Build_Engine_Objects():
    '''
    Returns a list of Edit_Objects for 'assets/props/Engines'.
    Meant for calling from the Live_Editor.
    '''    
    File_System.Load_Files('assets/props/Engines/*.xml')
    game_files = File_System.Get_Asset_Files_By_Class('macros','engine')
    return Create_Objects_From_Asset_Files(game_files, engine_item_macros)


# TODO: customize tree by engine tags:
# 'engine' vs 'thruster', and by size.

engine_item_macros = [
    E('makerrace'            , './macro/properties/identification'        , 'makerrace'    , 'Maker', ''),
    E('mk'                   , './macro/properties/identification'        , 'mk'           , 'Mark', ''),    

    E('thrust_forward'       , './macro/properties/thrust'                , 'forward'      , 'Thrust Forward', ''),
    E('thrust_reverse'       , './macro/properties/thrust'                , 'reverse'      , 'Thrust Reverse'  , ''),
    
    E('thrust_strafe'        , './macro/properties/thrust'                , 'strafe'       , 'Thrust Strafe'  , ''),
    E('thrust_pitch'         , './macro/properties/thrust'                , 'pitch'        , 'Thrust Pitch'  , ''),
    E('thrust_yaw'           , './macro/properties/thrust'                , 'yaw'          , 'Thrust Yaw'  , ''),
    E('thrust_roll'          , './macro/properties/thrust'                , 'roll'         , 'Thrust Roll'  , ''),

    E('boost_duration'       , './macro/properties/boost'                 , 'duration'     , 'Boost Duration', ''),
    E('boost_thrust'         , './macro/properties/boost'                 , 'thrust'       , 'Boost Thrust'  , ''),
    E('boost_attack'         , './macro/properties/boost'                 , 'attack'       , 'Boost Attack'  , ''),
    E('boost_release'        , './macro/properties/boost'                 , 'release'      , 'Boost Release' , ''),
    
    E('travel_charge'        , './macro/properties/travel'                , 'charge'       , 'Travel Charge', ''),
    E('travel_thrust'        , './macro/properties/travel'                , 'thrust'       , 'Travel Thrust'  , ''),
    E('travel_attack'        , './macro/properties/travel'                , 'attack'       , 'Travel Attack'  , ''),
    E('travel_release'       , './macro/properties/travel'                , 'release'      , 'Travel Release' , ''),

    E('hull'                 , './macro/properties/hull'                  , 'max'          , 'Hull', ''),
    E('hull_threshold'       , './macro/properties/hull'                  , 'threshold'    , 'Hull Thr.', 'Hull Threshold'),
    
    E('effects_boosting'     , './macro/properties/effects/boosting'      , 'ref'          , 'Boost Effect', ''),
    E('sounds_engine'        , './macro/properties/sounds/enginedetail'   , 'ref'          , 'Sound Effect', ''),

    ]


##############################################################################

@Live_Editor_Object_Builder('cockpits')
def _Build_Cockpit_Objects():
    game_files = File_System.Get_All_Indexed_Files('macros','cockpit_*')
    return Create_Objects_From_Asset_Files(game_files, [])

##############################################################################
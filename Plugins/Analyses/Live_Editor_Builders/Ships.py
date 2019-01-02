
from Framework import File_System
from Framework.Live_Editor_Components import *
# Convenience macro renaming.
E = Edit_Item_Macro
D = Display_Item_Macro
G = Item_Group_Macro

from .Support import Create_Objects_From_Asset_Files
from ...Transforms.Support import Float_to_String


@Live_Editor_Object_Builder('ships')
def _Build_Storage_Objects():
    # TODO: also load in files needed for references, as needed.
    # Ensure some available refs are loaded.
    Live_Editor.Get_Category_Objects('storage')
    game_files = File_System.Get_All_Indexed_Files('macros','ship_*')
    return Create_Objects_From_Asset_Files(game_files, ship_item_macros)



ship_item_macros = [
    E('ship_type'                 , './macro/properties/ship'                , 'type'       , 'Ship Type'       , ''),
    E('purpose_primary'           , './macro/properties/purpose'             , 'primary'    , 'Primary Purpose' , ''),

    E('hull'                      , './macro/properties/hull'                , 'max'        , 'Hull'            , ''),
    E('explosion_damage'          , './macro/properties/explosiondamage'     , 'value'      , 'Expl. Damage'    , ''),
    E('people_capacity'           , './macro/properties/people'              , 'capacity'   , 'People'          , ''),
    E('storage_missile'           , './macro/properties/storage'             , 'missile'    , 'Missile Storage' , ''),
    E('thruster_tags'             , './macro/properties/thruster'            , 'tags'       , 'Thruster Tags'   , ''),
    E('secrecy_level'             , './macro/properties/secrecy'             , 'level'      , 'Secrecy Level'   , ''),
    
    E('physics_mass'              , './macro/properties/physics'             , 'mass'       , 'Mass'            , ''),
    E('physics_inertia_pitch'     , './macro/properties/physics/inertia'     , 'pitch'      , 'Inertia Pitch'   , ''),
    E('physics_inertia_yaw'       , './macro/properties/physics/inertia'     , 'yaw'        , 'Inertia Yaw'     , ''),
    E('physics_inertia_roll'      , './macro/properties/physics/inertia'     , 'roll'       , 'Inertia Roll'    , ''),
    E('physics_drag_forward'      , './macro/properties/physics/drag'        , 'forward'    , 'Drag Forward'    , ''),
    E('physics_drag_reverse'      , './macro/properties/physics/drag'        , 'reverse'    , 'Drag Reverse'    , ''),
    E('physics_drag_horizontal'   , './macro/properties/physics/drag'        , 'horizontal' , 'Drag Horizontal' , ''),
    E('physics_drag_vertical'     , './macro/properties/physics/drag'        , 'vertical'   , 'Drag Vertical'   , ''),
    E('physics_drag_pitch'        , './macro/properties/physics/drag'        , 'pitch'      , 'Drag Pitch'      , ''),
    E('physics_drag_yaw'          , './macro/properties/physics/drag'        , 'yaw'        , 'Drag Yaw'        , ''),
    E('physics_drag_roll'         , './macro/properties/physics/drag'        , 'roll'       , 'Drag Roll'       , ''),

    E('sounds_ship'               , './macro/properties/sounds/shipdetail'   , 'ref'        , 'Sound Effect'    , ''),
    E('sound_occlusion'           , './macro/properties/sound_occlusion'     , 'inside'     , 'Sound Occlusion' , ''),

    # Loop over software.
    G('software'                  , './macro/properties/software'            , 'software'   , 'Software'            ),
    E('ware'                      , '.'                                      , 'ware'       , 'Ware'            , ''),
    E('default'                   , '.'                                      , 'default'    , 'Default'         , ''),
    E('compatible'                , '.'                                      , 'compatible' , 'Compatible'      , ''),
    G('/software'),

    # Loop over connections.
    G('connections'               , './macro/connections'                    , 'connection' , 'Connection'          ),
    E('name'                      , '.'                                      , 'ref'        , 'Name'            , ''),
    E('connector'                 , './macro'                                , 'connection' , 'Connector'       , ''),
    E('macro_name'                , './macro'                                , 'ref'        , 'Macro Codename'  , '',  is_reference = True),
    G('/connections'),
    
    ]



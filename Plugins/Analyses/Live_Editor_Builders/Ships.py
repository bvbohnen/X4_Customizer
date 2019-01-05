
from Framework import File_System
from Framework.Live_Editor_Components import *
# Convenience macro renaming.
E = Edit_Item_Macro
D = Display_Item_Macro
G = Item_Group_Macro

from .Support import Create_Objects_From_Asset_Files
from .Support import physics_item_macros
from .Support import connection_item_macros
from ...Transforms.Support import Float_to_String


@Live_Editor_Object_Builder('ships')
def _Build_Storage_Objects():
    # Ensure some available refs are loaded.
    Live_Editor.Get_Category_Objects('storage')
    Live_Editor.Get_Category_Objects('dockingbays')
    Live_Editor.Get_Category_Objects('cockpits')
    # TODO: dynamic connections.

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
    
    *physics_item_macros,

    E('sounds_ship'               , './macro/properties/sounds/shipdetail'   , 'ref'        , 'Sound Effect'    , ''),
    E('sound_occlusion'           , './macro/properties/sound_occlusion'     , 'inside'     , 'Sound Occlusion' , ''),

    # Loop over software.
    G('software'                  , './macro/properties/software'            , 'software'   , 'Software'            ),
    E('ware'                      , '.'                                      , 'ware'       , 'Ware'            , ''),
    E('default'                   , '.'                                      , 'default'    , 'Default'         , ''),
    E('compatible'                , '.'                                      , 'compatible' , 'Compatible'      , ''),
    G('/software'),

    *connection_item_macros
    
    ]



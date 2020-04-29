
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

# TODO:
# Speed calculations depend on the engine. However, can make an assumption
# about the engine to estimate speed.


@Live_Editor_Object_Builder('ships')
def _Build_Storage_Objects():
    # Ensure some available refs are loaded.
    Live_Editor.Get_Category_Objects('storage')
    Live_Editor.Get_Category_Objects('dockingbays')
    Live_Editor.Get_Category_Objects('cockpits')

    # TODO: dynamic connections.
    # These would require looking up and processing the component file,
    # to try to identify eg. how many engines the ship has, and of which
    # tags, then to go look up engine data and determine what the thrusts are.
    # Overall, this route is plausible, but would be best served by a wider
    # scale parsing of data into custom classes for cross referencing,
    # whereas the code here just runs on xpaths in the original xml.
    #Live_Editor.Get_Category_Objects('engines')

    game_files = File_System.Get_All_Indexed_Files('macros','ship_*')
    return Create_Objects_From_Asset_Files(game_files, ship_item_macros)

#def Display_Update_Speed(component, ship_type, purpose_primary, physics_drag_forward):
#    return ''


ship_item_macros = [
    E('ship_type'                 , './properties/ship'                , 'type'       , 'Ship Type'       , ''),
    E('purpose_primary'           , './properties/purpose'             , 'primary'    , 'Primary Purpose' , ''),

    E('hull'                      , './properties/hull'                , 'max'        , 'Hull'            , ''),
    E('explosion_damage'          , './properties/explosiondamage'     , 'value'      , 'Expl. Damage'    , ''),
    E('people_capacity'           , './properties/people'              , 'capacity'   , 'People'          , ''),
    E('storage_missile'           , './properties/storage'             , 'missile'    , 'Missile Storage' , ''),
    E('thruster_tags'             , './properties/thruster'            , 'tags'       , 'Thruster Tags'   , ''),
    E('secrecy_level'             , './properties/secrecy'             , 'level'      , 'Secrecy Level'   , ''),
    
    #D('speed'                     , Display_Update_Speed               , 'Speed', 'Assumes combat mk3 engines'),
    *physics_item_macros,

    E('sounds_ship'               , './properties/sounds/shipdetail'   , 'ref'        , 'Sound Effect'    , ''),
    E('sound_occlusion'           , './properties/sound_occlusion'     , 'inside'     , 'Sound Occlusion' , ''),

    # Loop over software.
    G('software'                  , './properties/software'            , 'software'   , 'Software'            ),
    E('ware'                      , '.'                                , 'ware'       , 'Ware'            , ''),
    E('default'                   , '.'                                , 'default'    , 'Default'         , ''),
    E('compatible'                , '.'                                , 'compatible' , 'Compatible'      , ''),
    G('/software'),

    *connection_item_macros
    
    ]



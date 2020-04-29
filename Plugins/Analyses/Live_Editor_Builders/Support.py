'''
Some reusable functions for different object types.
Intially, mainly aimed at various component file pairs.
'''

from Framework import File_System
from Framework.Live_Editor_Components import *
# Convenience macro renaming.
_E = Edit_Item_Macro
_D = Display_Item_Macro
_G = Item_Group_Macro


def Get_Macro_Component_File(macro_file, xpath_prefix):
    '''
    Returns the component file matched to the given macro file,
    along with an xpath to the component node.
    The component should already have been loaded.
    TODO: maybe support an attempt at autoloading one directory up.
    '''
    root = macro_file.Get_Root_Readonly()
    component_name = root.xpath(xpath_prefix + '/component')[0].get('ref')
    component_file = File_System.Get_Indexed_File('components', component_name)
    xpath = component_file.Get_Asset_Xpath(component_name)
    return component_file, xpath


def Get_Component_Connection_Xpath(game_file, xpath):
    '''
    Returns an xpath to the "connection" node holding the main component
    "tags" attribute; it will be the one with a "component" term.
    If none found, returns None.
    TODO: return multiple component matches, if found.
    '''
    # Note: this connection doesn't have a standard name, but can
    # be identified by a "component" term in the tags.
    root = game_file.Get_Root_Readonly()
    xpath += '/connections/connection[@tags]'
    for connection in root.xpath(xpath):
        if 'component' in connection.get('tags'):
            # Add the name of the connection to the xpath to uniquify it.
            name = connection.get('name')
            xpath += '[@name="{}"]'.format(name)
            # Verify it.
            assert root.xpath(xpath)[0] is connection
            return xpath
    return None


def Fill_Macro_Object_Standard_Items(
        game_file, 
        edit_object, 
        xpath_prefix = None
    ):
    '''
    Fill in some standard items for macro objects, including
    the tags from a matching component file.

    * game_file
      - The Game_File holding the object properties.
    * edit_object
      - The Edit_Object being filled in.
    * xpath_prefix
      - Optional xpath to prefix to all macros to find the base asset node.
    '''
    # Fill in its edit items.
    edit_object.Make_Items(game_file, _item_macros, xpath_prefix)

    # Get the component file, and an xpath to the component
    # (in case the file has multiple).
    comp_file, comp_xpath = Get_Macro_Component_File(game_file, xpath_prefix)
    # Get the xpath for the connection node.
    # This may end up unfound.
    conn_xpath = Get_Component_Connection_Xpath(comp_file, comp_xpath)
        
    if conn_xpath != None:
        # Add extra bits from the components file.
        # These macros need to fill in the connection node xpath term.
        edit_object.Make_Items(
            comp_file,
            _component_item_macros,
            xpath_replacements = {'connection_xpath' : conn_xpath})
    return


def Create_Objects_From_Asset_Files(
        game_files, 
        custom_item_macros = None, 
        is_macro = None
    ):
    '''
    Returns a list of Edit_Objects for the given asset style game_file,
    applying a set of custom Item building macros.
    '''
    object_list = []
    for game_file in game_files:
        # Go through the assets in the file (normally just one).
        for asset_class_name, asset_name_list in game_file.asset_class_name_dict.items():
            for name in asset_name_list:
                # Create an Edit_Object using the asset name.
                edit_object = Edit_Object(name)
                object_list.append( edit_object )

                # Get the xpath to the particular asset node.
                xpath_prefix = game_file.Get_Asset_Xpath(name)

                # Fill in standard terms.
                Fill_Macro_Object_Standard_Items(
                    game_file, edit_object, xpath_prefix)

                # Fill in custom terms.
                edit_object.Make_Items(
                    game_file, custom_item_macros, xpath_prefix)
    return object_list


def Update_Name(
        t_name_entry,
        codename
    ):
    'Look up a text reference name.'
    if not t_name_entry:
        # If no t_name_entry available, use the codename name.
        # Component could be used sometimes, since it often is the codename
        #  without a _macro suffix, but doesn't work quite as well
        #  since sometimes objects will share a component (causing them
        #  to have the same name).
        # This will manually prune the _macro term if found.
        return codename.replace('_macro','')
    else:
        t_file = File_System.Load_File('t/0001-L044.xml')
        # Let the t-file Read handle the lookup.
        name = t_file.Read(t_name_entry)
        # TODO: maybe replace with something when the name is blank.
        return name
    
def Update_Description(
        t_descrip_entry,
    ):
    'Look up a text reference description.'
    if not t_descrip_entry:
        return ''
    else:
        t_file = File_System.Load_File('t/0001-L044.xml')
        # Let the t-file Read handle the lookup.
        return t_file.Read(t_descrip_entry)

_item_macros = [
    _D('name'                 , Update_Name                                            , 'Name', ''),
    _E('t_name_entry'         , './properties/identification'   , 'name'         , 'T Name Entry', ''),
    # TODO: maybe description; would need to think of
    # a special way to show this that is legible.
    _D('description'          , Update_Description                                     , 'Description', ''),
    _E('t_descrip_entry'      , './properties/identification'   , 'description'  , 'T Desc. Entry', ''),
    _E('codename'             , '.'                             , 'name'         , 'Codename', '', read_only = True),
    _E('macro_class'          , '.'                             , 'class'        , 'Class', '', read_only = True),
    _E('component'            , './component'                   , 'ref'          , 'Component', '', read_only = True),
    ]
_component_item_macros = [
    _E('connection_name'       , 'connection_xpath'       , 'name'         , 'Connection Name', ''),
    _E('connection_tags'       , 'connection_xpath'       , 'tags'         , 'Connection Tags', ''),
    ]


physics_item_macros = [
    _E('physics_mass'              , './properties/physics'             , 'mass'       , 'Mass'            , ''),
    _E('physics_inertia_pitch'     , './properties/physics/inertia'     , 'pitch'      , 'Inertia Pitch'   , ''),
    _E('physics_inertia_yaw'       , './properties/physics/inertia'     , 'yaw'        , 'Inertia Yaw'     , ''),
    _E('physics_inertia_roll'      , './properties/physics/inertia'     , 'roll'       , 'Inertia Roll'    , ''),
    _E('physics_drag_forward'      , './properties/physics/drag'        , 'forward'    , 'Drag Forward'    , ''),
    _E('physics_drag_reverse'      , './properties/physics/drag'        , 'reverse'    , 'Drag Reverse'    , ''),
    _E('physics_drag_horizontal'   , './properties/physics/drag'        , 'horizontal' , 'Drag Horizontal' , ''),
    _E('physics_drag_vertical'     , './properties/physics/drag'        , 'vertical'   , 'Drag Vertical'   , ''),
    _E('physics_drag_pitch'        , './properties/physics/drag'        , 'pitch'      , 'Drag Pitch'      , ''),
    _E('physics_drag_yaw'          , './properties/physics/drag'        , 'yaw'        , 'Drag Yaw'        , ''),
    _E('physics_drag_roll'         , './properties/physics/drag'        , 'roll'       , 'Drag Roll'       , ''),
    ]

connection_item_macros = [    
    # Loop over connections.
    _G('connections'               , './connections'                    , 'connection' , 'Conn.'           ),
    _E('name'                      , '.'                                , 'ref'        , 'Name'            , ''),
    _E('connector'                 , './macro'                          , 'connection' , 'Connector'       , ''),
    _E('macro_name'                , './macro'                          , 'ref'        , 'Macro'           , '',  is_reference = True),
    _G('/connections'),
    ]
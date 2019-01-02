'''
Some reusable functions for different object types.
Intially, mainly aimed at various macro/component file pairs.
'''

from Framework import File_System
from Framework.Live_Editor_Components import *
# Convenience macro renaming.
_E = Edit_Item_Macro
_D = Display_Item_Macro


def Get_Macro_Component_File(macro_file):
    '''
    Returns the component file matched to the given macro file.
    The component should already have been loaded.
    TODO: maybe support an attempt at autoloading one directory up.
    '''
    root = macro_file.Get_Root_Readonly()
    component_name = root.find('./macro/component').get('ref')
    component_file = File_System.Get_Indexed_File('components', component_name)
    return component_file


def Get_Component_Connection_Xpath(game_file):
    '''
    Returns an xpath to the "connection" node holding the main component
    "tags" attribute; it will be the one with a "component" term.
    If none found, returns None.
    TODO: return multiple component matches, if found.
    '''
    # Note: this connection doesn't have a standard name, but can
    # be identified by a "component" term in the tags.
    root = game_file.Get_Root_Readonly()
    xpath = './/connection[@tags]'
    for connection in root.findall(xpath):
        if 'component' in connection.get('tags'):
            # Add the name of the connection to the xpath to uniquify it.
            name = connection.get('name')
            xpath += '[@name="{}"]'.format(name)
            # Verify it.
            assert root.find(xpath) is connection
            return xpath
    return None


def Fill_Macro_Object_Standard_Items(game_file, edit_object):
    '''
    Fill in some standard items for macro objects, including
    the tags from a matching component file.
    '''
    # Fill in its edit items.
    edit_object.Make_Items(game_file, _item_macros)

    # Get the component file.
    comp_file = Get_Macro_Component_File(game_file)
    # Get the xpath for the connection node.
    # This may end up unfound.
    conn_xpath = Get_Component_Connection_Xpath(comp_file)
        
    if conn_xpath != None:
        # Also add extra bits from its components file.
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
    Returns an Edit_Object for the given asset style game_file,
    applying a set of custom Item building macros.
    '''
    object_list = []
    for game_file in game_files:
        name = game_file.asset_name

        # Create an Edit_Object using the asset name.
        edit_object = Edit_Object(name)
        object_list.append( edit_object )

        # Fill in standard terms.
        Fill_Macro_Object_Standard_Items(game_file, edit_object)

        # Fill in custom terms.
        edit_object.Make_Items(game_file, custom_item_macros)
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
    _E('t_name_entry'         , './macro/properties/identification'   , 'name'         , 'T Name Entry', ''),
    # TODO: maybe description; would need to think of
    # a special way to show this that is legible.
    _D('description'          , Update_Description                                     , 'Description', ''),
    _E('t_descrip_entry'      , './macro/properties/identification'   , 'description'  , 'T Desc. Entry', ''),
    _E('codename'             , './macro'                             , 'name'         , 'Codename', '', read_only = True),
    _E('macro_class'          , './macro'                             , 'class'        , 'Class', '', read_only = True),
    _E('component'            , './macro/component'                   , 'ref'          , 'Component', '', read_only = True),
    ]
_component_item_macros = [
    _E('connection_name'       , 'connection_xpath'       , 'name'         , 'Connection Name', ''),
    _E('connection_tags'       , 'connection_xpath'       , 'tags'         , 'Connection Tags', ''),
    ]



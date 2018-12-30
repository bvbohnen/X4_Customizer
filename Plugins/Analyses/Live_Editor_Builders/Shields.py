

from itertools import chain
from collections import OrderedDict, defaultdict
import time

from Framework import File_System, Settings, Print
from Framework.Live_Editor_Components import *

# Convenience macro renaming.
E = Edit_Item_Macro
D = Display_Item_Macro

# TODO: maybe remove dependency on the Weapons transform code.
from ...Transforms.Weapons import Get_All_Weapons
from ...Transforms.Support import Float_to_String

from .Support import Create_Objects_From_Asset_Files


def _Build_Shield_Objects():
    '''
    Returns a list of Edit_Objects for all found shields.
    Meant for calling from the Live_Editor.
    '''    
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
    D('recharge_time'        , Calc_Recharge_Time                         , 'Recharge Time', ''),

    E('hull'                 , './/hull'                 , 'max'          , 'Hull', ''),
    E('hull_threshold'       , './/hull'                 , 'threshold'    , 'Hull Thr.', 'Hull Threshold'),
    ]



def _Build_Shield_Object_Tree_View():
    '''
    Constructs an Edit_Tree_View object for use in displaying
    shield data.
    '''
    # Set up a new table.
    object_tree_view = Edit_Tree_View('shields')

    # Get all of the objects.
    objects_list = Live_Editor.Get_Category_Objects('shields')

    # Organize by class, then by size.
    for object in objects_list:
        # Use the parsed name to label it.
        name      = object.Get_Item('name')     .Get_Value('current')

        # Size needs to be found in the tags.
        tags = object.Get_Item('connection_tags').Get_Value('current').split()
        for size in ['small','medium','large','extralarge']:
            if size in tags:
                break
            size = '?'

        object_tree_view.Add_Object(name, object, size)
        
    # Sort the tree in place when done.
    object_tree_view.Sort_Branches()

    # Apply default label filtering.
    object_tree_view.Apply_Filtered_Labels()

    return object_tree_view





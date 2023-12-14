'''
Support function(s) shared by analysis and transforms.
Initially just used for ship file loading.
'''
from Framework.Documentation import Doc_Category_Default
_doc_category = Doc_Category_Default('Analyses')

from Framework import File_System

def Get_Ship_Macro_Files():
    '''
    Finds and returns all ship macro game files.
    '''
    # Note: normally ship macros start with "ship_".
    # However, this doesn't find the XR shippack, since they all start
    # with "units_" instead; also over-includes on XR shippack since it calls
    # some docking bay macros "ship_storage_".
    File_System.Get_All_Indexed_Files('macros','ship_*')
    File_System.Get_All_Indexed_Files('macros','units_*')

    # Search out loaded assets, which already have checked the
    # class tags. Do this for each ship class.
    ret_list = []
    for suffix in ['xs','s','m','l','xl']:
        ret_list += File_System.Get_Asset_Files_By_Class('macros',f'ship_{suffix}')

    return ret_list

    
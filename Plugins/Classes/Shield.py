from .Macro import Macro
from .Connection import Connection
from .Component  import Component
from Framework import Transform_Wrapper, File_System, Print

__all__ = ['Shield']

class Shield(Macro):
    '''
    Shield macro.
    '''
    def __init__(self, xml_node, *args, **kwargs):
        super().__init__(xml_node, *args, **kwargs)
        return            

'''
For reference, paths/attributes of interest.

'./properties/recharge'                , 'max'  
'./properties/recharge'                , 'rate'  
'./properties/recharge'                , 'delay'  

'./properties/hull'                  , 'max'      
'./properties/hull'                  , 'integrated'

'''


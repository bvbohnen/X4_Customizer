
from .Macro import Macro
from .Connection import Connection
from .Component  import Component
from Framework import File_System

__all__ = ['Storage']

class Storage(Macro):
    '''
    Storage macro. This will be filled in as needed.

    * component_name
      - Name of the base component.
    * component
      - Component, filled in by Get_Component.
    '''

    def __init__(self, xml_node, *args, **kwargs):
        super().__init__(xml_node, *args, **kwargs)

        # Of notable interest is the main component
        self.component_name = xml_node.find('./component').get('ref')
        self.component = None

        # Read out info of interest, as it comes up.
        return

    def Get_makerrace(self):
        return self.Get('./properties/identification', 'makerrace')

    def Get_Tags(self):
        '''
        Returns a list of cargo tags. Expected to typically be one
        of 'solid','liquid','container'.
        '''
        return self.Get('./properties/cargo', 'tags').split()
    
    def Get_Volume(self):
        'Returns integer volume of the cargo bay.'
        return int(self.Get('./properties/cargo', 'max'))
        
    def Set_Volume(self, new_volume):
        'Set the volume of the cargo bay.'
        # Round it in case a float.
        self.Set('./properties/cargo', 'max', f'{round(new_volume)}')

    
'''
Reference paths:
'./properties/identification'        , 'makerrace'

'./properties/cargo'                 , 'max'
'./properties/cargo'                 , 'tags'

'./properties/hull'                  , 'max'
'./properties/hull'                  , 'integrated'
'''

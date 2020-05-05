
from .Macro import Macro
from .Connection import Connection
from .Component  import Component
from Framework import File_System

__all__ = ['Engine']

class Engine(Macro):
    '''
    Engine macro. This will be filled in as needed; many basic ship edits
    are done directly on the xml.
    TODO: move more ship stuff over to here.

    * component_name
      - Name of the base component.
    * component
      - Component, filled in by Get_Component.
    * engine_count
      - Number of engines.
    * engine_tags
      - Tags related to engine connections.
    '''

    def __init__(self, xml_node, *args, **kwargs):
        super().__init__(xml_node, *args, **kwargs)

        # Of notable interest is the main component
        self.component_name = xml_node.find('./component').get('ref')
        self.component = None

        # Read out info of interest, as it comes up.
        return

    def Get_mk(self):
        return self.Get('./properties/identification', 'mk')
    
    def Get_makerrace(self):
        return self.Get('./properties/identification', 'makerrace')

    def Get_Forward_Thrust(self):
        return self.Get('./properties/thrust', 'forward')
    

'''
For reference, paths/attributes of interest.

'./properties/identification'        , 'makerrace'
'./properties/identification'        , 'mk'       

'./properties/thrust'                , 'forward'  
'./properties/thrust'                , 'reverse'  

'./properties/thrust'                , 'strafe'   
'./properties/thrust'                , 'pitch'    
'./properties/thrust'                , 'yaw'      
'./properties/thrust'                , 'roll'     

'./properties/boost'                 , 'duration' 
'./properties/boost'                 , 'thrust'   
'./properties/boost'                 , 'attack'   
'./properties/boost'                 , 'release'  

'./properties/travel'                , 'charge'   
'./properties/travel'                , 'thrust'   
'./properties/travel'                , 'attack'   
'./properties/travel'                , 'release'  

'./properties/hull'                  , 'max'      
'./properties/hull'                  , 'threshold'

'./properties/effects/boosting'      , 'ref'      
'./properties/sounds/enginedetail'   , 'ref'      

'''
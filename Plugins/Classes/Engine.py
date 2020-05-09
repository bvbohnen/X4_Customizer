
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
    
    def Get_Purpose(self):
        # This is not stored anywhere, but is implicit in the name.
        for purpose in ['combat','allround','travel']:
            if purpose in self.name:
                return purpose
        return None
    
    def Get_Size(self):
        # Check the tags.
        tags = self.Get_Component_Connection_Tags()
        for size in ['small','medium','large','extralarge']:
            if size in tags:
                return size
        return None
    

    def Get_Forward_Thrust(self):
        return float(self.Get('./properties/thrust', 'forward'))
    
    def Get_Boost_Thrust(self):
        forward_thrust = self.Get_Forward_Thrust()
        mult = float(self.Get('./properties/boost', 'thrust'))
        return forward_thrust * mult
    
    def Get_Travel_Thrust(self):
        forward_thrust = self.Get_Forward_Thrust()
        mult = float(self.Get('./properties/travel', 'thrust'))
        return forward_thrust * mult

    def Get_Boost_Time(self):
        return float(self.Get('./properties/boost', 'duration'))
        
    def Set_Boost_Time(self, new_time):
        self.Set('./properties/boost', 'duration', f'{new_time:.2f}')


    def Set_Forward_Thrust_And_Rescale(self, new_thrust):
        '''
        Set a new forward thrust value, and rescale other thrusts to
        match the relative change.
        '''
        old = self.Get_Forward_Thrust()
        mult = new_thrust / old
        # Set the new thrust directly.
        self.Set('./properties/thrust', 'forward', f'{new_thrust:.3f}')
        # Scale others.
        for field in ['reverse', 'strafe', 'pitch', 'yaw', 'roll']:
            old = self.Get('./properties/thrust', field)
            # Normal race engines don't have most of these properties.
            if old == None:
                continue
            new = float(old) * mult
            self.Set('./properties/thrust', field, f'{new:.3f}')
        return
        
    def Set_Boost_Thrust(self, new_thrust):
        # Backcompute the multiplier needed.
        forward_thrust = self.Get_Forward_Thrust()
        mult = new_thrust / forward_thrust
        self.Set('./properties/boost', 'thrust', f'{mult:.3f}')
    
    def Set_Travel_Thrust(self, new_thrust):
        # Backcompute the multiplier needed.
        forward_thrust = self.Get_Forward_Thrust()
        mult = new_thrust / forward_thrust
        self.Set('./properties/travel', 'thrust', f'{mult:.3f}')
    
    def Set_Travel_Mult(self, new_mult):
        self.Set('./properties/travel', 'thrust', '1')
        
    def Set_Travel_Charge(self, new_mult):
        self.Set('./properties/travel', 'charge', '0')


    def Remove_Travel(self):
        'Remove the travel subelement from the engine. Untested.'
        self.Remove('./properties/travel')
    

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
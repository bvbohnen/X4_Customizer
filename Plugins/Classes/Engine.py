
from .Macro import Macro
from .Connection import Connection
from .Component  import Component
from Framework import File_System, Print

__all__ = ['Engine']

class Engine(Macro):
    '''
    Engine macro.
    '''
    def __init__(self, xml_node, *args, **kwargs):
        super().__init__(xml_node, *args, **kwargs)
        return

    def Get_mk(self):
        'Get engine mark, as string, or None if not specified.'
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
        'Returns boost bonus thrust strength, or None if boost undefined.'
        forward_thrust = self.Get_Forward_Thrust()
        mult_str = self.Get('./properties/boost', 'thrust')
        if not mult_str:
            return
        # Subtract the 1 from base thrust.
        mult = float(mult_str) - 1
        return forward_thrust * mult
    
    def Get_Travel_Thrust(self):
        'Returns travel bonus thrust strength, or None if boost undefined.'
        forward_thrust = self.Get_Forward_Thrust()
        mult_str = self.Get('./properties/travel', 'thrust')
        if not mult_str:
            return
        # Subtract the 1 from base thrust.
        mult = float(mult_str) - 1
        return forward_thrust * mult

    def Get_Boost_Time(self):
        'Returns boost time, or None if boost undefined.'
        time_str = self.Get('./properties/boost', 'duration')
        if not time_str:
            return
        return float(time_str)
        
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
        # Add 1 for base thrust.
        mult += 1
        self.Set('./properties/boost', 'thrust', f'{mult:.3f}')
    
    def Set_Travel_Thrust(self, new_thrust):
        # Backcompute the multiplier needed.
        forward_thrust = self.Get_Forward_Thrust()
        mult = new_thrust / forward_thrust
        # Add 1 for base thrust.
        mult += 1
        self.Set('./properties/travel', 'thrust', f'{mult:.3f}')            

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

from .Macro import Macro
from .Connection import Connection
from .Component  import Component
from Framework import File_System

__all__ = ['Ship']

class Ship(Macro):
    '''
    Ship macro. This will be filled in as needed; many basic ship edits
    are done directly on the xml.
    TODO: move more ship stuff over to here.

    * engine_count
      - Int, number of engines.
    * engine_tags
      - Set of tags related to engine connections, including 'engine'.
    '''

    def __init__(self, xml_node):
        super().__init__(xml_node)

        # Read out info of interest, as it comes up.
        return

    def Get_Game_Name(self):
        'Return the in-game name of this ship.'
        if self.game_name == None:
            self.game_name = File_System.Read_Text(self.xml_root.find('./properties/identification').get('name'))
        return self.game_name

    def Load_Engine_Data(self):
        'Helper function that loads engine count and tags.'
        component = self.Get_Component()

        # Search the connections.
        self.engine_count = 0
        self.engine_tags = []
        for conn in component.conns.values():
            if 'engine' in conn.tags:
                self.engine_count += 0
                self.engine_tags = conn.tags
        return


    def Get_Engine_Count(self):
        'Returns the number of engine connections.'
        self.Load_Engine_Data()
        return self.engine_count

    def Get_Engine_Tags(self):
        'Returns the engine connection tags.'
        self.Load_Engine_Data()
        return self.engine_tags

    # TODO: some function somewhere which links a ship with engines,
    # picked based on connection tag matching and whatever other criteria,
    # and annotated back to here for convenience.
    # Maybe a Loadout class?

        
'''
    For reference, paths/attributes of interest.
    './properties/identification'   , 'name'
    './properties/identification'   , 'description' 
    '.'                             , 'name'        
    '.'                             , 'class'       
    './component'                   , 'ref'        
    './properties/ship'                , 'type'   
    './properties/purpose'             , 'primary'
    './properties/hull'                , 'max'     
    './properties/explosiondamage'     , 'value'   
    './properties/people'              , 'capacity'
    './properties/storage'             , 'missile' 
    './properties/thruster'            , 'tags'    
    './properties/secrecy'             , 'level'       
    './properties/sounds/shipdetail'   , 'ref'   
    './properties/sound_occlusion'     , 'inside'
    './properties/software' 
    './properties/physics'             , 'mass'      
    './properties/physics/inertia'     , 'pitch'     
    './properties/physics/inertia'     , 'yaw'       
    './properties/physics/inertia'     , 'roll'      
    './properties/physics/drag'        , 'forward'   
    './properties/physics/drag'        , 'reverse'   
    './properties/physics/drag'        , 'horizontal'
    './properties/physics/drag'        , 'vertical'  
    './properties/physics/drag'        , 'pitch'     
    './properties/physics/drag'        , 'yaw'       
    './properties/physics/drag'        , 'roll'      
'''
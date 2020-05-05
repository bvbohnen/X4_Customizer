
from .Macro import Macro
from .Connection import Connection
from .Component  import Component
from Framework import File_System

__all__ = [
    'Ship',
    ]


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

    def __init__(self, xml_node, *args, **kwargs):
        super().__init__(xml_node, *args, **kwargs)
        
        self.engine_count = None
        self.engine_tags = None
        self.engine_macro = None
        self._race = None
        return

    def Get_Game_Name(self):
        'Return the in-game name of this ship.'
        if not hasattr(self, '_game_name'):
            self._game_name = File_System.Read_Text(self.xml_node.find('./properties/identification').get('name'))
        return self._game_name


    def Get_Race(self):
        '''
        Returns the expected race for this ship, based on wares group,
        defaulting to argon if not found.
        '''
        if self._race == None:
            race = 'argon'
            wares_file = File_System.Load_File('libraries/wares.xml')
            xml_root = wares_file.Get_Root_Readonly()

            # /wares/ware[./component/@ref="ship_arg_l_destroyer_01_a_macro"]
            ware_entries = xml_root.xpath(f'./ware[./component/@ref="{self.name}"]')
            if ware_entries:
                assert len(ware_entries) == 1
                group = ware_entries[0].get('group')
                if group and group.startswith('ships_'):
                    # The race should be the term after "ships_".
                    race = group.replace('ships_', '')
            self._race = race
        return self._race


    def Load_Engine_Data(self):
        'Helper function that loads engine count and tags.'
        component = self.Get_Component()

        # Search the connections.
        self.engine_count = 0
        self.engine_tags = []
        for conn in component.conns.values():
            if 'engine' in conn.tags:
                self.engine_count += 1
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


    def Select_Engine(self, engine_macros, mk = None, makerrace = None):
        '''
        From the given engine macros, select a matching engine.
        '''
        matches = []

        # Add "component" to the engine tags, to match up with the other macro.
        engine_tags = self.Get_Engine_Tags()
        engine_tags.add('component')

        for macro in engine_macros:
            if macro.name == 'engine_arg_s_combat_01_mk2_macro' and self.name == 'ship_kha_m_fighter_01_a_macro':
                bla = 0
            macro_tags = macro.Get_Component_Connection_Tags()
            if macro_tags != engine_tags:
                continue
            if mk and macro.Get_mk() != mk:
                continue
            if makerrace and macro.Get_makerrace() != makerrace:
                continue
            matches.append(macro)

        if not matches:
            bla = 0

        # From matches, pick fastest engine.
        self.engine_macro = None
        for macro in matches:
            if not self.engine_macro or macro.Get_Forward_Thrust() > self.engine_macro.Get_Forward_Thrust():
                self.engine_macro = macro
        return

    def Get_Engine_Macro(self):
        'Return the currently selected engine macro.'
        return self.engine_macro

    def Get_Speed(self):
        'Return the ship speed with currently selected engine.'
        if not self.engine_macro:
            return 0
        thrust = float(self.engine_macro.Get_Forward_Thrust()) * self.engine_count
        drag = float(self.Get('./properties/physics/drag', 'forward'))
        speed = thrust / drag
        return speed


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
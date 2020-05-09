
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

    def Get_Ship_Type(self):
        return self.Get('./properties/ship', 'type')

    def Get_Primary_Purpose(self):
        return self.Get('./properties/purpose', 'primary')


    #def Get_Race(self):
    #    '''
    #    Returns the expected race for this ship, based on wares group,
    #    defaulting to argon if not found.
    #    '''
    #    if self._race == None:
    #        race = 'argon'
    #        wares_file = File_System.Load_File('libraries/wares.xml')
    #        xml_root = wares_file.Get_Root_Readonly()
    #
    #        # /wares/ware[./component/@ref="ship_arg_l_destroyer_01_a_macro"]
    #        ware_entries = xml_root.xpath(f'./ware[./component/@ref="{self.name}"]')
    #        if ware_entries:
    #            assert len(ware_entries) == 1
    #            group = ware_entries[0].get('group')
    #            if group and group.startswith('ships_'):
    #                # The race should be the term after "ships_".
    #                race = group.replace('ships_', '')
    #        self._race = race
    #    return self._race


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


    def Select_Engine(
            self, 
            engine_macros, 
            mk = None, 
            match_owner = True,
            owner = None,
            ):
        '''
        From the given engine macros, select a matching engine.
        '''
        # There might be a specified loadout in the ship macro.
        loadouts = self.xml_node.xpath('.//loadout')
        for loadout in loadouts:
            # Just check the first one for an engine macro.
            engine_node = loadout.find('./macros/engine')
            if engine_node != None and engine_node.get('macro'):
                engine_macro_name = engine_node.get('macro')
                # Look up this engine.
                macro = self.database.Get_Macro(engine_macro_name)
                if macro:
                    self.engine_macro = macro
                    return
                
        # If here, search for a matching engine.
        matches = []

        # Find factions that can make the ship. As set for lookups.
        ship_factions = set(self.Get_Ware_Factions())
        # Use owner if given, and there are factions involved.
        if ship_factions and owner:
            ship_factions = set([owner])
            
        # The rules for component matching are unclear, but it is not
        # simply a direct tag group match, but some sort of subgroup match.
        # Eg. ship-side {'platformcollision', 'engine', 'medium'}
        # should match engine-side {'medium', 'engine', 'component'},
        # where only two terms are common.
        # In some cases, the ship won't have a size specifier, nor does
        # a generic_engine.

        # Try gathering select tags, for use in an exact match.
        # Start with component.
        engine_tags = ['component']
        valid_tags = ['small', 'medium', 'large', 'extralarge', 'engine', 'spacesuit', 'bomb']
        for tag in self.Get_Engine_Tags():
            if tag in valid_tags:
                engine_tags.append(tag)
        # Convert to set for match checks.
        engine_tags = set(engine_tags)

        for macro in engine_macros:
            macro_tags = macro.Get_Component_Connection_Tags()
            if not macro_tags == engine_tags:
                continue
            if mk and macro.Get_mk() != mk:
                continue

            if ship_factions and match_owner:
                # Find factions that can make the engine.
                engine_factions = macro.Get_Ware_Factions()
                # Check for no overlap.
                if not any(x in ship_factions for x in engine_factions):
                    continue

            matches.append(macro)

        # From matches, pick fastest engine.
        self.engine_macro = None
        this_thrust = None
        for macro in matches:
            macro_thrust = macro.Get_Forward_Thrust()
            if not self.engine_macro or macro_thrust > this_thrust:
                self.engine_macro = macro
                this_thrust = self.engine_macro.Get_Forward_Thrust()

        return

    def Get_Engine_Macro(self):
        'Return the currently selected engine macro.'
        return self.engine_macro

    def Get_Speed(self):
        'Return the ship speed with currently selected engine.'
        if not self.engine_macro:
            return 0
        thrust = float(self.engine_macro.Get_Forward_Thrust()) * self.Get_Engine_Count()
        drag = float(self.Get('./properties/physics/drag', 'forward'))
        speed = thrust / drag
        return speed


    def Adjust_Speed(self, multiplier):
        '''
        Adjust the speed and acceleration of this ship based on the
        given multiplier.
        This applies the inverse multiplier to the ship's drag and mass.
        '''
        # The fields to change are scattered under the physics node.        
        path_attrs = [
            ('./properties/physics', 'mass'),
            ('./properties/physics/drag', 'forward'),
            ('./properties/physics/drag', 'reverse'),
            ('./properties/physics/drag', 'horizontal'),
            ('./properties/physics/drag', 'vertical'),
            ]

        for path, attr in path_attrs:
            value = float(self.Get(path, attr))
            new_value = value / multiplier
            self.Set(path, attr, f'{new_value:0.4f}')
        return

    
    def Adjust_Turning(self, multiplier):
        '''
        Adjust the turning rate of this ship based on the given multiplier.
        This applies the inverse multiplier to the ship's inertia.
        '''
        path_attrs = [
            ('./properties/physics/inertia', 'pitch'),
            ('./properties/physics/inertia', 'yaw'),
            ('./properties/physics/inertia', 'roll'),
            ]
        
        for path, attr in path_attrs:
            value = float(self.Get(path, attr))
            new_value = value / multiplier
            self.Set(path, attr, f'{new_value:0.4f}')
        return

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

from Framework import Load_File, File_System, Plugin_Log, File_Manager

from collections import defaultdict
from lxml import etree
from lxml.etree import Element
import fnmatch


from .Macro import *
from .Component import *

from .Ship import *
from .Engine import *

__all__ = ['Database']

# TODO: better way to match x4 classes to local classes.
class_name_to_macro = {
    'spacesuit': Ship,
    'ship_xs' : Ship,
    'ship_s'  : Ship,
    'ship_m'  : Ship,
    'ship_l'  : Ship,
    'ship_xl' : Ship,
    'engine'  : Engine,
    }

class Database:
    '''
    Container for various loaded macros and components, handling cross
    connections. This should be recreated for each transform, to
    update xml links properly. This focuses on macros, which will look
    up their own components dynamically. Components are read only for now.

    * gamefile_roots
      - Dict matching Game_Files to their xml root nodes (to be edited).
    * class_macros
      - Dict, keyed by macro class (eg. 'engine'), holding a subdict of
        macros keyed by name.
    * macros
      - Dict of all macros, keyed by lowercase name, collected from the above.
    * class_components
      - Dict, keyed by component class (eg. 'engine'), holding a subdict of
        components keyed by name.
    * components
      - Dict of all components, keyed by lowercase name, collected from the above.
    '''
    def __init__(self):
        self.gamefile_roots = {}
        self.macros = {}
        self.class_macros = defaultdict(dict)
        self.components = {}
        self.class_components = defaultdict(dict)

        self._get_macros_cache = set()
        self._get_components_cache = set()

        # TODO: the below as needed; for now let macro classes fill refs
        # as needed.
        ## For every connection, find its macro link.
        #for subdict in self.class_macros.values():
        #    for macro in subdict.values():
        #        for connection in macro.conns.values():
        #            if connection.macro_ref:
        #                macro = self.macros.get(connection.macro_ref)
        #                # Note: may go unfound if referring to outside assets.
        #                if macro:
        #                    connection.Set_Macro(macro)
        return

                            

    def Load_File(self, game_file):
        '''
        Loads a game file into this database, generating an xml_root copy
        and recording macros and components.
        Skips if not an xml file.
        '''
        if not isinstance(game_file, File_Manager.XML_File):
            return
        # Skip if already loaded.
        if game_file in self.gamefile_roots:
            return

        xml_root = game_file.Get_Root()
        # Record the root.
        self.gamefile_roots[game_file] = xml_root

        # Search it.
        for macro in xml_root.xpath("./macro"):
            class_name = macro.get('class')
            object = class_name_to_macro[class_name](macro, self)

            self.class_macros[class_name][object.name] = object
            self.macros[object.name.lower()] = object

        for component in xml_root.xpath("./component"):
            class_name = component.get('class')
            object = Component(component, self)
                
            self.class_components[class_name][object.name] = object
            self.components[object.name.lower()] = object

        return


    def Get_Macro(self, macro_name):
        '''
        Returns a Macro object (likely a subclass) with the given name.
        '''
        # Reuse the below, and unpack the list.
        macros = self.Get_Macros(macro_name)
        return macros[0]

    def Get_Macros(self, pattern):
        '''
        Returns a list of Macros with names matching the given pattern.
        '''
        # Cache patterns seen, to skip index lookup.
        if pattern not in self._get_macros_cache:
            self._get_macros_cache.add(pattern)

            # The index will match macro names to files, where a file can
            # hold multiple macros. Start by getting the files.
            game_files = File_System.Get_All_Indexed_Files('macros', pattern)

            # Add each file to the database, loading macros, xml, etc, skipping
            # those already loaded.
            for game_file in game_files:
                self.Load_File(game_file)

        # Now pick out the actual macros.
        macro_names = fnmatch.filter(self.macros.keys(), pattern.lower())
        return [self.macros[x] for x in macro_names]

    
    def Get_Component(self, component_name):
        '''
        Returns a Component object with the given name.
        '''
        # Reuse the below, and unpack the list.
        components = self.Get_Components(component_name)
        return components[0]


    def Get_Components(self, pattern):
        '''
        Returns a list of Components with names matching the given pattern.
        '''
        # Cache patterns seen, to skip index lookup.
        if pattern not in self._get_components_cache:
            self._get_components_cache.add(pattern)

            # The index will match names to files, where a file can
            # hold multiple macros. Start by getting the files.
            game_files = File_System.Get_All_Indexed_Files('components', pattern)

            # Add each file to the database, loading macros, xml, etc, skipping
            # those already loaded.
            for game_file in game_files:
                self.Load_File(game_file)

        # Now pick out the actual components.
        component_names = fnmatch.filter(self.components.keys(), pattern.lower())
        return [self.components[x] for x in component_names]



    def Update_XML(self):
        '''
        Update changed xml nodes, and write modified roots back to
        their game files.
        '''
        for macro in self.macros.values():
            macro.Update_XML()
        for comp in self.components.values():
            comp.Update_XML()
        # TODO: automate gamefile writebacks or not? How to know which changed?
        #for game_file, new_root in self.gamefile_roots.items():
        #    game_file.Update_Root(new_root)
        return
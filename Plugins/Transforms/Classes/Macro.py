
from .Connection import Connection
__all__ = ['Macro']

class Macro:
    '''
    Generic macro, holding a set of connections.
    
    * xml_node
      - Macro xml node.
    * class_name
      - String, class name.
    * conns
      - Dict of Connections, keyed by a tuple of (name, ref), where name
        may be None.
    * parent_conns
      - List of external connections that link to this macro (will belong to
        some other macro).
      - Filled in post-init.
    * component_name
      - Name of the base component
    * component
      - Component, filled in by Get_Component.
    '''
    def __init__(self, xml_node):
        self.xml_node = xml_node
        self.name = xml_node.get('name')
        self.class_name = xml_node.get('class')
        
        self.component_name = xml_node.find('./component').get('ref')
        self.component = None

        self.parent_conns = []
        self.conns = {}
        for conn_node in xml_node.xpath("./connections/connection"):
            conn = Connection(self, conn_node)
            # Verify the name/ref combo hasn't been seen.
            key = (conn.name, conn.ref)
            assert key not in self.conns
            self.conns[key] = conn
        return
    
    def Get_Component(self):
        '''
        Returns the component for this macro.
        '''
        if self.component == None:
            # Load from the index.
            game_file = File_System.Get_Indexed_File('components', self.component_name)
            # If not found, error.
            if game_file == None:
                return
            # Load its xml into a Component and store.
            # TODO: will this always be readonly? Can speed up if so.
            self.component = Component(game_file.Get_XML_Root())
        return self.component
    

    def Get_Component_Connection_Tags(self):
        '''
        Returns the component connection tags, including 'component', or
        None if there is no such connection.
        '''
        comp = self.Get_Component()
        for conn in comp.conns.values():
            # Looking for a 'component' tag.
            if 'component' in conn.tags:
                return conn.tags
        return


    def Update_XML(self):
        '''
        Update the xml node positions of all connections.
        May be wrapped by subclasses to fill in extra changes.
        '''
        # TODO: maybe also update component.

        for connection in self.conns.values():
            connection.Update_XML()
        return


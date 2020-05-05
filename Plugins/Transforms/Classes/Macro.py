
from Framework import Load_File, File_System, Plugin_Log
from .Connection import Connection
from .Component import Component
__all__ = ['Macro']

class Macro:
    '''
    Generic macro, holding a set of connections.
    
    * database
      - Database recording this macro.
    * xml_node
      - Macro xml node.
    * name
      - String, name.
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
    def __init__(self, xml_node, database = None):
        self.xml_node = xml_node
        self.database = database
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


    def Get(self, xpath, attr):
        '''
        Return an attribute or element matching the given xpath and attribute.
        '''
        node = self.xml_node.find(xpath)
        if node != None:
            return node.get(attr)
        return
    
    def Set(self, xpath, attr, value):
        '''
        Set an attribute matching the given xpath and attribute.
        '''
        self.xml_node.find(xpath).set(attr, value)
    

    def Get_Component(self):
        '''
        Returns the component for this macro.
        '''
        if self.component == None:
            self.component = self.database.Get_Component(self.component_name)
        return self.component
    

    def Get_Component_Connection_Tags(self):
        '''
        Returns the component connection tags, including 'component', or
        None if there is no such connection.
        '''
        return self.Get_Component().Get_Connection_Tags()


    def Update_XML(self):
        '''
        Update the xml node positions of all connections.
        May be wrapped by subclasses to fill in extra changes.
        '''
        # TODO: maybe also update component.

        for connection in self.conns.values():
            connection.Update_XML()
        return


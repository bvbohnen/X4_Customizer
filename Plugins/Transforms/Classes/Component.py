
from .Connection import Connection
from Framework import File_System

__all__ = 'Component'

class Component:
    '''
    Component, eg. defining a ship model or similar.
    
    * xml_node
      - Component xml node.
    * conns
      - Dict of Connections, keyed by a tuple of (name, ref), where name
        or ref may be None.
    '''
    def __init__(self, xml_node):
        self.xml_node = xml_node

        self.conns = {}
        for conn_node in xml_node.xpath("./connections/connection"):
            conn = Connection(self, conn_node)
            # Verify the name/ref combo hasn't been seen.
            key = (conn.name, conn.ref)
            assert key not in self.conns
            self.conns[key] = conn
        return
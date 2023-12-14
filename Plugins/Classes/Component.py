
from Framework.Documentation import Doc_Category_Default
_doc_category = Doc_Category_Default('Classes')

from .Connection import Connection
from Framework import File_System

__all__ = ['Component']

class Component:
    '''
    Component, eg. defining a ship model or similar.
    
    * database
      - Database recording this macro.
    * xml_node
      - Component xml node.
    * class_name
      - String, class name.
    * modified
      - Bool, True if this macro's xml is modified.
    * name
      - String, name.
    * conns
      - Dict of Connections, keyed by a tuple of (name, ref), where name
        or ref may be None.
    '''
    def __init__(self, xml_node, database = None):
        self.xml_node = xml_node
        self.database = database
        self.modified = False
        self.name = xml_node.get('name')
        self.class_name = xml_node.get('class')

        self.conns = {}
        for conn_node in xml_node.xpath("./connections/connection"):
            conn = Connection(self, conn_node)
            # Verify the name/ref combo hasn't been seen.
            key = (conn.name, conn.ref)
            # Just skip same-name keys for now.
            # TODO: how to handle these?  eg. 'ship_gen_xs_repairdrone_01'
            # has two "test_weld_effect".
            if key in self.conns:
                continue
            self.conns[key] = conn
            
        self._connection_tags = None
        return
    
    def Replace_XML(self, replacements):
        '''
        Swap xml element references out for their replacements. 
        Called when switching to writable xml.
        '''
        self.xml_node = replacements[self.xml_node]
        for conn in self.conns.values():
            conn.Replace_XML(replacements)
        return

    def Get_Connection_Tags(self):
        '''
        Returns the component connection tags, including 'component', or
        an empty set if there is no such connection.
        '''
        if self._connection_tags == None:
            self._connection_tags = set()
            for conn in self.conns.values():
                # Looking for a 'component' tag.
                if 'component' in conn.tags:
                    self._connection_tags = conn.tags
                    break
        return self._connection_tags

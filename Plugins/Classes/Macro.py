
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
    * modified
      - Bool, True if this macro's xml is modified.
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
        self.modified = False
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

    def Replace_XML(self, replacements):
        '''
        Swap xml element references out for their replacements. 
        Called when switching to writable xml.
        '''
        self.xml_node = replacements[self.xml_node]
        for conn in self.conns.values():
            conn.Replace_XML(replacements)
        return

    def Get(self, xpath, attr, default = None):
        '''
        Return an attribute or element matching the given xpath and attribute.
        '''
        node = self.xml_node.find(xpath)
        if node != None:
            return node.get(attr)
        return default
    
    def Set(self, xpath, attr, value):
        '''
        Set an attribute matching the given xpath and attribute name.
        XML is updated directly, and modified flag set.
        '''
        # First, skip if the xpath doesn't match anything.
        if self.xml_node.find(xpath) == None:
            # TODO: maybe warning.
            return
                
        self.database.Set_Object_Writable(self)
        self.xml_node.find(xpath).set(attr, value)
        self.modified = True          
        return

    def Remove(self, xpath):
        '''
        Remove matching subnodes, if found.
        '''
        self.database.Set_Object_Writable(self)
        nodes = self.xml_node.xpath(xpath)
        for node in nodes:
            node.getparent().remove(node)
            self.modified = True
        return
    

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
    
    
    def Get_Game_Name(self):
        '''
        Return the in-game name of this macro, defaulting to the macro
        name if not found.
        '''
        if not hasattr(self, '_game_name'):
            # Default to macro name.
            self._game_name = self.name
            # Check for idenfication/name.
            ident_node = self.xml_node.find('./properties/identification')
            if ident_node != None:
                name_code = ident_node.get('name')
                if name_code:
                    self._game_name = File_System.Read_Text(name_code)
        return self._game_name
    

    def _Get_Ware_Node(self):
        '''
        Support function that returns a wares.xml node associated with
        this macro, or None. If there are multiple matches, returns the first.
        '''
        # TODO: add ware nodes to Database, and link to there.
        if not hasattr(self, '_ware_node'):
            wares_file = File_System.Load_File('libraries/wares.xml')
            xml_root = wares_file.Get_Root_Readonly()

            # Stupidly, the "component" node holds this macro name.
            ware_entries = xml_root.xpath(f'./ware[./component/@ref="{self.name}"]')
            if ware_entries:
                # Assume just one match.
                self._ware_node = ware_entries[0]
            else:
                self._ware_node = None
        return self._ware_node


    def Get_Ware_Factions(self):
        '''
        Returns a list of faction names which own the ware associated
        with this macro, or an empty list if none found.
        '''
        if not hasattr(self, '_ware_factions'):
            self._ware_factions = []

            ware_entry = self._Get_Ware_Node()
            if ware_entry != None:
                # Find the owners; multiple matches possible.
                owner_nodes = ware_entry.xpath('./owner')
                factions = []
                for node in owner_nodes:
                    # 'faction' attribute holds the name.
                    factions.append(node.get('faction'))
                self._ware_factions = factions
        return self._ware_factions


    def Get_Ware_Cost(self):
        '''
        Get the cost of the ware associated with this macro, or None if
        no cost found.
        '''
        if not hasattr(self, '_ware_cost'):
            self._ware_cost = None
            ware_entry = self._Get_Ware_Node()
            try:
                self._ware_cost = int(ware_entry.find('./price').get('average'))
            except Exception as ex:
                pass
        return self._ware_cost

    def Set_Float_Property(self, prop, attrib, val_change, op):
        xml_val = self.Get(f'./properties/{prop}', attrib)
        if not xml_val:
            return        
        val = float(xml_val)

        if(op == '+'):
            val = val + val_change
        elif(op == '*'):
            val = val * val_change
        elif(op=='='):
            val = val_change
        
        self.Set(f'./properties/{prop}', attrib, f'{val:.3f}')        
        
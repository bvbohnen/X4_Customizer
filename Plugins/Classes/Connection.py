
from copy import copy
from itertools import combinations

from .Position import Position

__all__ = ['Connection']

# TODO: directly link/register connections with the database.
class Connection:
    '''
    Generic connection, used by zones, sectors, etc.

    * parent
      - Macro or Component that holds this connection.
    * xml_node
    * name
      - Name attribute, or None.
    * tags
      - Set of strings holding tags.
    * ref
      - Ref attribute, if present.
    * macro_ref
      - String, name of the macro this connects to, if known.
    * macro
      - Macro that this connects to (filled in post-init), if a ref.
    '''
    def __init__(self, parent, xml_node):
        self.parent     = parent
        self.xml_node   = xml_node
        self.name       = xml_node.get('name')
        self.ref        = xml_node.get('ref')

        self.tags       = xml_node.get('tags')
        # Split them up, into a set for easy comparisons.
        if self.tags:
            self.tags = set(self.tags.split())
        else:
            self.tags = set()

        macro_node = xml_node.find('./macro')
        if macro_node != None:
            self.macro_ref  = macro_node.get('ref')
        else:
            self.macro_ref  = None
        self.macro = None
        return
    
    def Replace_XML(self, replacements):
        '''
        Swap xml element references out for their replacements. 
        Called when switching to writable xml.
        '''
        self.xml_node = replacements[self.xml_node]
        return

    def Get_Macro(self):
        '''
        Returns the connected Macro object, if a ref. If the macro isn't
        loaded yet, it will be loaded from the parent database. If this
        isn't a ref, returns None.
        '''
        if not self.macro and self.macro_ref:
            self.Set_Macro(self.parent.database.Get_Macro(self.macro_ref))
        return self.macro

    def Set_Macro(self, macro):
        '''
        Set the child macro this connection links to.
        '''
        self.macro = macro
        # Reverse link.
        macro.parent_conns.append(self)
        return
    
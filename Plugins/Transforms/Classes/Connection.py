
from copy import copy
from itertools import combinations

from .Position import Position

__all__ = ['Connection']

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
    * position
      - Current Position for this connection.
    * orig_position
      - Original Position when this connection was parsed.
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

        # TODO: maybe move position stuff to a map-specific subclass.
        pos_node        = xml_node.find('./offset/position')
        if pos_node != None:
            self.position = Position(pos_node)
        else:
            # When position is not specified, it seems to often default to 0,
            # so 0-fill here.
            # (Eg. happens regularly with one sector per cluster.)
            # TODO: is this always accurate? Maybe sometimes there is no
            # associated position.
            self.position = Position()

        # Make a safe copy as the original.
        self.orig_position = copy(self.position)
        return

    def Get_Offset(self):
        '''
        Returns a Position offset between the current position and
        original xml position.
        '''
        return self.position - self.orig_position

    def Set_Macro(self, macro):
        '''
        Set the child macro this connection links to.
        '''
        self.macro = macro
        # Reverse link.
        macro.parent_conns.append(self)
        return
    
    def Update_XML(self):
        '''
        Update the xml node position, if an xml_node attached.
        '''
        if self.position:
            self.position.Update_XML()
        return

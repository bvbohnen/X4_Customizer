
from copy import copy
from itertools import combinations

from .Position import Position
from .Region import Region
from ...Support import XML_Modify_Float_Attribute

__all__ = [
    'Connection',
    'Macro',
    'Region_Macro',
    'Zone',
    'Cluster',
    'Sector',
    ]

class Connection:
    '''
    Generic connection, used by zones, sectors, etc.

    * parent_macro
      - Macro that holds this connection.
    * xml_node
    * name
      - Name attribute, or None.
    * ref
      - Ref attribute (never None?).
    * position
      - Current Position for this connection.
    * orig_position
      - Original Position when this connection was parsed.
    * macro_ref
      - String, name of the macro this connects to, if known.
    * macro
      - Macro that this connects to (filled in post-init).
    '''
    def __init__(self, parent, xml_node):
        self.parent_macro = parent
        self.xml_node = xml_node
        self.name       = xml_node.get('name')
        self.ref        = xml_node.get('ref')

        macro_node = xml_node.find('./macro')
        if macro_node != None:
            self.macro_ref  = macro_node.get('ref')
        else:
            self.macro_ref  = None
        self.macro = None

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


class Macro:
    '''
    Generic macro, holding a set of connections.
    
    * xml_node
      - Macro xml node.
    * conns
      - Dict of Connections, keyed by a tuple of (name, ref), where name
        may be None.
    * parent_conns
      - List of external connections that link to this macro (will belong to
        some other macro).
      - Filled in post-init.
    * radius
      - Float, radius of this macro.
      - Objects should not move closer than their combined radiuses.
    * inner_radius
      - Float or None, objects already closer than the inner_radius
        can move freely, as long as the inner_radius is not breeched.
    '''
    def __init__(self, xml_node):
        self.xml_node = xml_node
        self.name = xml_node.get('name')
        self.parent_conns = []
        self.conns = {}
        # Generic default radius.
        self.radius = 6000
        self.inner_radius = None
        for conn_node in xml_node.xpath("./connections/connection"):
            conn = Connection(self, conn_node)
            # Verify the name/ref combo hasn't been seen.
            key = (conn.name, conn.ref)
            assert key not in self.conns
            self.conns[key] = conn
        return

    def Update_XML(self):
        '''
        Update the xml node positions of all connections.
        May be wrapped by subclasses to fill in extra changes.
        '''
        for connection in self.conns.values():
            connection.Update_XML()
        return

    def Contains_Gate(self):
        'Dummy function returns False, for easy of use with zones.'
        return False

    def Is_Damage_Region(self):
        'Convenience function to match up with Region verion; normally False.'
        return False


class Region_Macro(Macro):
    '''
    Special region dummy. These don't have connections like other macros.
    Regions are defined in Clusters, but associated with sectors later.

    * sector
      - The sector that is closest to this region.
    * region
      - The Region that this macro represents.
    '''
    def __init__(self, xml_node):
        super().__init__(xml_node)
        self.sector = None
        return

    def Set_Sector(self, sector):
        'Associate this region with the given sector.'
        self.sector = sector
        sector.cluster_connected_macros.append(self)
        return

    def Set_Region(self, region):
        'Link a region to this region macro.'
        self.region = region
        self.radius = region.radius
        self.inner_radius = region.inner_radius
        return
    
    def Is_Damage_Region(self):
        'True if this region does damage.'
        return self.region.does_damage
    
    def Update_XML(self):
        '''
        Update the connection for this region in the cluster, as well
        as the region itself (splines/etc.).
        '''
        super().Update_XML()
        self.region.Update_XML()
        return


class Zone(Macro):
    '''
    Basic zone info. Note: zone objects can be up to 50km or so away from
    the zone center.
    
    * god_objects
      - List of God_Objects that will be placed in this zone.
    * has_gate
      - Bool, True if this zone has a standard gate.
    * has_zone_highway
      - Bool, True if this zone has a zone highway entry or exit.
    * has_sector_highway
      - Bool, True if this zone has a sector highway entry or exit.
    '''
    def __init__(self, xml_node):
        super().__init__(xml_node)
        self.has_gate = False
        self.has_zone_highway = False
        self.has_sector_highway = False
        self.god_objects = []

        # Zones with standard gates have a connection of ref="gates" type.
        # This applies to accelerators as well.
        for conn in self.conns.values():
            if conn.ref == 'gates':
                self.has_gate = True

        # Set radius based on distances between internal objects.
        self.Update_Radius()
        return

    def Get_Sector_Conn(self):
        '''
        Returns the parent Sector Connection.
        '''
        # There are often two connections, so need to find the right one.
        for conn in self.parent_conns:
            if isinstance(conn.parent_macro, Sector):
                return conn
        raise Exception()

    def Contains_Gate(self):
        '''
        Returns True if this zone has a gate (including accelerator
        or zone highway).
        '''
        return self.has_gate or self.has_sector_highway

    # Note: unused currently.
    def Contains_Gate_Or_Highway(self):
        '''
        Returns True if this zone has a gate or highway entry/exit.
        '''
        return self.has_gate or self.has_zone_highway or self.has_sector_highway

    def Update_Radius(self):
        '''
        Update the radius.  Call this if a new object was added.
        '''
        # Set radius based on distances between internal objects.
        self.radius = self.Get_Size() / 2
        return
    
    def Get_Size(self):
        '''
        Returns approximate zone size, as a diamater.
        '''
        # Gather connections and god objects.
        objects = [x for x in self.conns.values()]
        objects += [x for x in self.god_objects if x.position]

        # Find the max distance between internal connections.
        # (These may all be skewed off to one side.)
        max_dist = 0
        for obj_0, obj_1 in combinations(objects, 2):
            pos_0 = obj_0.position
            pos_1 = obj_1.position
            this_dist = pos_0.Get_Distance_To(pos_1)
            if this_dist > max_dist:
                max_dist = this_dist

        # If 0 or 1 object, assume a standard size.
        if not max_dist:
            # Vanilla hand placed zones are spaced 10k apart or more.
            max_dist = 10000
        return max_dist

    def Get_Center(self):
        '''
        Returns the center point of this zone, based on connections
        and god objects.
        '''
        # Gather connections and god objects.
        objects = [x for x in self.conns.values()]
        objects += [x for x in self.god_objects if x.position]

        sum_pos = Position()
        # Some zones have no connections by default.
        if objects:
            for obj in objects:
                sum_pos += obj.position
            sum_pos /= len(objects)
        return sum_pos
    

class Cluster(Macro):
    '''
    Information on a cluster of sectors. Often just has one sector.
    '''
    def __init__(self, xml_node):
        super().__init__(xml_node)
    
        # Regions don't normally have defined macros, but they are handy
        # to normalize the processing, so add them.
        for conn in self.conns.values():
            if not conn.ref == 'regions':
                continue
            region_macro = Region_Macro(conn.xml_node.find('./macro'))
            conn.Set_Macro(region_macro)
        return


class Sector(Macro):
    '''
    Information on a cluster of sectors. Often just has one sector.

    * cluster_connected_macros
      - List of objects at the cluster level (initially just resource Regions)
        that associate with this sector.
    * md_objects
      - List of MD_Objects that will be placed in this sector.
    * god_objects
      - List of God_Objects that will be placed in this sector.
    * scaling_factor
      - Float, the scaling_factor applied to this sector.
    '''
    def __init__(self, xml_node):
        super().__init__(xml_node)
        self.cluster_connected_macros = []
        self.md_objects = []
        self.god_objects = []
        self.scaling_factor = 1
        return

    def Set_Scaling_Factor(self, scaling_factor):
        '''
        Set the scaling factor for this sector, possibly used in some
        runtime calculations. Has no direct effects.
        '''
        self.scaling_factor = scaling_factor

    def Remove_Highways(self):
        '''
        Removes all zone highways from this sector.
        Immediately edits the xml.
        '''
        to_remove = []
        for key, conn in self.conns.items():
            if conn.xml_node.get('ref') == 'zonehighways':
                conn.getparent().remove(conn)
                to_remove.append(key)
        for key in to_remove:
            del(self.conns[key])
        return
    

    def Get_Gate_Distance(self):
        '''
        Returns the maximum distance between any two gates, accelerators,
        or highways.  If there is just one, returns 0.
        '''
        conns = [x for x in self.conns.values()
                if x.macro and x.macro.Contains_Gate()]
        max_dist = 0

        # Find the highest inter-object distance.
        for conn_0, conn_1 in combinations(conns, 2):
            pos_0 = conn_0.position
            pos_1 = conn_1.position
            this_dist = pos_0.Get_Distance_To(pos_1)
            if this_dist > max_dist:
                max_dist = this_dist

        return max_dist


    def Get_Size(self):
        '''
        Returns approximate sector size, as a diamater, based on distances
        between zones in the sector, prioritizing gates and highways.
        Size will have a minimum based on the scaling factor.
        '''
        # Similar to sector.size property in game.
        # Presumably this is based on the gate distances.
        conns = [x for x in self.conns.values()
                if x.macro and x.macro.Contains_Gate()]

        # Check the gate distances.
        gate_dist = self.Get_Gate_Distance()
        # If the above was <50km, assume it was a single gate, single
        # sector-highway pair, or a couple gate/highway links placed
        # next to each other, such that the sector heart is further away
        # and needs to check all zones.
        if gate_dist < 50000:
            conns = [x for x in self.conns.values()]

        # Initialize this to the minimum.
        # Vanilla coresize has a min of ~425 km; that might be overkill,
        # but can go with half of that, scaled.
        max_dist = 425000 / 2 * self.scaling_factor

        # Find the highest inter-object distance.
        for conn_0, conn_1 in combinations(conns, 2):
            pos_0 = conn_0.position
            pos_1 = conn_1.position
            this_dist = pos_0.Get_Distance_To(pos_1)
            if this_dist > max_dist:
                max_dist = this_dist

        return max_dist


    def Get_Center(self):
        '''
        Returns the center point of this sector, based on gate zones,
        or all zones if there is only one gate.
        '''
        sum_pos = Position()
        
        # As above, use inter-gate region if gates >50km apart, else 
        # use everything with macros.
        gate_dist = self.Get_Gate_Distance()
        if gate_dist > 50000:
            conns = [x for x in self.conns.values()
                      if x.macro and x.macro.Contains_Gate()]
        else:
            conns = [x for x in self.conns.values() if x.macro]

        for conn in conns:
            # Count sector highways as half, since there are normally
            # (always) a pair of zones for the entry and exit.
            if isinstance(conn.macro, Zone) and conn.macro.has_sector_highway:
                sum_pos += conn.position / 2
            else:
                sum_pos += conn.position
        sum_pos /= len(conns)
        return sum_pos


    def Update_XML(self):
        super().Update_XML()

        # Fill in new zone nodes.
        # TODO
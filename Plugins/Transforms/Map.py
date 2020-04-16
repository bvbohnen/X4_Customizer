'''
Transforms to the map.
'''
from fnmatch import fnmatch
from collections import defaultdict
from copy import copy
import math
from itertools import combinations

from Framework import Transform_Wrapper, Load_File, Load_Files, Plugin_Log
from .Support import XML_Modify_Int_Attribute
from .Support import XML_Modify_Float_Attribute

'''
TODO:
- Adjust misc md scripts
  - PlacedObjects maybe.
    - Data vaults are close to center anyway (generally within 50km any dim).
    - Abandoned ships can be far, up to 1000km+ per dim.
- Change mass traffic draw distance in parameters.xml.
  - Generally want to reduce this due to performance.
  - Maybe optional, or separate transform.
- Stations still spawning far away, eg. 200+ km, sometimes.
  - Maybe innaccessible god code?
- Nap Fortune, further station at end of highway, 650 km from gate.
- Fix slight highway graphic doubling near zone gates (harmless, visual quirk).

- Sacred Relic spaced out; 250 km to furthest station.
- debuglog complaint about superhighway002_cluster_29_macro (Hatikvah) splines?


Note on regions:
    These are referenced in cluster.xml, but are defined over in
    libraries/region_definitions.xml. They mostly include resource fields,
    but also lockbox spawns, audio sounds, wrecks, etc.
  
Note: at a glance, vanilla zones can be as little as 9.5 km apart, though
    normally are further.  Sector highway gates are also spaces this much.
    

Note on gate sizing and distance:
    X4 gates are larger than X3.  Assuming 2x wider (not sure on exact ratio),
    then gates need to be 2x further away to have the same visual footprint.
    Assuming X3 has a 50 km gate-to-gate distance, and X4 has a ~230 km
    distance, then want a scaling of 100/230 = 0.43.
    TODO: check these numbers.

Note on travel times:
    X3 seta is up to 10x, X4 seta if 5x.
    X3 speeds are 125 typically, X4 are ~300 base and ~3k travel drive.
    (Can be lower, eg. 200 and 3k in x4, but depends wildly on engine).
    
    X4 time to cross AP: 230 km / 3kps = 76s (can't seta in travel)
    X4 time, no travel : 230 km / 300mps / 5 = 153s
    X3 time to cross AP: 50 km / 125mps / 10 = 40s (can seta)

    So X3 takes about half the time of X4 in general.
    If x4 travel drive removed, to meet x3 times, need scaling of 40/153= 0.26.
    To maint x4 travel drive times, need scaling of 76/153 = 0.5

Overall ideal scaling from the above is between 0.26 and 0.5.
Maybe aim for 0.33?

'''
@Transform_Wrapper()
def Scale_Sector_Size(
        scaling_factor,
        debug = True
    ):
    '''
    Change the size of the maps by moving contents (zones, etc.) closer
    together or futher apart. Note: this will require a new game to
    take effect, as positions become part of a save file.

    * scaling_factor
      - Float, how much to adjust distances by.
    * debug
      - Bool, if True then write runtime state to the plugin log.
    '''
    
    # Use a pattern to pick up the base and dlc sectors.
    # Store the game_file as key, xml root as value.
    # Below transforms exit the xml root, which gets committed at the end
    # if there were no errors.
    # Note: for testing, just grab the basic files, no wildcards.
    test = 1
    if test:
        gamefile_roots = {
        'sectors'       : [(x, x.Get_Root()) for x in [Load_File('maps/xu_ep2_universe/sectors.xml')]],
        'zones'         : [(x, x.Get_Root()) for x in [Load_File('maps/xu_ep2_universe/zones.xml')]],
        'zone_highways' : [(x, x.Get_Root()) for x in [Load_File('maps/xu_ep2_universe/zonehighways.xml')]],
        'clusters'      : [(x, x.Get_Root()) for x in [Load_File('maps/xu_ep2_universe/clusters.xml')]],
        'sec_highways'  : [(x, x.Get_Root()) for x in [Load_File('maps/xu_ep2_universe/sechighways.xml')]],
        'region_defs'   : [(x, x.Get_Root()) for x in [Load_File('libraries/region_definitions.xml')]],
        'md_hq'         : [(x, x.Get_Root()) for x in [Load_File('md/X4Ep1_Mentor_Subscription.xml')]],
        'md_stations'   : [(x, x.Get_Root()) for x in [Load_File('md/FactionLogic_Stations.xml')]],
        'god'           : [(x, x.Get_Root()) for x in [Load_File('libraries/god.xml')]],
        }
    else:
        gamefile_roots = {
        'sectors'       : [(x, x.Get_Root()) for x in Load_Files('*maps/xu_ep2_universe/*sectors.xml')],
        'zones'         : [(x, x.Get_Root()) for x in Load_Files('*maps/xu_ep2_universe/*zones.xml')],
        'zone_highways' : [(x, x.Get_Root()) for x in Load_Files('*maps/xu_ep2_universe/*zonehighways.xml')],
        'clusters'      : [(x, x.Get_Root()) for x in Load_Files('*maps/xu_ep2_universe/*clusters.xml')],
        'sec_highways'  : [(x, x.Get_Root()) for x in Load_Files('*maps/xu_ep2_universe/*sechighways.xml')],
        'region_defs'   : [(x, x.Get_Root()) for x in [Load_File('libraries/region_definitions.xml')]],
        'md_hq'         : [(x, x.Get_Root()) for x in [Load_File('md/X4Ep1_Mentor_Subscription.xml')]],
        'md_stations'   : [(x, x.Get_Root()) for x in [Load_File('md/FactionLogic_Stations.xml')]],
        'god'           : [(x, x.Get_Root()) for x in [Load_File('libraries/god.xml')]],
        }
        

    # Tweak faction logic to spawn stations closer/further.
    # (Maybe low priority.)
    faction_stations_file = Load_File('md/FactionLogic_Stations.xml')
    faction_stations_root = faction_stations_file.Get_Root()

    # Look up a couple nodes with 400km values.
    node_0 = faction_stations_root.xpath(".//match_distance[@max='[$ChosenSector.coresize / 2.0f, 400km].min']")[0]
    node_0.set('max', node_0.get('max').replace('400km', '{}km'.format(
        int(400 * scaling_factor))))
    node_1 = faction_stations_root.xpath(".//set_value[@exact='[$ChosenSector.size / 2.0f, 400km].min']")[0]
    node_1.set('exact', node_1.get('exact').replace('400km', '{}km'.format(
        int(400 * scaling_factor))))


    # FactionLogic.xml:
    # <match_distance space="$Sector" value="$Sector.coreposition" max="[$Sector.coresize, 400km].min"/>
    faction_logic_file = Load_File('md/FactionLogic.xml')
    faction_logic_root = faction_logic_file.Get_Root()

    # Look up a couple nodes with 400km values.
    node_0 = faction_logic_root.xpath(".//match_distance[@max='[$Sector.coresize, 400km].min']")[0]
    node_0.set('max', node_0.get('max').replace('400km', '{}km'.format(
        int(400 * scaling_factor))))


    # Load in data of interest, to the local data structure.
    galaxy = Galaxy(gamefile_roots)

    # Run the repositioning routines.
    Scale_Regions(galaxy, scaling_factor, debug)
    Scale_Sectors(galaxy, scaling_factor, debug)

    # Update the xml nodes.
    galaxy.Update_XML()


    # Tweak the main plot player HQ placement.
    # TODO

    
    # If here, everything worked, so commit the updates.
    for file_roots in gamefile_roots.values():
        # TODO: maybe skip clusters, as unmodified.
        for game_file, new_root in file_roots:
            game_file.Update_Root(new_root)

    faction_stations_file.Update_Root(faction_stations_root)
    faction_logic_file.Update_Root(faction_logic_root)

    return


# TODO: drop support for y, maybe.
class Position:
    '''
    Position of an object, typically either in a sector or in a cluster.

    * xml_node
      - Position node from the xml, or None if nothing associated.
    * x,y,z
      - Floats, current position.
      - May differ from the original xml.
    '''
    def __init__(self, xml_node = None, x = None, y = None, z = None):
        self.xml_node = xml_node
        if xml_node != None:
            # Sometimes a dim is forgotten; treat as 0.
            for attr in ['x','y','z']:
                val_str = xml_node.get(attr)
                if val_str:
                    value = float(val_str)
                else:
                    value = 0.0
                setattr(self, attr, value)
        else:
            assert x != None and y != None and z != None
            self.x = x
            self.y = y
            self.z = z
        return

    def Update_XML(self):
        '''
        Apply the current position back to the xml node.
        Should be called at the end of all processing.
        '''
        if self.xml_node != None:
            self.xml_node.set('x', str(int(self.x)))
            self.xml_node.set('y', str(int(self.y)))
            self.xml_node.set('z', str(int(self.z)))
        return

    def Update(self, other):
        '''
        Update this position to match a given other position.
        The xml_node link is retained.
        '''
        for attr in ['x','y','z']:
            setattr(self, attr, getattr(other, attr))
        return
    
    def __add__(self, other):
        assert isinstance(other, Position)
        ret_pos = copy(self)
        for attr in ['x','y','z']:
            setattr(ret_pos, attr, getattr(self, attr) + getattr(other, attr))
        return ret_pos

    def __sub__(self, other):
        assert isinstance(other, Position)
        ret_pos = copy(self)
        for attr in ['x','y','z']:
            setattr(ret_pos, attr, getattr(self, attr) - getattr(other, attr))
        return ret_pos
        
    def __mul__(self, other):
        assert isinstance(other, (int, float))
        ret_pos = copy(self)
        for attr in ['x','y','z']:
            setattr(ret_pos, attr, getattr(self, attr) * other)
        return ret_pos
    
    def __truediv__(self, other):
        assert isinstance(other, (int, float))
        ret_pos = copy(self)
        for attr in ['x','y','z']:
            setattr(ret_pos, attr, getattr(self, attr) / other)
        return ret_pos
    
    def Get_Distance(self, other = None):
        '''
        Returns the distance to 0,0,0.
        '''
        return math.sqrt((self.x ** 2) + (self.y ** 2) + (self.z ** 2))
    
    def Get_Distance_To(self, other):
        '''
        Returns the distance between this pos and another position.
        '''
        return math.sqrt(((self.x - other.x) ** 2) 
                         + ((self.y - other.y) ** 2) 
                         + ((self.z - other.z) ** 2))

    def Is_Within_Distance(self, other, distance):
        '''
        Returns True if this pos and the other pos are within the
        given distance.
        '''
        # This is checked often, so will use some fancier logic to fast
        # fail on distance objects.
        squared_sum = 0
        for attr in ['x','y','z']:
            offset = abs(getattr(self, attr) - getattr(other, attr))
            # If any single dim is greater than the distance, then this
            # will always be False.
            if offset > distance:
                return False
            squared_sum += offset ** 2

        this_distance = squared_sum ** 0.5
        if this_distance <= distance:
            return True
        return False

    def __str__(self):
        return '[x= {:.0f}, y= {:.0f}, z= {:.0f}]'.format(self.x, self.y, self.z)

    
class Spline_Position(Position):
    '''
    Special position node for highway splines. Works like a position, but
    also has additional fields that can be modified directly.

    * tx,ty,tz
      - Floats, curve of the highway at this point.
    * inlength, outlength
      - Floats, how long before/after this point the highway should flatten.
      - Entry spline should have inlength of 0; exit spline outlength of 0.
    '''
    def __init__(self, xml_node):
        super().__init__(xml_node)
        for attr in ['tx','ty','tz','inlength','outlength']:
            setattr(self, attr, float(xml_node.get(attr)))
        return

    def Update_XML(self):
        '''
        Apply the current position back to the xml node.
        Should be called at the end of all processing.
        '''
        super().Update_XML()
        for attr in ['tx','ty','tz']:
            self.xml_node.set(attr, str(getattr(self, attr)))
        for attr in ['inlength','outlength']:
            self.xml_node.set(attr, str(int(getattr(self, attr))))
        return


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
            self.position = Position(x=0, y=0, z=0)

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
    '''
    def __init__(self, xml_node):
        self.xml_node = xml_node
        self.name = xml_node.get('name')
        self.parent_conns = []
        self.conns = {}
        # Generic default radius.
        self.radius = 6000
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

    def Contains_Gate_Or_Highway(self):
        'Dummy function returns False, for easy of use with zones.'
        return False


class Region:
    '''
    Region, read from region_definitions. Note: not a macro.

    * xml_node
      - Region xml node.
    * name
      - String, name of the region.
    * radius
      - Float, radius of this region.
    * does_damage
      - Bool, True if this region does passive damage.
    '''
    def __init__(self, xml_node):
        self.xml_node = xml_node
        self.name = xml_node.get('name')

        # Get an estimate of the radius from the size node.
        boundary_node = xml_node.find('./boundary')
        size_node     = boundary_node.find('./size')
        
        # If there is any damage node, assume the region has a damage field.
        self.does_damage = xml_node.find('.//damage') != None

        # Can come in different shapes, but all have an 'r' radius.
        self.radius = float(size_node.get('r'))

        # -Removed; this spacing is a bit overkill, and may not
        #  really matter (depending on how effect and region radius
        #  is handled, eg. region radius might override this).
        ## If this does damage, the damage radius may be larger than
        ## the basic radius. Bump it up in this case.
        ## (Only comes up with the lightning damage in Lasting Vengeance
        ###  Cluster_35.)
        #if self.does_damage:
        #    effect_node = xml_node.find('./fields/effect')
        #    if effect_node != None:
        #        effect_radius = effect_node.get('maxdistance')
        #        if effect_radius:
        #            effect_radius = float(effect_radius)
        #            if effect_radius > self.radius:
        #                self.radius = effect_radius
        return

    def Scale(self, scaling_factor):
        '''
        Scale the size of this region by the scaling factor.
        Since regions may have issues when shrinking, this will only 
        allow increasing size.
        Should be called before adjusting sector sizing, so it can
        reflect the new size.
        Changes the xml directly.
        '''
        # Skip if wanting to shrink.
        if scaling_factor < 1:
            return

        # Adjust all of the size attributes.
        size_node = xml_node.find('./boundary/size')
        for attr in size_node.keys():
            XML_Modify_Float_Attribute(size_node, attr, scaling_factor, '*')

        # Update the radius.
        self.radius = float(size_node.get('r'))

        # Handle any splines.
        for spline_node in xml_node.xpath('./boundary/splineposition'):
            # Update components.
            for attr in ['x','y','z','tx','ty','tz','inlength','outlength']:
                XML_Modify_Float_Attribute(spline_node, attr, scaling_factor, '*')
        return


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
            max_dist = 5000
        return max_dist

    def Get_Center(self):
        '''
        Returns the center point of this zone, based on connections
        and god objects.
        '''
        # Gather connections and god objects.
        objects = [x for x in self.conns.values()]
        objects += [x for x in self.god_objects if x.position]

        sum_pos = Position(x=0, y=0, z=0)
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

# TODO: maybe make this the primary class, and wrap superhighway endpoints
# and resource regions into here for position transforms.
# Alternatively, do it elsewhere that builds a list of generic objects,
# using info from here and other files.
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
    '''
    def __init__(self, xml_node):
        super().__init__(xml_node)
        self.cluster_connected_macros = []
        self.md_objects = []
        self.god_objects = []
        return

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
    
    def Get_Size(self):
        '''
        Returns approximate sector size, as a diamater.
        '''
        # Similar to sector.coresize property in game.
        # Presumably this is based on the gate distances.
        gate_zones = [x.macro for x in self.conns.values()
                      if x.macro and x.macro.Contains_Gate_Or_Highway()]

        max_dist = 0
        for zone_0, zone_1 in combinations(gate_zones, 2):
            pos_0 = zone_0.Get_Sector_Conn().position
            pos_1 = zone_1.Get_Sector_Conn().position
            this_dist = pos_0.Get_Distance_To(pos_1)
            if this_dist > max_dist:
                max_dist = this_dist

        # If there was just one gate, fall back on checking zone distances.
        # TODO
        # For now, just assume a standard size of 250 km.
        if not max_dist:
            max_dist = 250000
        return max_dist

    def Get_Center(self):
        '''
        Returns the center point of this sector, based on gate zones.
        Update: temporarily just returns 0 for now.
        '''
        gate_zones = [x.macro for x in self.conns.values()
                      if x.macro and x.macro.Contains_Gate_Or_Highway()]

        sum_pos = Position(x=0, y=0, z=0)

        if 0:
            # Note: had trouble with single-gate sectors spawning god stations
            # very far away from the gate. This could be related to the god
            # code assuming sector center is at 0, not at the gate, so in
            # that case just return 0 here as well.
            if len(gate_zones) > 1:
                for zone in gate_zones:
                    # Count sector highways as half, since there are normally
                    # (always) a pair of zones for the entry and exit.
                    if zone.has_sector_highway:
                        sum_pos += (zone.Get_Sector_Conn().position / 2)
                    else:
                        sum_pos += zone.Get_Sector_Conn().position
                sum_pos /= len(gate_zones)
        return sum_pos


class Highway(Macro):
    '''
    Parent class for zone highways and sector highways.

    * spline_positions
      - List of Positions for each spline node; just x,y,z.
    * orig_spline_positions
      - Originals of the above, just for debug viewing.
    '''
    def __init__(self, xml_node):
        super().__init__(xml_node)

        self.spline_positions = []
        self.orig_spline_positions = []
        for spline_node in xml_node.xpath('.//splineposition'):
            # Two unique copies.
            self.spline_positions.append(Spline_Position(spline_node))
            self.orig_spline_positions.append(Spline_Position(spline_node))

        # Note: napleos fortune 2 highway has an end point that is 
        # ~15 Mm past the actual last spline, which throws of logic below
        # that applies offsets to splines by linear interpolation betwee
        # endpoints. In game, the last spline defines that actual end
        # point of the highway.
        # To make the logic work cleanly, fix this bug in the ego code
        # by adjusting the entry/exit positions to match their splines.
        # Note: in testing, this goes wildly wrong, eg. nap fortune 
        # highway becomes only a few km long (vs 1Mm).
        for conn in self.conns.values():
            if conn.ref == 'entrypoint':
                spline_pos = self.spline_positions[0]
            elif conn.ref == 'exitpoint':
                spline_pos = self.spline_positions[-1]
            else:
                raise Exception()
            # Ignore small discrepencies.
            if conn.position.Get_Distance_To(spline_pos) > 100:
                # Make the connection match the spline.
                conn.position.Update(spline_pos)
                # Pretend the original value was the spline value, so
                # offset propagation doesn't get confused.
                conn.orig_position.Update(spline_pos)
        return

    def Update_Splines(self):
        '''
        Adjust splines for tx/ty/tz/inlength/outlength.
        Child classes handle updates of the x/y/z points.
        '''
                
        '''
        The tx,ty,tz values roughly indicate the direction of the highway
        at a given spline node.
        By observation, tx^2 + ty^2 + tz^2 == 1.
        The start/end splines should probably be unmodified, since they
        are set up to point roughly at a gate or similar.
        Intermediate points can be recomputed based on prior and following
        points.
        By observation, existing values appear to match this approach,
        eg. check dx/dy/dz between prior/later points, square them, then
        normalize to get a total == 1.

        The inlength and outlength indicate how long before/after the point
        the highways should flatten out again.
        Around 1/3 the length to the next point should work for
        in/out lengths.
        '''
        for i, this_pos in enumerate(self.spline_positions):

            # Get the nodes on either side.
            prior_pos = self.spline_positions[i-1] if i != 0 else None
            next_pos  = self.spline_positions[i+1] if i+1 != len(self.spline_positions) else None

            # Handle inlength and outlength, as 1/3 the distance to the
            # prior/next nodes.
            # (Endpoints will remain as 0 length.)
            if prior_pos:
                this_pos.inlength = this_pos.Get_Distance_To(prior_pos) / 3
            if next_pos:
                this_pos.outlength = this_pos.Get_Distance_To(next_pos) / 3

            # tx/ty/tz update if prior/next points are both known.
            # If not, base it on the current and next/previous point.
            delta_pos_0 = prior_pos if prior_pos else this_pos
            delta_pos_1 = next_pos  if next_pos else this_pos
            if delta_pos_0 and delta_pos_1:
                # Delta should be negative if next pos is getting more negative.
                dx = delta_pos_1.x - delta_pos_0.x
                dy = delta_pos_1.y - delta_pos_0.y
                dz = delta_pos_1.z - delta_pos_0.z
                # Normalize these so their sum of squares == 1.
                norm_factor = 1 / ((dx**2 + dy**2 + dz**2) ** 0.5)
                # Put back.
                this_pos.tx = dx * norm_factor
                this_pos.ty = dy * norm_factor
                this_pos.tz = dz * norm_factor
        return
    
    def Update_XML(self):
        '''
        Update xml, including adjusting spline positions based on 
        endpoint positions.
        '''
        super().Update_XML()
        for position in self.spline_positions:
            position.Update_XML()
        return


class Zone_Highway(Highway):
    '''
    Information on zone highway.
    
    * is_ring_piece
      - Bool, true if this highway is part of the large multi-sector ring.
    '''
    def __init__(self, xml_node):
        super().__init__(xml_node)
        self.is_ring_piece = xml_node.find('./properties/configuration').get('ring') == '1'
        return

    def Update_Splines(self):
        'Adjust spline positions based on endpoint positions.'
        
        # Ensure the first/last splines still align with the highway entry/exit
        # as expected (where the entry/exit moved with their home zone, but
        # the spline was moved as a separate object that should have been
        # grouped with the zone).
        # If not aligned, the zone may have originally been skewed heavily
        # from the spline position, else might just be a minor discrepency.
        # In either case, force a match.
        for conn in self.conns.values():
            if conn.ref == 'entrypoint':
                spline_pos = self.spline_positions[0]
            elif conn.ref == 'exitpoint':
                spline_pos = self.spline_positions[-1]
                
            # Ignore small discrepencies (mostly to make this easier
            # to debug break and see stuff that matters).
            if conn.position.Get_Distance_To(spline_pos) > 50:
                # If this is part of the highway ring, force the spline to
                # match the connection (which aligns with a gate), else
                # force the connection to match the spline.
                if self.is_ring_piece:
                    spline_pos.position.Update(conn)
                else:
                    conn.position.Update(spline_pos)

        # Use shared code to fix inlength/outlength/tx/ty/tz.
        super().Update_Splines()
        return


class Sector_Highway(Highway):
    '''
    Information on sector highway.
    '''    
    def Update_Splines(self):
        'Adjust spline positions based on endpoint positions.'

        # Each spline is somewhere between the entry and exit points, which
        # may have been offset differently.
        # This will use linear interpolation, eg. the spline will mostly match
        # the offset of its nearest edge, based on spline position.
        # Note: for sector highways, can probably also leave the splines
        # untouched except entry/exit.

        # Look up the original points on either end.
        # Also look at how much they were offset.
        point_offsets = {}
        for conn in self.conns.values():
            point_offsets[conn.orig_position] = conn.position - conn.orig_position
            
        # Go through the splines.
        for i, position in enumerate(self.spline_positions):
        
            # Get ratios based on how close to either side, and
            # pick up that much of their offsets.
            # Note: the first and last splines should match exactly with
            # an entry/exit point (maybe with some float error).
            distances = {x : position.Get_Distance_To(x)
                        for x in point_offsets.keys()}
            total_distance = sum(distances.values())
            ratios = {k : 1 - v / total_distance for k,v in distances.items()}
            offsets = [point_offsets[k] * ratios[k] for k in point_offsets]
            offset = offsets[0] + offsets[1]
        
            # Apply the offset back to the position.
            position += offset
            self.spline_positions[i] = position
        
        # Use shared code to fix inlength/outlength/tx/ty/tz.
        super().Update_Splines()
        return
    

class MD_Object:
    '''
    Parent class for generic MD created objects, with a sector and position.
    Each particular object is expected to have its own unique xml to deal
    with.

    * name
      - String, name of this object (may be descriptive).
    * xml_node
      - MD script root node for this object.
    * sector_name
      - Name of the sector macro.
    * sector
      - Sector with this object.
    * position
      - Position of this object.
    * radius
      - Explicit radius of this object.
      - Defaults to be similar to a zone, eg. 5km.
    '''
    def __init__(
            self, 
            xml_node
            ):
        self.name = None
        self.xml_node = xml_node
        self.sector_name = None
        self.sector = None
        self.position = None
        self.radius = 5000
        return

    def Set_Sector(self, sector):
        'Fill the Sector holding this object.'
        self.sector = sector
        sector.md_objects.append(self)
        return

    def Update_XML(self):
        raise NotImplementedError()


class MD_Headquarters(MD_Object):
    '''
    Player headquarters.

    * hq_sector_node
    * hq_pos_node
    '''
    def __init__(self, xml_node):
        super().__init__(xml_node)
        self.name = 'headquarters'

        # Bump up the radius a bunch.
        # 20k should be good enough, maybe.
        self.radius = 20000
    
        # Look up the commands that pick the sector and pos.
        hq_sector_node = xml_node.find('./cues/cue/actions/find_sector[@name="$HQSector"]')
        hq_pos_node    = xml_node.find('./cues/cue/actions/set_value[@name="$HQPosition"]')
        self.hq_sector_node = hq_sector_node
        self.hq_pos_node = hq_pos_node

        # Macro has the form: macro="macro.cluster_01_sector001_macro"
        self.sector_name = hq_sector_node.get('macro').replace('macro.','')

        # Position has the form: exact="position.[128km, 0m, 198km]"
        pos_string = hq_pos_node.get('exact').replace('position.','').replace('[','').replace(']','')
        dim_strings = [x.strip() for x in pos_string.split(',')]
        dims = {}
        for i, attr in enumerate(['x','y','z']):
            dim_str = dim_strings[i]

            if dim_str.endswith('km'):
                value = float(dim_str.replace('km','')) * 1000
            elif dim_str.endswith('m'):
                value = float(dim_str.replace('m',''))
            else:
                raise Exception()
            dims[attr] = value
        self.position = Position(**dims)
        return

    def Update_XML(self):
        # Sector will be the same; just update position.
        dims = [self.position.x, self.position.y, self.position.z]
        dim_strs = []
        for dim in dims:
            dim_strs.append(str(int(dim / 1000)))
        pos_string = 'position.[{}km, {}km, {}km]'.format(*dim_strs)

        self.hq_pos_node.set('exact', pos_string)
        return


class God_Object:
    '''
    Object defined in god.xml.
    
    * name
      - String, name of this object.
    * xml_node
      - God xml object node for this object.
    * macro_name
      - Name of the sector or zone macro.
    * sector
      - Sector with this object.
    * zone
      - Zone with this object, if specific to a zone.
    * position
      - Position of this object.
    * radius
      - Explicit radius of this object.
      - Defaults to be similar to a zone, eg. 5km.
    '''
    def __init__(
            self, 
            xml_node
            ):
        self.xml_node = xml_node

        self.name = xml_node.get('id')
        self.macro_name = xml_node.find('./location').get('macro')
        self.sector = None
        self.zone   = None

        # Some of these don't have specific positions, but are randomly
        # placed based on sector size (which should update automatically
        # after sector scaling).
        pos_node = xml_node.find('./position')
        if pos_node != None:
            self.position = Position(pos_node)
        else:
            # Do not give a default 0 position for now; assume its random.
            self.position = None

        # Radius is unclear; can vary by object.
        # For now, give a decent padding, but many of these are stations.
        self.radius = 5000
        return

    def Set_Macro(self, macro):
        'Fill the Sector or Zone macro holding this object.'

        if isinstance(macro, Sector):
            self.sector = macro
            macro.god_objects.append(self)

        elif isinstance(macro, Zone):
            self.zone = macro
            macro.god_objects.append(self)
            # It's radius will change; update it since it is cached.
            # TODO: maybe avoid caching this.
            macro.Update_Radius()
        else:
            raise Exception()
        return

    def Update_XML(self):
        if self.position:
            self.position.Update_XML()
            

class Galaxy:
    '''
    Primary class for holding galaxy/sector/zone/etc. information parsed
    from xml files, and providing transform methods.

    * gamefile_roots
      - Dict matching Game_Files to their xml root nodes (to be edited).
    * class_macros
      - Dict, keyed by macro class (eg. 'sector'), holding a subdict of
        macros keyed by name.
    * macros
      - Dict of all macros, keyed by name, collected from the above.
      - Includes lowercase versions of keys, eg. each object is present
        up to twice.
    * regions
      - Dict of all regions, keyed by name, collection from region_definitions.
    * md_objects
      - List of MD created objects.
    * god_objects
      - List of god created objects.
    '''
    def __init__(self, gamefile_roots):
        self.gamefile_roots = gamefile_roots
        self.macros = {}
        self.class_macros = defaultdict(dict)
        self.regions = {}
        self.md_objects = []
        self.god_objects = []
        
        # Read the various macros from the xml files.
        for field_name, macro_name, base_class in [
                ('zones', 'zone', Zone),
                ('zone_highways', 'highway', Zone_Highway),
                ('sec_highways', 'highway', Sector_Highway),
                ('sectors', 'sector', Sector),
                ('clusters', 'cluster', Cluster),
            ]:
            for _, xml_root in gamefile_roots[field_name]:
                for macro in xml_root.xpath(".//macro[@class='{}']".format(macro_name)):
                    object = base_class(macro)

                    self.class_macros[field_name][object.name] = object
                    self.macros[object.name] = object

                    # Lookup are not case sensetive; as a quick workaround,
                    # keep a lowercased key in general macros.
                    # (Don't do this for class_macros, since that is often
                    # use in loops and would otherwise repeat entries.)
                    self.macros[object.name.lower()] = object


        # For every connection, find its macro link.
        for subdict in self.class_macros.values():
            for macro in subdict.values():
                for connection in macro.conns.values():
                    if connection.macro_ref:
                        macro = self.macros.get(connection.macro_ref)
                        # Note: may go unfound if referring to outside assets.
                        if macro:
                            connection.Set_Macro(macro)
                            

        # Load region definitions.
        # Note: these aren't macros/connections/etc., just plain region nodes.
        for region_node in gamefile_roots['region_defs'][0][1].xpath('./region'):
            region = Region(region_node)
            self.regions[region.name] = region
                
        # For every region macro (defined in clusters), link its region.
        for cluster in self.class_macros['clusters'].values():
            for conn in cluster.conns.values():
                if not isinstance(conn.macro, Region_Macro):
                    continue
                region_macro = conn.macro
                region_name = region_macro.xml_node.find('./properties/region').get('ref')
                region_macro.Set_Region(self.regions[region_name])


        # In the case of sector highways:
        # - Cluster connects to sechighway.
        #   - This then sub-connects entrypoint and exitpoint to zones.
        # To simplify later effort, parse those nested connections here.
        # The goal is to annotate the Sector_Highway connections with
        #  their final zones (will always be 1:1).
        for cluster in self.class_macros['clusters'].values():

            for conn in cluster.conns.values():
                if not isinstance(conn.macro, Sector_Highway):
                    continue
                sec_highway = conn.macro

                # Search the connection macro node's nested connections.
                for nested_conn in conn.xml_node.xpath('./macro/connections/connection'):

                    # 'ref' is exitpoint or entrypoint.
                    # Find the matching connection in the sec highway.
                    highway_link_conn = sec_highway.conns[(None, nested_conn.get('ref'))]

                    # Look up the zone macro.
                    zone = self.class_macros['zones'][nested_conn.find('./macro').get('ref')]

                    # Link them up.
                    highway_link_conn.Set_Macro(zone)
                    # Flag the zone as having a highway link.
                    zone.has_sector_highway = True


        # Similar logic applies to zone highways.
        # - Sector connects to zone highway
        #   - This then subconnects to zones.
        for sector in self.class_macros['sectors'].values():

            for conn in sector.conns.values():
                if not isinstance(conn.macro, Zone_Highway):
                    continue
                zone_highway = conn.macro

                # Search the connection macro node's nested connections.
                for nested_conn in conn.xml_node.xpath('./macro/connections/connection'):

                    # 'ref' is exitpoint or entrypoint.
                    # Find the matching connection in the highway.
                    highway_link_conn = zone_highway.conns[(None, nested_conn.get('ref'))]

                    # Look up the zone macro.
                    # 'path' has some prefixed '../'s and then the name of the
                    # zone connection in the sector file.
                    zone_conn_name = nested_conn.find('./macro').get('path').replace('../','')
                    zone_conn = sector.conns[(zone_conn_name, 'zones')]
                    zone = zone_conn.macro
                    assert isinstance(zone, Zone)

                    # Link them up.
                    highway_link_conn.Set_Macro(zone)
                    # Flag the zone as having a highway link.
                    zone.has_zone_highway = True


        # Clusters define resource regions, which are placed to end up
        # somewhere in a sector.
        # For this transform, want to know which sector each region
        # corresponds to.
        for cluster in self.class_macros['clusters'].values():

            # Gather the sector connections.
            sector_conns = [x for x in cluster.conns.values()
                            if isinstance(x.macro, Sector)]

            for conn in cluster.conns.values():
                if not isinstance(conn.macro, Region_Macro):
                    continue
                region_macro = conn.macro

                # Based on this position in the cluster, find the closest
                # sector it could match to.
                closest_sector   = sector_conns[0].macro
                closest_distance = sector_conns[0].position.Get_Distance_To(conn.position)
                if len(sector_conns) > 1:
                    for sector_conn in sector_conns[1:]:
                        this_dist = sector_conn.position.Get_Distance_To(conn.position)
                        if this_dist < closest_distance:
                            closest_distance = this_dist
                            closest_sector   = sector_conn.macro

                # Annotate the region with this sector.
                region_macro.Set_Sector(closest_sector)


        # The player hq is fairly important, so treat it as a special
        # object.
        self.md_objects.append(MD_Headquarters(gamefile_roots['md_hq'][0][1]))

        # Link md objects to their sectors.
        for md_object in self.md_objects:
            # Note: md names are not case sensetive.
            sector = self.macros[md_object.sector_name]
            md_object.Set_Sector(sector)


        # Read in god placed objects.
        for object_node in gamefile_roots['god'][0][1].xpath('./objects/object'):
            self.god_objects.append(God_Object(object_node))

        # Read in god placed stations.
        # (Most of these are in zones with no position, but some have pos.)
        # This is where the scientific start hq pos is located.
        for object_node in gamefile_roots['god'][0][1].xpath('./stations/station'):
            self.god_objects.append(God_Object(object_node))
            
        # Link god objects to their sectors or zones.
        for god_object in self.god_objects:
            # Note: md names are not case sensetive.
            # Note: during testing, dlc god objects may show up when those
            # sectors are skipped, so try to fail safe in that case.
            macro = self.macros.get(god_object.macro_name)
            if macro:
                god_object.Set_Macro(macro)
            else:
                god_object.position = None

        return


    def Update_XML(self):
        '''
        Update the xml nodes to reflect the current positions.
        '''
        for subdict in self.class_macros.values():
            for macro in subdict.values():
                macro.Update_XML()
        for md_object in self.md_objects:
            md_object.Update_XML()
        for god_object in self.god_objects:
            god_object.Update_XML()
        return



class Object:
    '''
    Object to be moved around in the sector.

    * cluster_pos
      - Position in the cluster, if relevant.
      - Used for objects that originate from the cluster level.
    * sector_pos
      - Position in the sector.
      - This will have an xml_node for objects that originate in the sector,
        else should have a cluster_pos.
    * type
      - Type of the object.
    * name
      - Name of the object's macro
    * connection
      - Primary connection node that defined this object in the sector/cluster.
      - May be None for other objects, like MD created ones.
    * md_object
      - MD_Object, if this is an object defined by md.
    * god_object
      - God_Object, if this is an object defined by god.
    * spline_pos
      - Spline_Position, if this is a highway spline psuedo-object.
    * radius
      - Float, radius of this object, inside which other objects should not
        be allowed (unless they start inside).
    * contains_gate_or_highway
      - Flag, True if the object is a zone with a gate or highway entry/exit.
    '''
    def __init__(self, name, type, connection = None, 
                 cluster_pos = None, sector_pos = None, md_object = None,
                 god_object = None, spline_pos = None):
        self.name = name
        self.type = type
        self.connection = connection
        self.md_object = md_object
        self.god_object = god_object
        self.cluster_pos = cluster_pos
        self.spline_pos = spline_pos
        self.sector_pos = sector_pos
        self.contains_gate_or_highway = False        

        # Default radius to that of zones, splines, misc.
        # Zones are 10km apart in vanilla, which can be considered 5km radius
        # on each. Add a little extra safety.
        self.radius = 5000 + 1000

        if spline_pos:
            # Note: splines that should be roughly paired are observed to
            # be ~10 km apart, so add some extra radius here to encourage
            # the splines to group up and move together.
            self.radius += 1000

        elif connection:
            # Start with the macro's radius.
            self.radius = connection.macro.radius

            # Zones with gates will be given some extra spacing, so ships can
            # fly around them and such.
            # This will be finetuned later to avoid gate-to-gate distances
            # getting too short.
            if isinstance(connection.macro, Zone):
                zone = connection.macro
                if zone.Contains_Gate_Or_Highway():
                    self.contains_gate_or_highway = True
                    # Some extra spacing.
                    self.radius += 5000

        # MD objects annotate their radius.
        elif md_object:
            self.radius = md_object.radius
            
        elif god_object:
            self.radius = god_object.radius

        return


class Object_Group:
    '''
    Groups of objects to reposition.
    Initially there will be 1 object per group; over time groups will
    merge together as they get too close.

    * objects
      - List of objects in this group.
    * sector_pos
      - Position of the weighted center of this group in the sector.
      - Objects closer to the sector center are weighted more heavily.
    * has_regions
      - Any object in the group is a region.
    * has_damage_regions
      - Any object in the group is a damaging region.
    * has_non_regions
      - Any object in the group is a non-region.
    '''
    def __init__(self, objects):
        self.objects = objects

        self.has_regions = any(x.type == Region_Macro for x in objects)
        self.has_damage_regions = any(x.type == Region_Macro 
                               and x.connection.macro.region.does_damage 
                               for x in objects)
        self.has_non_regions = any(x.type != Region_Macro for x in objects)

        # Compute average sector position.
        # Note: if a highway splines are in this group, they should control
        # the average position, to better maintain the shape of highways.
        # Note: for trinity sanctum 3, there is a misc highway that does
        # a half circle, which tends to get grouped with and throw off the
        # main ring highways. As such, this will favor ring highway splines,
        # then general highways, then everything.
        ring_splines = [x for x in objects if x.spline_pos and x.connection.macro.is_ring_piece]
        splines = [x for x in objects if x.spline_pos]
        if ring_splines:
            centering_objects = ring_splines
        elif splines:
            centering_objects = splines
        else:
            centering_objects = objects

        # This can have a problem if a distant region (large radius) gets
        # added into a group and heavily skew the average. To counteract
        # that, the average will be weighted by 1/distance from center.
        sector_pos = Position(x=0, y=0, z=0)
        weights = 0
        for object in centering_objects:
            if object.connection and object.connection.macro_ref == 'Zone001_Cluster_47_Sector001_macro':
                bla = 0
            weight = 1 / (object.sector_pos.Get_Distance() + 1)
            sector_pos += object.sector_pos * weight
            weights += weight
        self.sector_pos = sector_pos / weights

        return


    def Scale_Pos(self, scaling):
        '''
        Adjust the pos of this group to be multiplied by scaling.
        All internal objects will get the same fixed offset.
        '''
        orig_pos = self.sector_pos
        new_pos  = self.sector_pos * scaling
        offset   = new_pos - orig_pos

        # -Removed; get more predictable scaling if offset isn't artifically
        #  limited. (Changed to keep highway shape better.)
        ## Generally want to avoid the offset causing any given object to
        ## move further away from the center, in any dimension, to avoid
        ## possible oddities (note: idea not strongly formed).
        ## As such, adjust the offset attributes to limit them.
        #for attr in ['x','y','z']:
        #    this_offset = getattr(offset, attr)
        #
        #    for object in self.objects:
        #        if object.connection and object.connection.macro_ref == 'Zone001_Cluster_47_Sector001_macro':
        #            bla = 0
        #        this_point = getattr(object.sector_pos, attr)
        #        next_point = this_point + this_offset
        #        
        #        # Limit the offset to not move the point past 0.
        #        if this_point >= 0:
        #            # Prevent offset being too negative.
        #            this_offset = max(this_offset, 0 - this_point)
        #            # Ensure it is not over 0.
        #            this_offset = min(this_offset, 0)
        #        else:
        #            # As above, but reversed due to signage.
        #            this_offset = min(this_offset, 0 - this_point)
        #            this_offset = max(this_offset, 0)
        #
        #    # Update with the adjusted offset.
        #    setattr(offset, attr, this_offset)

        # Now apply the adjusted offset to the objects.
        for object in self.objects:
            object.sector_pos += offset

        # The average should be adjusted by the same amount, since all
        # objects adjusted the same (regardless of weighting).
        self.sector_pos += offset
        return
    
    def Should_Merge_With(self, other, sector_size):
        '''
        Returns True if this group should merge with the other group based
        on internal objects between groups getting too close.
        '''
        # Disallow merging regions and non-regions, since that is overly
        # restrictive.  (Eg. zones can go inside asteroid fields.)
        # However, if the region does damage, allow merging, so try to keep
        # zones from being moved inside the damage.
        if not self.has_damage_regions and not other.has_damage_regions:
            if((self.has_regions and not other.has_regions)
            or (not self.has_regions and other.has_regions)):
                return False        

        # Check all object combos between groups.
        for object_1 in self.objects:
            for object_2 in other.objects:

                # Determine allowed distance.
                # Prevent the radiuses from touching.
                allowed_dist = object_1.radius + object_2.radius

                # If both objects are zones with gates, limit their proximity
                # to roughly a fraction of the desired sector size.
                # To be safe, add this to the radiuses, since the gates in
                # the zones may be placed near to each other's zone.
                if object_1.contains_gate_or_highway and object_2.contains_gate_or_highway:
                    allowed_dist += sector_size / 2

                # Check proximity.
                if object_1.sector_pos.Is_Within_Distance(object_2.sector_pos, allowed_dist):
                    return True
        return False


def Scale_Regions(galaxy, scaling_factor, debug):
    '''
    Scale all regions up if scaling_factor is positive, else do nothing.
    '''
    for region in galaxy.class_macros['regions'].values():
        region.Scale(scaling_factor)
    return

    
def Scale_Sectors(galaxy, scaling_factor, debug):
    '''
    Scale all sectors to roughly match the scaling factor.
    '''
    # Apply to all sectors individually.
    for sector in galaxy.class_macros['sectors'].values():
        # Testing, pick a sector.
        #if sector.name != 'Cluster_18_Sector001_macro':
        #    continue
        Scale_Sector(galaxy, sector, scaling_factor, debug)
        # In testing, skip after first sector.
        #break


    # Clean up sector highways.
    '''
    For these, there is an endpoint connection in the sector that was
    adjusted, as well as a redundant cluster-level sechighway with
    endpoint offsets from the center (located somewhere between the
    sectors it connects).
    Need to adjust the endpoint offsets of the cluster-level so that
    the final point matches what is in the sector.

    Note:
    - Sector highway links to a zone macro (one for each end).
    - Sector connects to the same zone macro.
    - Need to look up the sector connection for its position, get offset,
      then apply that to the sector highway endpoint connection.
    '''
    for sec_highway in galaxy.class_macros['sec_highways'].values():
        # Work through each connection, entry and exit.
        for connection in sec_highway.conns.values():

            # Find the zone it links to.
            zone = connection.macro
            assert isinstance(zone, Zone)

            # From the zone, get the parent connection for its originating
            # sector.  (Don't need the sector itself.)
            sector_zone_conn = zone.Get_Sector_Conn()

            # Determine the offset that was applied to the zone.
            offset = sector_zone_conn.Get_Offset()

            # Apply this offset to the sechighway endpoint.
            connection.position += offset
            
        # Call some method that adjusts splinepositions based on
        # how the endpoints moved.
        sec_highway.Update_Splines()


    # Clean up zone highways.
    '''
    Somewhat similarly, zone highways have their endpoints defined in Zones
    that were moved.  The overall highway has redundant positioning, with
    a center point in the sector and offsets to its entry/exit points.
    Need to adjust the highway entry/exit to match the zone.
    '''
    for zone_highway in galaxy.class_macros['zone_highways'].values():
        # Note: some zone highways have their sector connections
        # commented out or removed. Skip those.
        if not zone_highway.parent_conns:
            continue

        # Get the pos of this highway center point in the sector.
        assert len(zone_highway.parent_conns) == 1
        highway_pos = zone_highway.parent_conns[0].position

        # Work through each connection, entry and exit.
        for connection in zone_highway.conns.values():

            if connection.macro.name == 'Zone020_Cluster_04_Sector001_macro':
                bla = 0

            # Compute the total sector position.
            sector_pos = highway_pos + connection.position

            # Find the zone it links to.
            zone = connection.macro
            assert isinstance(zone, Zone)

            # From the zone, get the parent connection for its originating
            # sector.  (Don't need the sector itself.)
            sector_zone_conn = zone.Get_Sector_Conn()

            # Determine the offset that was applied to the zone.
            offset = sector_zone_conn.Get_Offset()

            # Apply this offset to the highway endpoint.
            connection.position += offset
            
        # Call some method that adjusts splinepositions based on
        # how the endpoints moved.
        zone_highway.Update_Splines()

    return


def Scale_Sector(galaxy, sector, scaling_factor, debug):
    '''
    Scale a single sector to roughly match the scaling factor.
    '''
    # Basic idea:
    # - Collect all objects associated with the sector that will be moved,
    # eg. zones, resource patches, highways, etc.
    # - Pack these into a standardize class object that includes a sector
    # position.
    # - Establish rules on how close objects of various types can be
    # to each other.
    # - Shift objects progressively together in a series of small steps.
    # - When objects reach a min distance to each other, merge them into
    # a grouped object that can itself be moved further.
    # - When done, unpeel the grouped objects to determine their final
    # positions, then push those positions back to the original objects
    # in some way (eg. cluster-level objects will need to know their
    # final cluster-level position).

    # Collect objects.
    objects = []
    
    if sector.parent_conns[0].parent_macro.name == 'Cluster_47_macro':
        bla = 0

    # Collect connections in the sector (mostly zones).
    for name, conn in sector.conns.items():

        # Zone highways are a little tricky.
        # The entry/exit points are associated with specific zones, and will
        # be moved naturally later (when zone connection offsets are
        # back-applied to the entry/exit). However, the spline positions
        # are not otherwise represented.
        # The approach here will treat splines as their own objects to be
        # moved around.
        if isinstance(conn.macro, Zone_Highway):
            for i, spline_pos in enumerate(conn.macro.spline_positions):
                # The spline position is relative to the zone center
                # in the sector.
                sector_pos = conn.position + spline_pos
                objects.append( Object(
                    sector_pos = sector_pos,
                    name = conn.name + 'spline[{}]'.format(i),
                    connection = conn,
                    spline_pos = spline_pos,
                    type = type(conn.macro),
                    ))
        else:
            # If this is a zone, adjust its sector position to re-center it
            # to be in the middle of the zone objects.
            if isinstance(conn.macro, Zone):
                # Eg. if zone is at x=5 in sector, but internally objects
                # are skewed x=6 further, then this will return x=11 in sector.
                sector_pos = conn.position + conn.macro.Get_Center()
            else:
                sector_pos = conn.position
            objects.append( Object(
                sector_pos = sector_pos,
                name = conn.name,
                connection = conn,
                type = type(conn.macro),
                ))
            
    # Look up the position of this sector in its cluster.
    assert len(sector.parent_conns) == 1
    sector_in_cluster_pos = sector.parent_conns[0].position

    # Collect cluster objects that align with this sector.
    for macro in sector.cluster_connected_macros:

        # Explicitly reject audio regions, else they end up clustering
        # with everything and preventing movement. Also, they have no
        # physical objects to care about.
        if 'audio' in macro.region.name:
            continue

        # These cases have only a cluster position normally, and need
        # a sector position generated.
        cluster_pos = macro.parent_conns[0].position
        # If the cluster object is at x=6, and sector is at x=7, then
        # the cluster object is at x=-1 in sector.
        sector_pos = cluster_pos - sector_in_cluster_pos

        objects.append( Object(
            cluster_pos = cluster_pos,
            sector_pos = sector_pos,
            name = macro.name,
            connection = macro.parent_conns[0],
            type = type(macro),
            ))


    # Collect md objects.
    for md_object in sector.md_objects:
        
        objects.append( Object(
            sector_pos = md_object.position,
            name = md_object.name,
            md_object = md_object,
            type = type(md_object),
            ))

    # Collect god objects.
    for god_object in sector.god_objects:
        
        # Skip those without positions.
        if god_object.position:
            objects.append( Object(
                sector_pos = god_object.position,
                name = god_object.name,
                god_object = god_object,
                type = type(god_object),
                ))


    # Calculate the sector center (may be offset from 0).
    sector_center = sector.Get_Center()

    # For simplicity, start by adjusting all objects to be centered around 0.
    # (This is undone later.)
    for object in objects:
        # Eg. if object is at x=10, center is x=4, then new object pos is x=6.
        object.sector_pos -= sector_center        

    # Determine the sector size limit, based on gate distances.
    # This is used to prevent gates from getting too close, if they
    # weren't already closer.
    sector_size = sector.Get_Size()
    target_sector_size = sector_size * scaling_factor


    # Debug printout.
    if debug:
        lines = [
            '',
            'Sector  : {}'.format(sector.name),
            ' center : {}'.format(sector_center),
            ' size   : {}'.format(sector.Get_Size()),
            ' target : {}'.format(target_sector_size),
            ' initial objects (centered): ',
            ]
        for object in objects:
            lines.append('  {} : {}'.format(object.name, object.sector_pos))
        Plugin_Log.Print('\n'.join(lines))

    
    # Put all objects into groups, starting with one per group.
    # Do this after sector center adjustment, to avoid the group
    # sector_pos being off.
    object_groups = [Object_Group([x]) for x in objects]

    # TODO: any special case forced groupings.
    # - Spline endpoints with their highway entry/exit zones (maybe handled by radius).
    # - Hazard regions with objects inside them.
    # - Superhighway entry/exit pairs (probably handled by radius).


    # Do a series of progressive steppings toward the scaling_factor.
    # When reducing size, assuming further object is 400 km out, and
    # the scaling is 0.25, it will move 300 km, so steppings of 1/300
    # would move only 1 km per step in this case.
    # Alternatively, can to a series of multipliers, whose total reaches
    # the scaling_factor.
    # step_scale ^ num_steps = scaling
    # step_scale = scaling ^ (1 / num_steps)
    # Note: 100 steps is a little slow to run in debug mode; try something
    # smaller during testing.
    num_steps = 10
    step_scaling = scaling_factor ** (1 / num_steps)

    if sector.parent_conns[0].parent_macro.name == 'Cluster_47_macro':
        bla = 0
        
    # Tinity sanctum 3, highways overlapping.
    if sector.name == 'Cluster_18_Sector001_macro':
        bla = 0

    for step in range(num_steps):
        # Start by looking for groups that can/should be merged (since this
        # may occur on the first iteration for objects that are already
        # at or below the min allowed distance).
        
        if debug:
            Plugin_Log.Print('Starting step {} of {}'.format(step+1, num_steps))

        if step == 9 and sector.parent_conns[0].parent_macro.name == 'Cluster_47_macro':
            bla = 0

        # Each loop may do a merge of two groups, but to allow chain merging,
        # the loops will keep checking until no changes occur.
        groups_to_check = [x for x in object_groups]
        while groups_to_check:
            this_group = groups_to_check.pop(0)

            # Check against all existing groups.
            for other_group in object_groups:
                # Skip self.
                if this_group is other_group:
                    continue
                # Are they close enough that they should merge?
                if this_group.Should_Merge_With(other_group, target_sector_size):
                    
                    # Prune both original groups out.
                    object_groups.remove(this_group)
                    object_groups.remove(other_group)
                    if other_group in groups_to_check:
                        groups_to_check.remove(other_group)

                    # Add in the merged group.
                    new_group = Object_Group(
                        objects = this_group.objects + other_group.objects)
                    object_groups.append(new_group)
                    # Set the new_group to be checked.
                    groups_to_check.append(new_group)
                    
                    if debug:
                        lines = ['', 'merging: ']
                        for object in this_group.objects:
                            lines.append('  {} : {}'.format(object.name, object.sector_pos))
                        lines.append('with:')
                        for object in other_group.objects:
                            lines.append('  {} : {}'.format(object.name, object.sector_pos))
                        lines.append('center: {}'.format(new_group.sector_pos))
                        lines.append('')
                        Plugin_Log.Print('\n'.join(lines))
                    break
                
        if step == 0 and sector.name == 'Cluster_18_Sector001_macro':
            bla = 0

        # Increment everything to be closer (apply change).
        for group in object_groups:
            group.Scale_Pos(step_scaling)
            
    # Trinity sanctum vii, paranid start location.
    if sector.parent_conns[0].parent_macro.name == 'Cluster_47_macro':
        bla = 0            

    # Sacred relic. Stations spaced out, but no clear cause.
    if sector.parent_conns[0].parent_macro.name == 'Cluster_23_macro':
        bla = 0

    # Nap fortune 2; looking at highway.
    if sector.name == 'Cluster_04_Sector001_macro':
        bla = 0

    # Tinity sanctum 3, highways overlapping.
    if sector.name == 'Cluster_18_Sector001_macro':
        bla = 0
        
    if debug:
        lines = [
            '',
            ' final objects (before decentering): ',
            ]
        for object in objects:
            lines.append('  {} : {}'.format(object.name, object.sector_pos))
        Plugin_Log.Print('\n'.join(lines))


    # De-center the objects.
    for object in objects:
        # Put the sector center offset back.
        object.sector_pos += sector_center

        # Put the zone offset back.
        if object.connection and isinstance(object.connection.macro, Zone):
            object.sector_pos -= object.connection.macro.Get_Center()


    # Push the new sector positions back to the original zones/etc.
    for object in objects:
        # Adjust cluster-level objects.
        if object.cluster_pos:
            # Recompute the original position in the sector.
            orig_sector_pos = object.cluster_pos - sector_in_cluster_pos
            # Get the offset.
            offset = object.sector_pos - orig_sector_pos
            # Apply this back to the cluster position.
            object.connection.position += offset
            
        # Adjust highway splines back to their highway offset position.
        elif object.spline_pos:
            # The connection is the highway center point.
            # Subtract it off to get the spline offset.
            object.spline_pos.Update(object.sector_pos - object.connection.position)

        # Record md object movements.
        elif object.md_object:
            md_object.position = object.sector_pos
            
        # Record god object movements.
        elif object.god_object:
            god_object.position = object.sector_pos

            
        # Everything else should be sector-level connections.
        elif object.connection and object.connection.parent_macro is sector:
            object.connection.position.Update(object.sector_pos)

        # Shouldn't be here.
        else:
            raise Exception()
        
    if debug:
        final_size = sector.Get_Size()
        lines = [
            '',
            'final size: {:.0f}'.format(final_size),
            'reduction : {:.0f}%'.format((1 - final_size / sector_size)*100),
            ]
        Plugin_Log.Print('\n'.join(lines))

    return


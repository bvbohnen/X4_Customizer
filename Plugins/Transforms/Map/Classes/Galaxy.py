
from collections import defaultdict
from lxml import etree
from lxml.etree import Element

from ...Classes import *
from .Region import *
from .Macros import *
from .Highways import *
from .Misc import *

__all__ = ['Galaxy']

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
      - List of god created objects, excepting the station defaults.
    * god_default_obj
      - God object that represents station defaults, and is not fully detailed.
    * recenter_sectors
      - Bool, True if edits to sectors should recenter their objects.
    * randomize_new_zones
      - Bool, True if new zone placements should be fully randomized, eg.
        not seeded with the sector name.
    * new_zones
      - List of Zones that have been freshly created, and are pending insertion
        into the xml files.
      - These are also present in the macros.
    '''
    def __init__(self, gamefile_roots, recenter_sectors = False, randomize_new_zones = False):
        self.gamefile_roots = gamefile_roots
        self.macros = {}
        self.class_macros = defaultdict(dict)
        self.regions = {}
        self.md_objects = []
        self.god_objects = []
        self.new_zones = []
        self.recenter_sectors = recenter_sectors
        self.randomize_new_zones = randomize_new_zones

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
                # Record it with other macros, for the Update_XML call later.
                self.class_macros['region_macro'][region_macro.name] = region_macro


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


        # Read in god placed objects and stations.
        # (Don't worry about tutorial stations.)
        # Most stations are in zones with no position, but some have pos.
        # This is where the scientific start hq pos is located.
        for xpath in ['./objects/object', './stations/station', './stations/defaults']:
            for object_node in gamefile_roots['god'][0][1].xpath(xpath):
                object = God_Object(object_node)
                if xpath == './stations/defaults':
                    self.god_default_obj = object
                else:
                    self.god_objects.append(object)

            
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

    

    def Create_Zone(self, sector):
        '''
        Creates a new, empty zone in the given sector, placed at 0,0,0.
        Returns the Zone object.
        '''
        assert isinstance(sector, Sector)

        # Pick a name for this zone.
        # Standard conversion is:
        #  Zone<3-digit #>_<sector macro name>
        # Tweak this with an extra term, eg. 'x4c'.

        # The zone name should be unique.
        zone_number = 0
        while 1:
            macro_name = 'Zone{:03}_x4c_{}'.format(
                zone_number,
                sector.name,
                )
            # Name the connection similarly, swaping the 'macro' suffix
            # for 'connection'.
            conn_name = macro_name.replace('macro', 'connection')

            # Check if the connection name is unique and the
            # zone name is unique.
            if macro_name not in self.macros and conn_name not in sector.conns:
                break
            zone_number += 1


        # Macro for the zones file.
        # Example:
        #<macro name="Zone002_Cluster_46_Sector001_macro" class="zone">
        #  <component ref="standardzone" />
        #</macro>
        zone = Zone( etree.fromstring('''
            <macro name="MACRO" class="zone">
              <component ref="standardzone" />
            </macro>
            '''.replace('MACRO', macro_name)))

        # Record it.  Multiple times due to how things are tracked.
        self.class_macros['zones'][zone.name] = zone
        self.macros[zone.name] = zone
        self.new_zones.append(zone)


        # Connection node for the sector.
        # Example:
        #<connection name="Zone002_Cluster_46_Sector001_connection" ref="zones">
        #  <offset>
        #    <position x="134486.6875" y="0" z="-81845.625" />
        #  </offset>
        #  <macro ref="Zone002_Cluster_46_Sector001_macro" connection="sector" />
        #</connection>
        conn = Connection(
            parent = sector,
            xml_node = etree.fromstring('''
            <connection name="CONN" ref="zones">
              <offset>
                <position x="0" y="0" z="0" />
              </offset>
              <macro ref="MACRO" connection="sector" />
            </connection>
            '''.replace('CONN', conn_name).replace('MACRO', macro_name)))

        assert conn.name not in sector.conns
        sector.conns[conn.name] = conn
        # Hook up to the macro it points at.
        conn.Set_Macro(zone)

        return zone


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
        self.god_default_obj.Update_XML()

        # All new zones need to be inserted into the xml.
        while self.new_zones:
            # Pop it off; treat as not a new zone once the xml is inserted.
            zone = self.new_zones.pop(0)

            # Exctract connection and sector.
            assert len(zone.parent_conns) == 1
            conn = zone.parent_conns[0]
            sector = conn.parent

            # Connection adds to the sector node connections element.
            sector_conns_node = sector.xml_node.find('./connections')
            sector_conns_node.append(conn.xml_node)

            # Zone adds to the Zones file directly.
            # It probably doesn't matter if a zone for a dlc sector is
            # added to the base zones file, so just put wherever for now.
            for game_file, xml_root in self.gamefile_roots['zones']:
                if game_file.virtual_path == 'maps/xu_ep2_universe/zones.xml':
                    break
            xml_root.append(zone.xml_node)

        return


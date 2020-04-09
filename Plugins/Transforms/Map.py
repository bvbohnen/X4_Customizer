'''
Transforms to the map.
'''
from fnmatch import fnmatch
from collections import defaultdict
from Framework import Transform_Wrapper, Load_File, Load_Files
from .Support import XML_Modify_Int_Attribute
from .Support import XML_Modify_Float_Attribute

@Transform_Wrapper()
def Scale_Sector_Size(
        scaling_factor
    ):
    '''
    Change the size of the maps by moving contents (zones, etc.) closer
    together or futher apart. Note: this will require a new game to
    take effect, as positions become part of a save file.

    * scaling_factor
      - Float, how much to adjust distances by.
    '''
    
    # Use a pattern to pick up the base and dlc sectors.
    # Store the game_file as key, xml root as value.
    # Below transforms exit the xml root, which gets committed at the end
    # if there were no errors.
    gamefile_roots = {
        'sectors'       : [(x, x.Get_Root()) for x in Load_Files('*maps/xu_ep2_universe/*sectors.xml')],
        'zones'         : [(x, x.Get_Root()) for x in Load_Files('*maps/xu_ep2_universe/*zones.xml')],
        'zone_highways' : [(x, x.Get_Root()) for x in Load_Files('*maps/xu_ep2_universe/*zonehighways.xml')],
        'clusters'      : [(x, x.Get_Root()) for x in Load_Files('*maps/xu_ep2_universe/*clusters.xml')],
        'sec_highways'  : [(x, x.Get_Root()) for x in Load_Files('*maps/xu_ep2_universe/*sechighways.xml')],
        }

    # Set of nodes that have been modified.
    # Sector and Zone highway processing will record such nodes, so that
    # a catchall scaling at the end can scale everything left over.
    nodes_scaled = set()

    # Handle sector highways.
    Scale_Sector_Highways(scaling_factor, gamefile_roots, nodes_scaled)

    # Handle zone highways.
    Scale_Zone_Highways(scaling_factor, gamefile_roots, nodes_scaled)

    # Handle everything else.
    Scale_Generic(scaling_factor, gamefile_roots, nodes_scaled)
    
    # If here, everything worked, so commit the updates.
    for file_roots in gamefile_roots.values():
        # TODO: maybe skip clusters, as unmodified.
        for game_file, new_root in file_roots:
            game_file.Update_Root(new_root)

    return


def Scale_Generic(scaling_factor, gamefile_roots, nodes_scaled):
    '''
    Carry out generic scaling not already performed.
    '''
    # Adjust everything remaining in the sector.
    for _, xml_root in gamefile_roots['sectors']:
        
        # Loop over the position nodes.
        for position in xml_root.xpath('.//position'):
            if position in nodes_scaled:
                continue
            nodes_scaled.add(position)
            # Loop over the x/y/z fields.
            for attr in ['x','y','z']:
                XML_Modify_Float_Attribute(position, attr, scaling_factor, '*')

    # TODO: anything to scale in zones, or just rely on them moving
    # closer together in the sector?
    return


class Sector_Highway:
    '''
    Container for data related to sector highway transforms.

    * cluster_name
      - Name of the cluster macro in clusters holding this highway.
    * highway_name
      - String, name of the macro in sechighways, referenced in clusters.
    * cluster_pos
      - Dict of 'x','y','z' values for the highway center position in
        the cluster.
      - May be unused.
    * conn_info
      - Dict holding the entry and exit information, for easier looping.
      - Keys are 'entrypoint' and 'exitpoint'.
      - Values:
        * conn_name
          - Same as the dict key.
        * zone_macro_name
          - String, name of the gate macro in zones, referenced in clusters.
        * sector_name
          - String, name of the sector macro in sectors.
        * sector_pos_node
          - Element, the position node in the sector file.
        * position
          - Dict of x/y/z values taken from the pos node.
        * offsets
          - Dict of 'x','y','z' offsets, determined by scaling in the sector
            position, to be applied in the sector and sechighways files.
    '''
    def __init__(
            self,
            cluster_name,
            highway_name,
            entry_name,
            exit_name,
            cluster_pos,
        ):
        self.cluster_name   = cluster_name
        self.highway_name   = highway_name
        self.conn_info      = {
            'entrypoint' : {
                'conn_name'       : 'entrypoint',
                'zone_macro_name' : entry_name,
                'sector_name'     : None,
                'sector_pos_node' : None,
                'position'        : {},
                'offsets'         : {},
                },
            'exitpoint' : {
                'conn_name'       : 'exitpoint',
                'zone_macro_name' : exit_name,
                'sector_name'     : None,
                'sector_pos_node' : None,
                'position'        : {},
                'offsets'         : {},
                },
            }
        self.cluster_pos    = cluster_pos
        return

    
'''
Within a sector, contents have position nodes that can be directly adjusted
to move zones, resources, and highways.

"Sector" highways are relative to a cluster, not the sector, and so
need special handling.

Conceptually, the cluster connects to a sectorhighway, which in turn
defines an entry/exit pair of positions (very far apart), and a set
of spline points along the way.  Typically, a second sectorhighway
defines the reverse direction, with entry/exit points slightly offset.

The sector specifies a connection position for the highway:
    tzoneCluster_01_Sector002SHCon5_GateZone_connection
The above links to an intermediate macro (found in zones, not much detail):
    tzoneCluster_01_Sector002SHCon5_GateZone_macro
The cluster also makes a connection to this same macro to link up:
    SuperHighway001_Cluster_01_connection (holds both entry and exit).

In the above, the sector gives a position, and the cluster gives a position
for the highway center, and the sechighway file gives entry/exit offsets
relative to the cluster center.

To further complicate issues, the entry/exit gates need to maintain
some distance from each other, to avoid clipping into each other.

To adjust things properly:
- Start by searching clusters to find the entry/exit gate macro pairs,
  and note the sechighway macros they correspond to.
- When scaling sector positions, look for those that attach to sechighway
  macros, and delay processing temporarily.
- For pairs of nodes from the sector, determine their average position,
  apply scaling to that, store the delta, and apply this delta to
  the entry/exit gates equally. (Or maybe allow them to move together
  but with some limit.) Store these offsets.
- Apply the delta to the sechighway node (entry or exit appropriately)
  and its start/end spline.

TODO: was warned to watch for quaternion and rotation in the offset
nodes (which house the position), though they aren't used currently
by ego.
'''
def Scale_Sector_Highways(scaling_factor, gamefile_roots, nodes_scaled):
    '''
    Carry out scaling related to sector highways.
    '''
    # List of Sector_Highway objects.
    highways = []
    
    # Example (want the inner macro refs).
    # Note: could also use the 'path' values to look up the sector
    # nodes, but unnecessary.
    '''
    ' <connection name="SuperHighway001_Cluster_01_connection" ref="sechighways">
    '   <offset>
    '     <position x="8703021" y="0" z="30508566" />
    '   </offset>
    '   <macro ref="SuperHighway001_Cluster_01_macro" connection="cluster">
    '     <connections>
    '       <connection ref="entrypoint">
    '         <macro ref="tzoneCluster_01_Sector002SHCon5_GateZone_macro" path="../../Cluster_01_Sector002_connection/tzoneCluster_01_Sector002SHCon5_GateZone_connection" connection="exitpoint1" />
    '       </connection>
    '       <connection ref="exitpoint">
    '         <macro ref="tzoneCluster_01_Sector003SHCon6_GateZone_macro" path="../../Cluster_01_Sector003_connection/tzoneCluster_01_Sector003SHCon6_GateZone_connection" connection="entrypoint1" />
    '       </connection>
    '     </connections>
    '   </macro>
    ' </connection>
    
    Highways typically come in pairs, with entry/exit points side by side
    in a given sector.
    There is no natural way to identify such pairings in the xml, but it
    can be estimated based on the cluster positions being roughly
    the same.

    Example, the above connection conceptually pairs with:
    
    ' <connection name="SuperHighway002_Cluster_01_connection" ref="sechighways">
    '   <offset>
    '     <position x="8803021" y="0" z="30508566" />
    '   </offset>
    '   ...

    '''
    # Note: these cluster files are not modified.
    for _, xml_root in gamefile_roots['clusters']:

        # Search for the superhighway macros.
        for top_conn_node in xml_root.xpath(".//connection[macro/connections/connection/@ref='entrypoint']"):
            
            cluster_name = top_conn_node.getparent().getparent().get('name')
            # Look up macro name refs.
            macro_node = top_conn_node.find('./macro')
            highway_name = macro_node.get('ref')
            entry_zone_macro_name = macro_node.xpath(
                "./connections/connection[@ref='entrypoint']/macro")[0].get('ref')
            exit_zone_macro_name = macro_node.xpath(
                "./connections/connection[@ref='exitpoint']/macro")[0].get('ref')

            # Gather the position data.
            pos = top_conn_node.find('./offset/position')
            cluster_pos = {}
            for attr, value in pos.items():
                cluster_pos[attr] = float(value)

            # Store it.
            highways.append(Sector_Highway(
                cluster_name = cluster_name,
                highway_name = highway_name,
                entry_name   = entry_zone_macro_name,
                exit_name    = exit_zone_macro_name,
                cluster_pos  = cluster_pos,
                ))
            

    # Sector highway connections have this form (example):
    '''
    ' <connection name="tzoneCluster_01_Sector002SHCon5_GateZone_connection" ref="zones">
    '   <offset>
    '     <position x="40468.75" y="0" z="200000" />
    '   </offset>
    '   <macro ref="tzoneCluster_01_Sector002SHCon5_GateZone_macro" connection="sector" />
    ' </connection>
    '''
    # First sector pass will just gather the entry/exit information, but
    # does no edits (since offsets not yet determined).
    for _, xml_root in gamefile_roots['sectors']:
        for highway in highways:

            # Check each side of the connection (will differ in sector).
            for conn_info in highway.conn_info.values():

                # Look up the connection node.
                conn_node = xml_root.xpath(".//connection[macro/@ref='{}']".format(conn_info['zone_macro_name']))
                if not conn_node:
                    continue
                conn_node = conn_node[0]

                # Get the sector name.
                conn_info['sector_name'] = conn_node.getparent().getparent().get('name')
                # Record the position node, to avoid having to look it up again.
                conn_info['sector_pos_node'] = conn_node.find('./offset/position')
                # Pick out the position info.
                for attr, value in conn_info['sector_pos_node'].items():
                    conn_info['position'][attr] = float(value)


    # Pair off the sector highways.
    # Pairing will be based on entry/exit points that are in the same sector
    # and near the same position.
    # In case entry/exit are paired in one sector but not in another for
    # some reason, these pairs are purely for the conn_info dicts, not for
    # the entire highways.
    conn_info_list = [x for h in highways for x in h.conn_info.values()]
    conn_info_pairs = []

    # Organize the highways by parent sector.
    conn_info_by_sector = defaultdict(list)
    for conn_info in conn_info_list:
        conn_info_by_sector[conn_info['sector_name']].append(conn_info)
        
    # Go through these sublists.
    for conn_info_list in conn_info_by_sector.values():
    
        # Look for connections with very similar positions, x/y/z.
        # This will work on a list copy, popping 1-2 per iteration.
        remaining = list(conn_info_list)
        while remaining:
            # Grab a conn.
            conn_info = remaining.pop()
    
            # Search the rest for matches.
            for other_conn_info in remaining:
                # Skip if both the same side (eg. both entry).
                if conn_info['conn_name'] == other_conn_info['conn_name']:
                    continue

                # Check for a position match.
                match = True
                for attr in ['x','y','z']:
                    this_pos  = conn_info      ['position'][attr]
                    other_pos = other_conn_info['position'][attr]
    
                    # (Special handling if both are 0.)
                    if this_pos == 0 and other_pos == 0:
                        continue
    
                    # Check if not within tolerance.
                    if abs(this_pos - other_pos) > 20000:
                        # Mismatch.
                        match = False
                        break
                # On match, stop searching.
                if match:
                    break
    
            if match:
                # Don't need to check the other conn_info later.
                remaining.remove(other_conn_info)
                # Pair these off.
                conn_info_pairs.append([conn_info, other_conn_info])
            else:
                # Leave this one alone.
                conn_info_pairs.append([conn_info])


    # Determine the sector offsets for the connections.
    for conn_infos in conn_info_pairs:

        # Average the positions.
        avg_start_pos = {}
        for attr in ['x','y','z']:
            values = [x['position'][attr] for x in conn_infos]
            avg_start_pos[attr] = sum(values) / len(values)

        # Scale based on this, and find the offsets.
        offsets = {}
        for attr, value in avg_start_pos.items():
            offsets[attr] = (value * scaling_factor) - value

        # Record to the conn_infos.
        for info in conn_infos:
            info['offsets'] = offsets
                    
            # Update the position nodes now.
            pos_node = info['sector_pos_node']
            for attr, value in offsets.items():
                XML_Modify_Float_Attribute(pos_node, attr, value, '+')
            # Note as modified.
            nodes_scaled.add(pos_node)



    # Using the above information, update the sector highways.
    # Example (with some trimming):
    '''
    ' <macro name="SuperHighway001_Cluster_01_macro" class="highway">
    '   <component ref="standardsechighway" />
    '   <connections>
    '     <connection ref="entrypoint">
    '       <offset>
    '         <position x="-29776510" y="0" z="-22926752" />
    '       </offset>
    '     </connection>
    '     <connection ref="exitpoint">
    '       <offset>
    '         <position x="29866978" y="0" z="22926754" />
    '       </offset>
    '     </connection>
    '   </connections>
    '   <properties>
    '     <boundaries>
    '       <boundary class="splinetube">
    '         <splineposition x="-29776510" y="0" z="-22926752" tx="0.790541887283325" ty="0" tz="0.612407982349396" weight="0" inlength="0" outlength="6239510" />
    '         ...
    '         <splineposition x="29866978" y="0" z="22926754" tx="0.793237626552582" ty="0" tz="0.608912229537964" weight="0" inlength="6275330" outlength="0" />
    '         <size r="1000" />
    '       </boundary>
    '     </boundaries>
    '     ...
    '   </properties>
    ' </macro>
    '''
    for _, xml_root in gamefile_roots['sec_highways']:
        for highway in highways:

            # Find the highway macro.
            macro_node = xml_root.xpath(".//macro[@name='{}']".format(highway.highway_name))
            # Skip if not found (eg. in other file).
            if not macro_node:
                continue
            macro_node = macro_node[0]
            
            splinepos_nodes = macro_node.xpath('./properties/boundaries/boundary/splineposition')

            # Entry and first spline update the same, as do the
            # exit and last spline.
            for conn_name in ['entrypoint','exitpoint']:
                
                # Grab the appropriate offsets.
                offsets = highway.conn_info[conn_name]['offsets']

                # Look up the connection node.
                conn_node = macro_node.find("./connections/connection[@ref='{}']".format(conn_name))
                # Get the position node.
                pos_node = conn_node.find('./offset/position')

                # Find the matching endpoint spline.
                # Note: the spline should, in theory, match the point x/y/z, but
                # in practice it is rounded differently or computed with different
                # numerical error, so may not quite match.
                # Instead, rely on the first spline being entry, last being exit.
                if conn_name == 'entrypoint':
                    splinepos_node = splinepos_nodes[0]
                else:
                    splinepos_node = splinepos_nodes[-1]
                    
                # Update with offsets.
                for node in [pos_node, splinepos_node]:
                    for attr in ['x','y','z']:
                        XML_Modify_Float_Attribute(node, attr, offsets[attr], '+')
                    # Note as modified.
                    nodes_scaled.add(node)

    return




'''
"Zone" highways are a bit of a mess as well.  They define:
- left/right side in sector
- macro locations in sector
- entry/exit points in zonehighways
- entry/exit points in zones

Example from zonehighways:
(Positions don't make sense, at least for exitpoint.)
' <macro name="Highway01_Cluster_04_Sector001_macro" class="highway">
'   <component ref="standardzonehighway" />
'   <connections>
'     <connection ref="entrypoint">
'       <offset>
'         <position x="-5735.763671875" y="0" z="-8191.5205078125" />
'       </offset>
'     </connection>
'     <connection ref="exitpoint">
'       <offset>
'         <position x="11482426" y="0" z="16398607" />
'       </offset>
'     </connection>
'   </connections>
'   <properties>
'     <boundaries>
'       <boundary class="splinetube">
'         <splineposition x="-5735.76" y="0.0" z="-8191.52" tx="0.573576" ty="0.0" tz="0.819152" inlength="0.0" outlength="50814.5" />
'         <splineposition x="81702.3" y="0.0" z="116683.0" tx="0.573557" ty="0.0" tz="0.819166" inlength="50814.5" outlength="174583.0" />
'         <splineposition x="381096.0" y="0.0" z="546425.0" tx="0.571662" ty="0.0" tz="0.820489" inlength="174583.0" outlength="102914.0" />
'         <splineposition x="558724.0" y="0.0" z="798950.0" tx="0.575348" ty="0.0" tz="0.817909" inlength="102913.0" outlength="84756.5" />
'         <splineposition x="704964.0" y="0.0" z="1006960" tx="0.575138" ty="0.0" tz="0.818056" inlength="84756.3" outlength="0.0" />
'         <size r="200" />
'       </boundary>
'     </boundaries>
'     ...
'     <configuration ring="0" />
'   </properties>
' </macro>

Example from sectors:
' <macro name="Cluster_04_Sector001_macro" class="sector">
'   <component ref="standardsector" />
'   <connections>
'     <connection name="Zone001_Cluster_04_Sector001_connection" ref="zones">
'       <offset>
'         <position x="43763.25390625" y="0" z="-153542.640625" />
'       </offset>
'       <macro ref="Zone001_Cluster_04_Sector001_macro" connection="sector" />
'     </connection>
'
'     <connection name="Highway01_Cluster_04_Sector001_connection" ref="zonehighways">
'       <offset>
'         <position x="74331.421875" y="0" z="-114004.1328125" />
'       </offset>
'       <macro ref="Highway01_Cluster_04_Sector001_macro" connection="sector">
'         <connections>
'           <connection ref="entrypoint">
'             <macro path="../../Zone001_Cluster_04_Sector001_connection" connection="Highway01Connection01_gate" />
'           </connection>
'           <connection ref="exitpoint">
'             <macro path="../../Zone020_Cluster_04_Sector001_connection" connection="Highway01Connection02_gate" />
'           </connection>
'         </connections>
'       </macro>
'     </connection>

Example from zones:
' <macro name="Zone001_Cluster_04_Sector001_macro" class="zone">
'   <component ref="standardzone" />
'   <connections>
'     <connection ref="Highway02Connection02_gate">
'       <offset>
'         <position x="29741.875" y="0" z="27909.33984375" />
'       </offset>
'     </connection>
'     <connection ref="Highway01Connection01_gate">
'       <offset>
'         <position x="24832.404296875" y="0" z="31346.9921875" />
'       </offset>
'     </connection>
'   </connections>
' </macro>

Example compute, where gate position matches highway endpoint:
- Zone001_Cluster_04_Sector001_macro x offset 43763 in sector
- Highway01Connection01_gate (entry) offset 24832 in zone
- = Entry gate at 68595
- Highway01_Cluster_04_Sector001_macro x offset 74331 in sector
- Above entry offset -5735 in zonehighways.
- = Highway entry at 68596

So, similar to sector/cluster highways:
- Sector defines a center position of the highway.
- Zonehighway defines offsets for entry and exit gates (and splines).
However, differences include:
- Inner splines cannot be ignored, and need scaling.
- Zone defines another offset, which needs scaling.
- Zone also defines gate positions, which need scaling so that gate
  connected highways line up properly.

Most of this can be done semi-blindly and work, though separating the
sides of the highway follows similar logic to sector highways above.
Pairings should be based on endpoint position in zones.

The highway splines would be particularly troublesome, since the amount
of separation a pair needs will vary along the highway path.
Would this require pairing up every spline point (assuming a matched
number) and determining offsets at each point?
TODO: think about this more, but probably.

TODO: also think about catching the highway advertisements.

How to do the offset scaling:
- Compute total endpoint position in sector
  (from zone/gate offset, or highway/endpoint offset).
- Pair up endpoints (based on zone position proximities).
- Scale endpoint sector positions, determining total offset, using average
  of each pair. Save offset to each endpoint.
- Scale the zone position in sector, and note the delta. Any difference
  from the desired offset will be applied to the gate pos in zone
  (highway gates and any standard gates as well).
- What about the highway???

Alternatively, let it be janky a really small scaling factors; normally
there are a few km of separation to tolerate light scaling.

'''
class Zone_Highway:
    '''
    Container for data related to zone highway transforms.

    * sector_name
      - Name of the sector macro holding this highway.
    * highway_name
      - String, name of the macro in zonehighways, referenced in sectors.
    * conn_info
      - Dict holding the entry and exit information, for easier looping.
      - Keys are 'entrypoint' and 'exitpoint'.
      - Values:
        * conn_name
          - Same as the dict key.
        * zone_macro_name
          - String, name of the gate macro in zones, referenced in sectors.
        * zone_name
          - String, name of the zone macro in zones.
        * zone_pos_node
          - Element, the position node in the zone file.
        * ???
    '''
    def __init__(
            self,
            sector_name,
            highway_name,
        ):
        self.sector_name    = sector_name
        self.highway_name   = highway_name
        self.conn_info      = {
            'entrypoint' : {
                'conn_name'       : 'entrypoint',
                'zone_macro_name' : entry_name,
                'zone_name'       : None,
                'zone_pos_node'   : None,
                },
            'exitpoint' : {
                'conn_name'       : 'exitpoint',
                'zone_macro_name' : exit_name,
                'zone_name'       : None,
                'zone_pos_node'   : None,
                },
            }
        return



def Scale_Zone_Highways(scaling_factor, gamefile_roots, nodes_scaled):
    '''
    Carry out scaling related to zone highways.
    Currently just does basic scaling; lanes may move closer together
    or futher apart.
    '''
    highways = []

    # Search the sector for highways.
    # TODO

    # Fill in zone info for the endpoints.
    # TODO

    # Pair up the endpoints.
    # TODO

    # Determine total desired offset for each endpoint.
    # TODO

    # Scale the zone position in sector, and apply leftover offset to
    # the endpoint positions in the zone.
    # TODO

    # Scale the highway position and zonehighway values?
    # TODO

    # Compute total endpoint position in sector
    # (from zone/gate offset, or highway/endpoint offset).
    # Pair up endpoints (based on zone position proximities).
    # Scale endpoint sector positions, determining total offset, using average
    # of each pair. Save offset to each endpoint.
    # Scale the zone position in sector, and note the delta. Any difference
    # from the desired offset will be applied to the gate pos in zone
    # (highway gates and any standard gates as well).
    # Do not scale the highway position in sector.
    # Apply offset to highway defined endpoints.
    
    # Update in-sector zone highways, blind scaling.
    for _, xml_root in gamefile_roots['zone_highways']:

        for position in xml_root.xpath('.//position'):
            nodes_scaled.add(position)
            for attr in ['x','y','z']:
                XML_Modify_Float_Attribute(position, attr, scaling_factor, '*')
            
        # Do the same for zonehighway splines.
        for position in xml_root.xpath('.//splineposition'):
            nodes_scaled.add(position)
            for attr in ['x','y','z','tx','ty','tz','inlength','outlength']:
                XML_Modify_Float_Attribute(position, attr, scaling_factor, '*')

    # Upate entries in zones.
    # Do this dumb for now.
    for _, xml_root in gamefile_roots['zones']:
        for connection in xml_root.xpath('.//connection'):
            ref = connection.get('ref')

            # Look for highways.
            # Also look for gates, to move them with highway endpoint for
            # those highways that lead to a gate.
            if ref and ref.startswith('Highway') or ref == 'gates':
                position = connection.find('./offset/position')
                nodes_scaled.add(position)
                for attr in ['x','y','z']:
                    XML_Modify_Float_Attribute(position, attr, scaling_factor, '*')



    return

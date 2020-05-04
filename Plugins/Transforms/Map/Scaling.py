
import random

from Framework import Plugin_Log, Print
from .Classes import *


def Scale_Regions(galaxy, scaling_factor, debug):
    '''
    Scale all regions up if scaling_factor.
    '''
    for region in galaxy.regions.values():
        region.Scale(scaling_factor)
    return

    
def Scale_Sectors(galaxy, scaling_factor, debug, precision_steps):
    '''
    Scale all sectors to roughly match the scaling factor.
    '''
    # For debug, print out starting sector attributes.
    def Print_Gate_Distances(title):
        lines = [f'{title} sector gate distances:']
        distances = [x.Get_Gate_Distance() for x in galaxy.class_macros['sectors'].values()]
        lines.append(', '.join([str(int(x)) for x in sorted(distances)]))
        # Pick out those of significant separation, eg. over 50 km.
        distances_over_50 = [x for x in distances if x > 50000]
        lines.append(f'Average (>50km): {sum(distances_over_50) / len(distances_over_50)}')
        Plugin_Log.Print('\n'.join(lines))

    if debug:
        Print_Gate_Distances('Pre-scaling')
     
    # Quick check for duplicate names; none found.
    #for name in sorted(galaxy.class_macros['sectors'].keys()):
    #    Print(name)

    # Apply to all sectors individually.
    for sector in galaxy.class_macros['sectors'].values():
        # Testing, pick a sector.
        #if sector.name != 'Cluster_416_Sector002_macro':
        #    continue
        Scale_Sector(galaxy, sector, scaling_factor, debug, precision_steps)
        # In testing, skip after first sector.
        #break
        
    # For debug, print out ending sector attributes.
    if debug:
        Print_Gate_Distances('Post-scaling')


    # Scale the god station defaults.
    galaxy.god_default_obj.Scale(scaling_factor)

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


def Scale_Sector(galaxy, sector, scaling_factor, debug, precision_steps):
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

    # Attach the scaling factor to the sector. Used in sector Size()
    # calculations to select a minimum.
    sector.Set_Scaling_Factor(scaling_factor)

    # Collect objects.
    objects = []
    
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
            for i, spline_pos in enumerate(conn.macro.Get_Splines_With_Dummies()):
                # The spline position is relative to the zone center
                # in the sector.
                sector_pos = conn.position + spline_pos
                objects.append( Object(
                    sector_pos = sector_pos,
                    name = conn.name + f'_spline[{i}]',
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
        # TODO: are there any audio regions that aren't simple spheres?
        if 'audio' in macro.region.name:
            continue

        # These cases have only a cluster position normally, and need
        # a sector position generated.
        cluster_pos = macro.parent_conns[0].position
        # If the cluster object is at x=6, and sector is at x=7, then
        # the cluster object is at x=-1 in sector.
        sector_pos = cluster_pos - sector_in_cluster_pos

        # If this has splines, split those out into separate objects,
        # else pack the thing as-is. These include dummies, to help
        # with locations along the path.
        splinepositions = macro.region.Get_Splines_With_Dummies()
        if splinepositions:
            for i, spline_pos in enumerate(splinepositions):
                # The spline position is relative to the region center
                # in the sector.
                spline_sector_pos = sector_pos + spline_pos
                # As well as relative to the cluster position.
                spline_cluster_pos = cluster_pos + spline_pos
                objects.append( Object(
                    cluster_pos = spline_cluster_pos,
                    sector_pos = spline_sector_pos,
                    name = macro.name + f'_spline[{i}]',
                    connection = macro.parent_conns[0],
                    spline_pos = spline_pos,
                    type = type(macro),
                    ))

        else:  
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
        
        # Handle based on if this has a position or not.
        if god_object.position:
            objects.append( Object(
                sector_pos = god_object.position,
                name = god_object.name,
                god_object = god_object,
                type = type(god_object),
                ))
        else:
            # It is randomized; scale its rand range.
            god_object.Scale(scaling_factor)


    # Calculate the sector center (may be offset from 0).
    sector_center = sector.Get_Center()

    # Start by adjusting all objects to be centered around 0.
    # -Removed for now; unsure if this would have any benefit, but it
    # has high risk of detriment, and makes it a little harder to
    # debug movements (comparing start/end), and it may lead to more
    # skew in highways that are otherwise often well centered.
    #for object in objects:
    #    # Eg. if object is at x=10, center is x=4, then new object pos is x=6.
    #    object.sector_pos -= sector_center

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
            lines.append('  '+str(object))
        Plugin_Log.Print('\n'.join(lines))

    
    # Put all objects into groups, starting with one per group.
    # Do this after sector center adjustment, to avoid the group
    # sector_pos being off.
    object_groups = [Object_Group([x]) for x in objects]

    # TODO: any special case forced groupings.
    # - Spline endpoints with their highway entry/exit zones (maybe handled by radius).
    # - Hazard regions with objects inside them.
    # - Superhighway entry/exit pairs (probably handled by radius).

    # TODO: more detailed algorithm that deals with damage regions better.

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
    step_scaling = scaling_factor ** (1 / precision_steps)

    for step in range(precision_steps):
        # Start by looking for groups that can/should be merged (since this
        # may occur on the first iteration for objects that are already
        # at or below the min allowed distance).
        
        if debug:
            Plugin_Log.Print('Starting step {} of {}'.format(step+1, precision_steps))

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

                # TODO: tweak merging rules when expanding the sector,
                # since only highway splines need to be kept together.

                # Are they close enough that they should merge?
                if this_group.Should_Merge_With(other_group, target_sector_size, step_scaling):
                    
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
                            lines.append('  '+str(object))
                        lines.append('with:')
                        for object in other_group.objects:
                            lines.append('  '+str(object))
                        lines.append('center: {}'.format(new_group.sector_pos))
                        lines.append('')
                        Plugin_Log.Print('\n'.join(lines))
                    break
                
        # Increment everything to be closer (apply change).
        for group in object_groups:
            group.Scale_Pos(step_scaling)
            

    if debug:
        lines = [
            '',
            ' final objects (before decentering/recentering): ',
            ]
        for object in objects:
            lines.append('  {}'.format(object))
        Plugin_Log.Print('\n'.join(lines))


    # De-center the objects.
    for object in objects:
        # Put the sector center offset back, if not keeping a global recenter.
        # -Removed; the initial offset was commented out above.
        #if not galaxy.recenter_sectors:
        #    object.sector_pos += sector_center

        # Put the zone offset back.
        if object.connection and isinstance(object.connection.macro, Zone):
            object.sector_pos -= object.connection.macro.Get_Center()


    # If requested, center objects around 0ish.
    # This may help other scripts that do not account for coreposition to
    # avoid putting things too far out.
    if galaxy.recenter_sectors:
        for object in objects:
            # Eg. if object is at x=10, center is x=4, then new object pos is x=6.
            object.sector_pos -= sector_center

            
    # Since god has trouble placing zones in tightly packed sectors,
    # when scaling down add some new manual zones to help out.
    # Note: can do this earlier, but it is probably faster to add these
    # post-scaling to avoid them getting position checked a bunch of
    # time in the above loop.
    # Do this before the following code that pushes object positions
    # back to their connections.
    Create_Zones(galaxy, sector, objects, scaling_factor)


    # Push the new sector positions back to the original zones/etc.
    for object in objects:

        # Adjust cluster-level objects.
        if object.cluster_pos:
            # Get the offset.
            offset = object.sector_pos - object.orig_sector_pos

            # This could be the base object (conection in cluster), or
            # a spline of it.
            if object.spline_pos:
                # Apply the offset to the spline_pos.
                object.spline_pos.Update(object.spline_pos + offset)
            else:
                # Apply the offset to the cluster position.
                object.connection.position += offset

            
        # Adjust highway splines back to their offset position.
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
        lines = [
            '',
            ' final objects: ',
            ]
        for object in objects:
            lines.append('  {}'.format(object))
        Plugin_Log.Print('\n'.join(lines))

        final_size = sector.Get_Size()
        lines = [
            '',
            'final size: {:.0f}'.format(final_size),
            'reduction : {:.0f}%'.format((1 - final_size / sector_size)*100),
            ]
        Plugin_Log.Print('\n'.join(lines))

    return


def Create_Zones(galaxy, sector, objects, scaling_factor):
    '''
    Create additional zones in this sector. New zones are packed into
    objects and appended to the given objects list directly.
    '''    
    # Guide placement using the current sector center and size.
    sector_center = sector.Get_Center()
    sector_size = sector.Get_Size()

    # For consistency across runs, seed the rng.
    # Use the sum of the sector name characters for this, so each
    # sector is a bit different, but still consistent.
    if not galaxy.randomize_new_zones:
        random.seed(sector.name)

    # The needed zone count is a little unclear, as it depends on the
    # number of god stations (which could be affected by mods).
    # Start with a fixed value.
    # Note: diff patches for new zones take a while to generate due
    # to lxml/xpath slowdown when dealing with long lists.
    # Note: at 10 zones, still had a couple station placement failures.
    # Also, low zone counts will tend to lead to same station spots
    # on each new game.
    num_zones = 15

    for i in range(num_zones):
        
        # Create the zone itself, at 0,0,0.
        zone = galaxy.Create_Zone(sector)
        conn = zone.parent_conns[0]

        # Pack into an object.
        object = Object(
            sector_pos = conn.position,
            name = conn.name,
            connection = conn,
            type = type(conn.macro),
            )

        # Place the object in the sector.
        # Use the size/position from before the new zones were added,
        # to avoid drift.
        Place_Object(object, objects, sector_size, sector_center)

        # Add to the existing objects for future placements.
        objects.append(object)

    return


def Place_Object(
        object,
        other_objects,
        sector_size,
        location,
    ):
    '''
    Place an object in the sector within the max_distance of the given
    location, outside the radius of any other object.
    The object sector_pos is updated directly.
    '''
    # Each attempt will start with a random location, where locations
    # are selected within progressively larger bands.
    # Starts from 0 to quarter sector size (where half sector size would
    # put the location on the edge of the sector).
    min_dist = 0
    max_dist = sector_size / 8

    while 1:
        # Make a few attempts within this range.
        success = False
        for attempt in range(10):

            # It is easy to make a rand location within a square, hard to
            # do within a circle directly.
            # This will just get rng spots in the square until one falls
            # within the circle.
            # Note: to hit the inner parts of the circle at corners,
            # need to adjust down the min_dist a bit.
            min_x = min_z = min_dist / 1.4

            # Max y will be similar to vanilla but squeezed a little.
            # Vanilla sets this linearly from 0 at the sector core center,
            #  to 40km at the core boundary. This will do the same,
            #  treating half of sector_size as the boundary, but allowing
            #  the central max_y to be larger, eg. 20km.
            # TODO: maybe just gaussian.
            max_y = 20000 + 20000 * max_dist / (sector_size / 2)
            # Standard zones already have plenty of stuff at y=0; give
            # a lockout to force new zones to spread out more.
            min_y = 5000

            # TODO: maybe switch to checking positions of existing zones, and
            # trying to stay relatively close to them, since they can
            # indicate the shape of the region. Though god zones seem to
            # be pretty random, so this is fine for now.

            while 1:
                pos = Position(
                    x = random.uniform(min_x, max_dist) * (1 if random.random() < 0.5 else -1),
                    z = random.uniform(min_z, max_dist) * (1 if random.random() < 0.5 else -1),
                    # TODO: non-uniform y, concentrating more toward 0.
                    y = random.uniform(min_y, max_y) * (1 if random.random() < 0.5 else -1),
                    )
                distance = pos.Get_Distance()
                if min_dist <= distance <= max_dist:
                    break            

            # Offset for the target location.
            # Eg. if rng picked x=+5, and location is x=6, then this will
            # put it at x=11.
            pos += location

            # Attach to the object for the following checks.
            object.sector_pos = pos

            # Search all other objects for conflicts.
            conflict = False
            for other_obj in other_objects:
                # Can base on the merge logic.
                # Note: this means a new zone can be placed within a damage
                # region, just not at the edge of it, but that's probably
                # okay.
                if object.Should_Merge_With(other_obj):
                    # Too close; reject.
                    conflict = True
                    break

            # If no conflicts detected, this spot is okay.
            if not conflict:
                success = True
                break

        # Stop when successful.
        if success:
            break
        
        # Adjust the rng band for next major loop.
        min_dist = max_dist
        max_dist = max_dist * 1.2
                
    return

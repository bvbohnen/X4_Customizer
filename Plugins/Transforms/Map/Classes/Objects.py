
from Framework.Documentation import Doc_Category_Default
_doc_category = Doc_Category_Default('Map_Transforms')

from itertools import combinations
from copy import copy

from ....Classes import *
from .Macros import *
from .Highways import *
from .Misc import *

__all__ = [
    'Object',
    'Object_Group',
    ]

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
    * orig_sector_pos
      - Copy of sector_pos made before any scaling.
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
    * inner_radius
      - Float, inner radius of this object, inside which other objects
        already present will be allowed to move.
    * contains_gate
      - Flag, True if the object is a zone with a gate or sec highway entry/exit.
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
        self.orig_sector_pos = copy(sector_pos)
        self.contains_gate = False        

        # Default radius to that of zones, splines, misc.
        # Zones are 10km apart in vanilla, which can be considered 5km radius
        # on each. Add a little extra safety.
        self.radius = 5000 + 1000
        self.inner_radius = None

        if spline_pos:
            # Note: splines that should be roughly paired are observed to
            # be ~10 km apart, so add some extra radius here to encourage
            # the splines to group up and move together.
            self.radius += 1000

        elif connection:
            # Start with the macro's radius.
            self.radius = connection.macro.radius
            self.inner_radius = connection.macro.inner_radius

            # Zones with gates will be given some extra spacing, so ships can
            # fly around them and such.
            # This will be finetuned later to avoid gate-to-gate distances
            # getting too short.
            if isinstance(connection.macro, Zone):
                zone = connection.macro
                if zone.Contains_Gate():
                    self.contains_gate = True
                    # Some extra spacing.
                    self.radius += 5000

        # MD objects annotate their radius.
        elif md_object:
            self.radius = md_object.radius
            
        elif god_object:
            self.radius = god_object.radius
        return


    def Should_Merge_With(self, other, sector_size = 200000, scaling = 1):
        '''
        Returns True if this object should merge with another object that
        is too close.
        '''
        # If this is a dummy spline position and some other spline position
        # (dummy or not), don't merge, else the dummies would prevent
        # splines from compressing. (Dummies exist to prevent other objects
        # from getting between the real splines.)
        if ( self.spline_pos and other.spline_pos 
        and (self.spline_pos.dummy or other.spline_pos.dummy)):
            return False

        # Determine allowed distance.
        # Prevent the radiuses from touching.
        allowed_dist = self.radius + other.radius

        # If both objects are zones with gates, limit their proximity
        # to roughly a fraction of the desired sector size.
        # To be safe, add this to the radiuses, since the gates in
        # the zones may be placed near to each other's zone.
        # Only do this when scaling down.
        if scaling < 1 and self.contains_gate and other.contains_gate:
            allowed_dist += sector_size / 2

        # Check proximity.
        if self.sector_pos.Is_Within_Distance(other.sector_pos, allowed_dist):
            
            # If either object has an inner_radius, check that.
            # When objects are closer than the inner_radius, don't merge,
            # since they can still move with respect to each other.
            # Note: two large regions may be partially overlapped, but don't
            # want to further overlap them, so check that the smaller region is 
            # fully inside the larger when not merging.
            smaller, larger = (self, other) if self.radius < other.radius else (other, self)
            if larger.inner_radius:

                # Looking for the smaller region's furthest edge from the
                # larger region (eg. a radius away) to be within the larger
                # region's edge (the larger inner_radius).
                allowed_distance = larger.inner_radius - smaller.radius
                    
                if smaller.sector_pos.Is_Within_Distance(
                        larger.sector_pos, allowed_distance):
                    # Close enough together to avoid a merge.
                    return False

            # Too close, one not inside the other, so merge.
            return True        
        return False


    def __str__(self):
        return '{} : {} (radius: {:.0f}{})'.format(
            self.name, 
            self.sector_pos, 
            self.radius,
            ', inner: {:.0f}'.format(self.inner_radius) if self.inner_radius else '',
            )


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
                               and x.connection.macro.Is_Damage_Region() 
                               for x in objects)
        self.has_non_regions = any(x.type != Region_Macro for x in objects)

        # Compute average sector position.
        # Note: if a highway splines are in this group, they should control
        # the average position, to better maintain the shape of highways.
        # Note: for trinity sanctum 3, there is a misc highway that does
        # a half circle, which tends to get grouped with and throw off the
        # main ring highways. As such, this will favor ring highway splines,
        # then general highways, then everything.
        ring_splines = [x for x in objects 
                        if x.spline_pos and issubclass(x.type, Highway)
                        and x.connection.macro.is_ring_piece]
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
        sector_pos = Position()
        weights = 0
        for object in centering_objects:
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
    

    def Should_Merge_With(self, other, sector_size, scaling):
        '''
        Returns True if this group should merge with the other group based
        on internal objects between groups getting too close.
        '''
        # Disallow merging regions and non-regions, since that is overly
        # restrictive.  (Eg. zones can go inside asteroid fields.)
        # However, if the region does damage, allow merging, so try to keep
        # zones from being moved inside the damage.
        # Update: allow merging, since other rules allow objects to move
        # around inside regions, and this merge would help support some
        # cases where a zone/object/etc should stay aligned with
        # a nearby over overlapping region.
        #if not self.has_damage_regions and not other.has_damage_regions:
        #    if((self.has_regions and not other.has_regions)
        #    or (not self.has_regions and other.has_regions)):
        #        return False        

        # Check all object combos between groups.
        for object_1 in self.objects:
            for object_2 in other.objects:
                if object_1.Should_Merge_With(object_2, sector_size, scaling):
                    return True
        return False



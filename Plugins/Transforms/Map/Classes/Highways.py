
from Framework.Documentation import Doc_Category_Default
_doc_category = Doc_Category_Default('Map_Transforms')

from ....Classes import *
from .Macros import Map_Macro

__all__ = [
    'Highway',
    'Zone_Highway',
    'Sector_Highway',
    ]

class Highway(Map_Macro):
    '''
    Parent class for zone highways and sector highways.
    
    * spline_positions
      - Spline_Position_List holding the splinepositions, or None.
      - None if the region doesn't have splines.
    '''
    def __init__(self, xml_node):
        super().__init__(xml_node)

        # Give some spacing around the highway.
        self.radius = 6000
        
        self.spline_positions = Spline_Position_List(xml_node.xpath('.//splineposition'))

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
    
    def Contains_Gate_Or_Highway(self):
        return True

    def Update_Splines(self):
        'Adjust splines for tx/ty/tz/inlength/outlength'
        self.spline_positions.Recompute_Deltas()

    def Get_Splines_With_Dummies(self):
        '''
        Returns a list with all splinepositions, along with a set
        of dummy splinepositions interpolated along the path
        every radius stepping.
        '''
        return self.spline_positions.Get_Splines_With_Dummies(self.radius)

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
                    spline_pos.Update(conn.position)
                else:
                    conn.position.Update(spline_pos)

        # Use shared code to fix inlength/outlength/tx/ty/tz.
        super().Update_Splines()
        return


class Sector_Highway(Highway):
    '''
    Information on sector highway.
    '''    
    def Contains_Gate(self):
        return True

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
            self.spline_positions[i].Update(position)
        
        # Use shared code to fix inlength/outlength/tx/ty/tz.
        super().Update_Splines()
        return
    


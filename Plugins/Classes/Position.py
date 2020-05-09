
from copy import copy
import math

__all__ = [
    'Position',
    'Spline_Position',
    'Spline_Position_List',
    ]

# TODO: drop support for y, maybe.
class Position:
    '''
    Position of an object, typically either in a sector or in a cluster.

    * xml_node
      - Position node from the xml, or None if nothing associated.
    * x,y,z
      - Floats, current position.
      - May differ from the original xml.
      - If used in init, any missing coordinates will default to 0.
    '''
    def __init__(self, xml_node = None, x = None, y = None, z = None):
        self.xml_node = xml_node
        if xml_node != None:
            # Sometimes a dim is forgotten; treat as 0.
            for attr in ['x','y','z']:

                val_str = xml_node.get(attr)
                if val_str:

                    # If there is a 'km' suffix, adjust for it.
                    in_km = False
                    if val_str.endswith('km'):
                        val_str = val_str.replace('km','')
                        in_km = True
                    elif val_str.endswith('m'):
                        val_str = val_str.replace('m','')

                    value = float(val_str)
                    if in_km:
                        value *= 1000
                else:
                    value = 0.0
                setattr(self, attr, value)
        else:
            # Fill 0s for coordinates not given.
            self.x = x if x else 0
            self.y = y if y else 0
            self.z = z if z else 0
        return

    def Update_XML(self):
        '''
        Apply the current position back to the xml node.
        Should be called at the end of all processing.
        '''
        if self.xml_node != None:
            self.xml_node.set('x', str(self.x))
            self.xml_node.set('y', str(self.y))
            self.xml_node.set('z', str(self.z))
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
    * dummy
      - Bool, True for dummy spline positions inserted at interpolated points.
    '''
    def __init__(self, xml_node):
        super().__init__(xml_node)
        self.dummy = False
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
            self.xml_node.set(attr, str(getattr(self, attr)))
        return

    
class Spline_Position_List(list):
    '''
    List of spline positions, with some functions to manage them.

    * []
      - List of spline positions.
    * orig_spline_positions
      - Originals of the positions, just for debug viewing.
    '''
    def __init__(self, xml_nodes):
        list.__init__(self)
        self.orig_spline_positions = []
        for node in xml_nodes:
            self.append(Spline_Position(node))
            self.orig_spline_positions.append(Spline_Position(node))
        return
    

    def Get_Splines_With_Dummies(self, radius):
        '''
        Returns a list with all splinepositions, along with a set
        of dummy splinepositions interpolated along the path
        every radius stepping.
        '''
        ret_list = list(self)

        # Loop over pairs of positions.
        for i in range(len(self) -1):
            start = self[i]
            end   = self[i+1]
            distance = start.Get_Distance_To(end)
            offset = end - start
            
            # Select a dummy count.
            # Every 2 - 4 radiuses makes sense.
            # Note: special merging logic will be needed to avoid
            # these dummies preventing actual splines from shrinking.
            num_dummies = round(distance / (radius * 4))

            # Note: long distances can end up with a ton of dummy spam,
            # bogging down the scaling. Artificially limit the
            # dummy count here.
            num_dummies = min(num_dummies, 5)

            # These are placed at fractions of the start->end offset
            # from start. The initial point will be moved out a bit
            # to center the dummies.
            for d in range(num_dummies):
                # 1 dummy starts halfway; two dummies starts at 1/3, etc.
                ratio = (d+1) / (num_dummies + 1)
                dummy_pos = start + offset * ratio
                # Make sure the xml_node is cleared.
                dummy_pos.xml_node = None
                dummy_pos.dummy = True
                #ret_list.append(dummy_pos)

        return ret_list

    
    def Recompute_Deltas(self):
        '''
        Adjust splines for tx/ty/tz/inlength/outlength, based on current
        x/y/z positions.
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
        for i, this_pos in enumerate(self):

            # Get the nodes on either side.
            prior_pos = self[i-1] if i != 0 else None
            next_pos  = self[i+1] if i+1 != len(self) else None

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
    

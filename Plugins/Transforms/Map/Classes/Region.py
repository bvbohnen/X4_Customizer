
from ...Classes import *
from ...Support import XML_Modify_Float_Attribute

__all__ = [
    'Region',
    ]

class Region:
    '''
    Region, read from region_definitions. Note: not a macro.

    * xml_node
      - Region xml node.
    * name
      - String, name of the region.
    * radius
      - Float, radius of this region, large enough to encompass it
        and all splines/etc.
    * inner_radius
      - Float, the inner radius of the region in which objects can move
        if inside.
    * does_damage
      - Bool, True if this region does passive hull damage.
      - Shield-only damage is ignored for now.
    * spline_positions
      - Spline_Position_List holding the splinepositions, or None.
      - None if the region doesn't have splines.
    '''
    def __init__(self, xml_node):
        self.xml_node = xml_node
        self.name = xml_node.get('name')
        
        self.does_damage = False
        # Check any damage nodes for a hull damage type.
        damage_nodes = xml_node.xpath('.//damage')
        for node in damage_nodes:
            # Two ways for it to apply hull damage.
            for field in ['hull', 'noshield']:
                self.does_damage = True
                break            

        self.spline_positions = None
        spline_nodes = xml_node.xpath('.//splineposition')
        if spline_nodes:
            self.spline_positions = Spline_Position_List(spline_nodes)
                 
        # Radius is updated with shared code.
        self.Update_Radius()
        return


    def Get_Splines_With_Dummies(self):
        '''
        Returns a list with all splinepositions, along with a set
        of dummy splinepositions interpolated along the path
        every radius stepping.  Empty list if no splines in use.
        '''
        if not self.spline_positions:
            return []
        return self.spline_positions.Get_Splines_With_Dummies(self.radius)


    def Update_Radius(self):
        '''
        Fills in the radius from the xml_node, adjusts for damage,
        and sets inner_radius. Used at init and after scaling.
        Note: regions with splines are not well represented by this radius.
        '''
        # Get an estimate of the radius from the size node.
        boundary_node = self.xml_node.find('./boundary')
        size_node     = boundary_node.find('./size')

        # Can come in different shapes, but all have an 'r' radius.
        # Ignore the 'l' of cylinders for now; it is shorter than 'r'
        # in spot checked cases, and may be used just for the vertical (y)
        # which doesn't have notable conflicts.
        self.radius = float(size_node.get('r'))

        # Set the inner portion as some fraction of the whole.
        # For large regions, use a flat subtraction; for small regions,
        # go with a multiplier.
        self.inner_radius = max(self.radius - 5000, self.radius * 0.9)

        # If this does hull damage, the damage radius may be larger than
        # the basic radius. Bump it up in this case.
        # (Eg. comes up with the lightning damage in Lasting Vengeance
        #  Cluster_35.)
        # Note: leave inner_radius alone in this case; objects deep inside
        # should stay deep inside.
        if self.does_damage:
            # Look for an effect node with the damage node.
            effect_node = self.xml_node.find('./fields/effect')
            if effect_node != None and effect_node.find('./damage') != None:
                effect_radius = effect_node.get('maxdistance')
                if effect_radius:
                    effect_radius = float(effect_radius)
                    if effect_radius > self.radius:
                        self.radius = effect_radius
        return


    def Scale(self, scaling_factor):
        '''
        Scale the size of this region by the scaling factor.
        Since regions may have issues when shrinking, any reductions
        will be limited in some way.
        Regions with splines will ignore this, in favor of spline movements.
        Should be called before adjusting sector sizing, so it can
        reflect the new size.
        Changes the xml directly.
        '''
        if self.spline_positions:
            return

        # Resource regions are ~25km radius.
        # Big shield damage region in xenon sector is 250 km.
        # Want to scale the latter down, not the former down.
        if scaling_factor < 1:
            # Cut scaling in half, to tame it a bit.
            scaling_factor = 1 - (1 - scaling_factor)/2
            # Reserve up to 50k, scale the rest.
            reserve = min(50000, self.radius)
            scaling_factor = (reserve + (self.radius - reserve) * scaling_factor) / self.radius

        # Adjust all of the size attributes.
        size_node = self.xml_node.find('./boundary/size')
        for attr in size_node.keys():
            XML_Modify_Float_Attribute(size_node, attr, scaling_factor, '*')

        # Adjust any effect node maxdistances.
        effect_nodes = self.xml_node.xpath('.//effect')
        for node in effect_nodes:
            if node.get('maxdistance'):
                XML_Modify_Float_Attribute(node, 'maxdistance', scaling_factor, '*')        

        # Update the radius calculation.
        self.Update_Radius()
        return

    
    def Update_XML(self):
        '''
        Update xml, adjusting spline positions.
        '''
        if self.spline_positions:
            for position in self.spline_positions:
                position.Update_XML()
        return

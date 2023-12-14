
from Framework.Documentation import Doc_Category_Default
_doc_category = Doc_Category_Default('Map_Transforms')

from ....Classes import *
from .Macros import *
from ...Support import XML_Modify_Int_Attribute

__all__ = [
    'MD_Object',
    'MD_Placed_Object',
    'MD_Headquarters',
    'God_Object',
    'MD_gs_split1_battlefield',
    'MD_gs_split1_pickupship',
    'MD_Gamestart',
    ]

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


class MD_Placed_Object(MD_Object):
    '''
    Object from PlacedObjects: ships, data vaults.

    * xml_node
      - A sector_find md operation.
    '''
    def __init__(self, xml_node):
        super().__init__(xml_node)

        # Pick out the sector name.
        self.sector_name = xml_node.get('macro').replace('macro.','')
        '''
        Syntax on ships is:
        <find_sector macro="macro.cluster_27_sector001_macro" .../>
        <do_if ...
        <create_ship ...>
         <position ...
        '''
        # Next is do_if; find the position inside it.
        pos_node = xml_node.getnext().find('.//position')
        if pos_node != None:
            # These are similar to normal positions.
            self.position = Position(pos_node)
            # Radius can be pretty small.
            self.radius = 2000
        
    def Update_XML(self):
        # TODO: maybe put in km.
        if self.position:
            self.position.Update_XML()


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

    
class MD_gs_split1_battlefield(MD_Object):
    '''
    Split start battlefield location, used to spawn defense fleet, player,
    ref position for rescue ship (which should also be moved closer).
    
    * battlefield_pos_node
    '''
    def __init__(self, xml_node):
        super().__init__(xml_node)
        self.name = 'MD_gs_split1_battlefield'

        # Bump up the radius a bunch.
        # 40k should be good enough, maybe.
        self.radius = 40000
    
        # Sector name is set earlier in the file.
        # <find_sector name="$FiresOfSector" macro="macro.cluster_421_sector001_macro"/>
        self.sector_name = xml_node.find('.//find_sector[@name="$FiresOfSector"]').get('macro').replace('macro.','')

        # Get the position node.
        # <create_position name="$Battlefield" object="$FiresOfSector" x="42000" y="-5000" z="120000" ...
        self.battlefield_pos_node = xml_node.find('.//create_position[@name="$Battlefield"]')
        self.position = Position(self.battlefield_pos_node)
        return
    
    def Update_XML(self):
        # Can update the position normally.
        self.position.Update_XML()
        return
    

class MD_gs_split1_pickupship(MD_Object):
    '''
    Split start rescue ship location.

    * rescue_ship_pos_node
    '''
    def __init__(self, xml_node):
        super().__init__(xml_node)
        self.name = 'MD_gs_split1_pickupship'

        # Radius is small for the actual ship, but want it to still spawn
        # some distance away, so bump this up a little bit.
        self.radius = 20000
    
        # Sector name is set earlier in the file.
        # <find_sector name="$FiresOfSector" macro="macro.cluster_421_sector001_macro"/>
        self.sector_name = xml_node.find('.//find_sector[@name="$FiresOfSector"]').get('macro').replace('macro.','')

        # Get the battlefield position node.
        # <create_position name="$Battlefield" object="$FiresOfSector" x="42000" y="-5000" z="120000" ...
        battlefield_pos_node = xml_node.find('.//create_position[@name="$Battlefield"]')

        # Get the rescue ship offset node.
        # <position x="$Battlefield.x - 22237" y="$Battlefield.y + 5000" z="$Battlefield.z - 155308"/>
        # Note: this is relative to the battlefield x/y/z, but for
        # convenience, could be converted to raw x/y/z for object movement,
        # the goal being to move the ship closer to the player if the
        # sector is being shrunk (assuming ships will also be slower, hence
        # the ship might otherwise not arrive before oxygen runs out).
        self.rescue_ship_offset_node = xml_node.find('.//create_ship[@name="$PickupShip"]/position')
        
        # Absolute position of rescue ship.
        dims = {}
        for attr in ['x','y','z']:
            # Get a string with the $Battlefield.* replaced.
            battle_pos = battlefield_pos_node.get(attr)
            pos_str = self.rescue_ship_offset_node.get(attr)
            pos_str = pos_str.replace(f'$Battlefield.{attr}', battle_pos)
            # Evaluate the expression. Do this manually for safety.
            left, op, right = pos_str.split()
            if op == '-':
                pos = float(left) - float(right)
            elif op == '+':
                pos = float(left) + float(right)
            dims[attr] = pos

        # Set up a fixed position, but link to the original xml node.
        # On update, this will overwrite the x/y/z with absolute values.
        self.position = Position(**dims)
        self.position.xml_node = self.rescue_ship_offset_node

        return
    
    def Update_XML(self):
        # Can update the position normally.
        self.position.Update_XML()
        return
    

class MD_Gamestart(MD_Object):
    '''
    Gamestart position, expected to line up with md script and region pos,
    so rescaled.

    * xml_node
      - Gamestart node.
    '''
    def __init__(self, xml_node):
        super().__init__(xml_node)

        # Try to glue position to generally nearby objects in radar range.
        self.radius = 40000

        self.name = xml_node.get('id')
        location = xml_node.find('./location')
        position = location.find('./position')

        # Get the sector from the location.
        self.sector_name = location.get('sector')
        # Package the position node.
        self.position = Position(position)
        return
    
    def Update_XML(self):
        # Can update the position normally.
        self.position.Update_XML()
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
      - None for the station defaults.
    * sector
      - Sector with this object.
    * zone
      - Zone with this object, if specific to a zone.
    * position
      - Position of this object, or None if undefined.
    * core_range
      - Dict, keyed by 'min' and 'max', holding floats, the min/max multiplier 
        on sector coresize when selecting how far out the object spawns.
      - Only used when position is None.
      - Both position and corerange may be None if this object uses
        the default station corerange.
    * radius
      - Explicit radius of this object.
      - Defaults to be similar to a zone, eg. 5km.
    * scaling_factor
      - Float, stored scaling factor for this object, to be applied
        to the xml during Update_XML.
    '''
    obj_macro_sizes = {
        # Unclear what this one is.
        'landmarks_par_monument_01_macro'     : 20000,
        # Big broken headquarters in a region field.
        # Give a large size so it glues to the region earlier.
        # (The region has an inner radius of 95k, outer of 130k, and this is
        # supposed to be in the center, so make it super huge.)
        'landmarks_gen_old_ringstation_macro' : 100000,
        # Unclear on size of each piece.
        'landmarks_xen_aqueduct_01_macro'     : 10000,
        'landmarks_xen_aqueduct_02_macro'     : 10000,
        'landmarks_xen_aqueduct_03_macro'     : 10000,
        'landmarks_xen_aqueduct_04_macro'     : 10000,
        'landmarks_xen_aqueduct_05_macro'     : 10000,
        'landmarks_xen_aqueduct_06_macro'     : 10000,
        'landmarks_xen_aqueduct_07_macro'     : 10000,
        }

    def __init__(
            self, 
            xml_node
            ):
        self.xml_node = xml_node

        self.name = xml_node.get('id')
        self.macro_name = xml_node.find('./location').get('macro')
        self.sector = None
        self.zone   = None
        self.scaling_factor = None

        # Some of these don't have specific positions, but are randomly
        # placed based on sector size (which should update automatically
        # after sector scaling).
        self.position = None
        pos_node = xml_node.find('./position')
        if pos_node != None:
            self.position = Position(pos_node)
            
        self.core_range = {'min': None, 'max':None}
        range_node = xml_node.find('./location/corerange')
        if range_node != None:
            for key in self.core_range:
                value = range_node.get(key)
                if value:
                    self.core_range[key] = float(value)

        # Radius is unclear; can vary by object.
        # For now, give a decent padding, but many of these are stations.
        self.radius = 5000

        # Selective upsizing based on the object.
        obj_node = xml_node.find('./object')
        if obj_node != None:
            object_macro = xml_node.find('./object').get('macro')
            if object_macro in self.obj_macro_sizes:
                self.radius = self.obj_macro_sizes[object_macro]
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


    def Scale(self, scaling_factor):
        '''
        Set ths scaling factor for this object, and immediately update
        the core range. Should only be called once.
        '''
        self.scaling_factor = scaling_factor
        # -Removed; this didn't work well since god logic creates oversized
        #  zones, and can't fit them well when shrinking. Instead, the
        #  solution is to set newzonechance to 0 and manually add zones.
        if 0:
            self.Scale_Range(scaling_factor)

    def Scale_Range(self, scaling_factor):
        '''
        Apply the scaling to the core range min and max.
        If scaling_factor is > 1, this will do nothing, on the assumption
        the ranges will scale properly with sector coresize (which only
        hits a min when trying to shrink).
        '''
        if scaling_factor >= 1:
            return
        for key, value in self.core_range.items():
            if value:
                self.core_range[key] = value * scaling_factor
        return

    def Update_XML(self):
        if self.position:
            self.position.Update_XML()
            
        # Adjust the range as well.
        range_node = self.xml_node.find('./location/corerange')
        if range_node != None:
            for key, value in self.core_range.items():
                if value:
                    range_node.set(key, '{:.2f}'.format(value))
                                        

        # If this is the default, apply some additional scaling logic.
        scaling_factor = self.scaling_factor
        if self.macro_name == None and scaling_factor and scaling_factor < 1:
            
            # Note: the new zone chance (25%) will still tend to spread
            # out stations when there is room.
            # In theory, can invert the squared scaling factor, for worst
            # case density increase. In practice, that is probably overkill,
            # and can do plain inversion or invert the square root.
            quota_scaling = 1 / (scaling_factor ** 0.5)
            quota_node = self.xml_node.find('.//quota')
            XML_Modify_Int_Attribute(   quota_node, 
                                        'zone', 
                                        quota_scaling, '*')


            # To allow more verticality, adjust the coreboundaryzoneheight.
            # This normally sets an allowed 40km vertical offset at the
            # core boundary (probably based on coresize, eg. min of 425km),
            # with the vertical offset being reduced closer in sector,
            # increased outside (assume linear scaling).
            # Aim is to move this 40km allowance closer inside, to where
            # the new desired boundary is. Eg. if wanted boundary cut
            # in half, can double the height at the original boundary.
            # This may be overdoing it, so taper a bit like above.
            height_scaling = 1 / (scaling_factor ** 0.5)
            location_node = self.xml_node.find('.//location')
            XML_Modify_Int_Attribute(   location_node, 
                                        'coreboundaryzoneheight', 
                                        height_scaling, '*')

            # Note: in testing, adding zones or increasing zone station quota
            # still had a lot of placement failures.
            # This was due to the new_zone_chance trigger not having
            # a fallback when it can't fit a zone.
            # Try decreasing the new zone chance a bunch, eg. to 0%.
            location_node.set('newzonechance', '0')

        return
            





from .. import File_Manager
from ..Common import Flags


@File_Manager.Transform_Wrapper('types/TShields.txt')
def Adjust_Shield_Regen(
    scaling_factor = 1
    ):
    '''
    Adjust shield regeneration rate by changing efficiency values.
    
    * scaling_factor:
      - Multiplier to apply to all shield types.
    '''
    for this_dict in File_Manager.Load_File('types/TShields.txt'):
        if scaling_factor != 1:
            # Grab the shield efficiency, as a float.
            value = float(this_dict['efficiency'])
            new_value = value * scaling_factor
            # Put it back, with 1 decimal place.
            this_dict['efficiency'] = str('{0:.1f}'.format(new_value))

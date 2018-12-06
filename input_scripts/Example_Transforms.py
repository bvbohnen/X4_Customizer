'''
Example for using the Customizer, setting a path to
the X3 directory and running some simple transforms.
'''

# Import all transform functions.
from X4_Customizer import *

Set_Path(
    # Set the path to the X3 installation folder.
    path_to_x3_folder = r'D:\Steam\SteamApps\common\x3 terran conflict',
)

# Speed up interceptors by 50%.
Adjust_Ship_Speed(adjustment_factors_dict = {'SG_SH_M4' : 1.5})

# Increase frigate laser regeneration by 50%.
Adjust_Ship_Laser_Recharge(adjustment_factors_dict = {'SG_SH_M7': 1.5})

# Reduce Out-of-sector damage by 30%.
Adjust_Weapon_OOS_Damage(scaling_factor = 0.7)
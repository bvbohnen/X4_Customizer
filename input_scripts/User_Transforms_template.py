'''
Template file for specifying user's transforms.
When X4 Customizer is launched without an input script specified, 
"User_Transforms.py" will be run by default.

Instructions:
1)  Copy or rename this file to "User_Transforms.py".
2)  Edit the 'path_to_x4_folder' argument in Set_Path to point to the
    X4 installation to be modified.
3)  Call any desired transform functions.
    Some select functions are provided as examples, commented out.
    See documentation for a list of all transforms and their arguments.
4)  Run the transforms using Launch_X4_Customizer.bat.
    Note: this will generate a new cat/dat pair in the x4 folder containing
    the edited files, as well as logging some information into the
    addon/x4_customizer_logs folder under the x4 directory.
    The first run will require a restart of X4 to recognize the
    new cat/dat pair.

To remove transforms, either:
a)  Comment out undesired transforms and rerun the input script.
b)  Run Clean_X4_Customizer.bat.
    This will remove the cat/dat pair, requiring a restart of X4.
'''

# Import all transform functions.
from X4_Customizer import *

Set_Path(
    # Set the path to the X4 installation folder.
    path_to_x4_folder = r'D:\Steam\SteamApps\common\X4 Foundations',
)

# Make seta speed up faster.
#Adjust_Max_Speedup_Rate(4)

# Stop scripts using 'create ship' from accidentally leaving
#  around spacefly swarms (often accumulating in the null sector).
#Prevent_Accidental_Spacefly_Swarms()

# Disable docking music transition when manually requesting to dock.
#Disable_Docking_Music()

# Keep equipment intacts for captured ships.
#Preserve_Captured_Ship_Equipment()

# Add some particles around the ship.
# 10 feels good as a base (10% of vanilla), upscaling by
#  0.5 of the fog amount (up to +25 in heavily fogged sectors).
#Adjust_Particle_Count(
#    base_count = 10,
#    fog_factor = 0.5)

# Swap to safer gate models that don't have protrusions in front that
#  capital ships run into.
#Adjust_Gate_Rings(
#    standard_ring_option = 'use_plain_ring',
#    hub_ring_option = 'use_reversed_hub',
#    )
    
# Reduce OOS damage by 40%.
#Adjust_Weapon_OOS_Damage(scaling_factor = 0.6)
        
# Beef up mosquitos for better intercept.
#Enhance_Mosquito_Missiles()

# Speed up interceptors by 50%.
#Adjust_Ship_Speed(adjustment_factors_dict = {'SG_SH_M4' : 1.5})

# Increase frigate laser regeneration by 50%.
#Adjust_Ship_Laser_Recharge(adjustment_factors_dict = {'SG_SH_M7': 1.5})

# Reduce Out-of-sector damage by 30%.
#Adjust_Weapon_OOS_Damage(scaling_factor = 0.7)
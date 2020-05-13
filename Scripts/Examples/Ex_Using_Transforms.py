'''
Example for using the Customizer, setting a path to
the X4 directory and running some simple transforms.
'''

# Import all transform functions.
from Plugins import *

# This could also be done in settings.json or through the gui.
Settings(
    # Set the path to the X4 installation folder.
    path_to_x4_folder   = r'C:\Steam\SteamApps\common\X4 Foundations',

    # Set the path to the user documents folder, if the auto-find
    # doesn't work. Commented out here.
    #path_to_user_folder = r'C:\Users\charname\Documents\Egosoft\X4\12345678',

    # Optionally change the output extension name. Default is "x4_customizer".
    extension_name = 'x4_customizer'
    )

# Reduce mass traffic and increase military jobs.
Adjust_Job_Count(
    ('id   masstraffic*', 0.5),
    ('tags military'   , 1.3)
    )

# Make weapons in general, and turrets in particular, better.
Adjust_Weapon_Damage(
    ('tags turret standard'   , 2),
    ('*'                      , 1.2),
    )
Adjust_Weapon_Shot_Speed(
    ('tags turret standard'   , 2),
    ('*'                      , 1.2),
    )

# Get csv and html documentation with weapon changes.
Print_Weapon_Stats()

# Write modified files.
Write_To_Extension()
'''
Example for using the Customizer, setting a path to
the X4 directory and running some simple transforms.
'''

# Import all transform functions.
from X4_Customizer import *

Settings(
    # Set the path to the X4 installation folder.
    path_to_x4_folder   = r'C:\Steam\SteamApps\common\X4 Foundations',
    # Set the path to the user documents folder.
    path_to_user_folder = r'C:\Users\charname\Documents\Egosoft\X4\12345678',
    # Switch output to be in the user documents folder.
    output_to_user_extensions = True,
    )

# Reduce mass traffic and increase military jobs.
Adjust_Job_Count(
    ('id','masstraffic', 0.5),
    ('tag','military', 2)
    )

# Write modified files.
Write_To_Extension()
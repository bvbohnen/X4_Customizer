'''
Template file for specifying user's transforms through the Run_Script option.
When Run_Script.bat launched without an input script specified, 
"User_Transforms.py" will be run by default.

Note: the GUI added in v1.2 automates some of these steps.

Instructions:
1)  Copy or rename this file to "Default_Script.py".
2)  Edit the 'path_to_x4_folder' argument in Set_Path to point to the
    X4 installation to be modified.
3)  Call any desired transform functions.
    Some select functions are provided as examples, commented out.
    See documentation for a list of all transforms and their arguments.
4)  Run the transforms using Run_Script.bat, or using the
    python source as "python Framework/Main.py".
    Note: this will generate a new extension containing the
    edited files.

To remove transforms, either:
a)  Comment out undesired transforms and rerun the input script.
b)  Run Clean_Script.bat.
c)  Using the python source, run 
    "python Framework/Main.py -clean".
d)  Manually delete the generated extension.
'''

# Import all transform functions.
from Plugins import *

# Apply paths and other settings.
# This could also be done in settings.json.
Settings(
    # Set the path to the X4 installation folder.
    path_to_x4_folder   = r'C:\Steam\SteamApps\common\X4 Foundations',
    # Set the path to the user documents folder.
    path_to_user_folder = r'C:\Users\charname\Documents\Egosoft\X4\12345678',
    # Optionally switch output to be in the user documents folder.
    #output_to_user_extensions = True,
    )

# Fill in transforms below.
# A few samples are commented out.

## Reduce mass traffic and increase military jobs.
#Adjust_Job_Count(
#    ('id   masstraffic*', 0.5),
#    ('tags military'   , 1.3)
#    )

## Make weapons in general, and turrets in particular, better.
#Adjust_Weapon_Damage(
#    ('tags turret standard'   , 2),
#    ('*'                      , 1.2),
#    )
#Adjust_Weapon_Shot_Speed(
#    ('tags turret standard'   , 2),
#    ('*'                      , 1.2),
#    )


# Write transform modified files when done.
# This can be commented out if not using transforms.
Write_To_Extension()
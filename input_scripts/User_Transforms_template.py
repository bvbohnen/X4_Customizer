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
    Note: this will generate a new extension containing the
    edited files.

To remove transforms, either:
a)  Comment out undesired transforms and rerun the input script.
b)  Run Clean_X4_Customizer.bat.
    This will remove the cat/dat pair, requiring a restart of X4.
'''

# Import all transform functions.
from X4_Customizer import *

# Set the path to the X4 installation folder.
Set_Path( path_to_x4_folder = r'C:\Steam\SteamApps\common\X4 Foundations' )

# Fill in transforms below.

## Reduce mass traffic and increase military jobs.
#Adjust_Job_Count(
#    ('id','masstraffic', 0.5),
#    ('tag','military', 2)
#    )

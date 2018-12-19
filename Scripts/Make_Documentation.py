'''
This script calls the documenation plugins to print out
information based on the current game state (with extensions appplied).

TODO: flesh out or remove.
'''
# Import all transform functions.
from Plugins import *

Settings(
    path_to_x4_folder = r'C:\Steam\SteamApps\common\X4 Foundations',
    # Include the current output extension in the check.
    Settings.ignore_output_extension = False,
    )

Print_Weapon_Stats()

'''
These transforms are those used by the author.
'''

# Import all transform functions.
from Plugins import *

Settings(
    path_to_x4_folder = r'C:\Steam\SteamApps\common\X4 Foundations',
    # Keep output in loose files, to double check them.
    output_to_catalog = False,
    )


# Toy around with job counts.
Adjust_Job_Count(
    ('id','masstraffic', 0.5),
    ('tag','military', 2),
    ('tag','miner', 1.5),
    ('faction','argon', 1.2),
    ('*', 1.1) )

# Write modified files.
Write_To_Extension()
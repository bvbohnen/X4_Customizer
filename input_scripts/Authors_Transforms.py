'''
These transforms are those used by the author.
'''

# Import all transform functions.
import X4_Customizer
from X4_Customizer import *

Set_Path(
    path_to_x4_folder = r'C:\Steam\SteamApps\common\X4 Foundations',
)
# Keep output in loose files, to double check them.
# TODO: maybe set this as default for x4, since cats aren't as important
#  as they were in x3.
Settings.output_to_catalog = False

# Toy around with job counts.
Adjust_Job_Count(
    ('id','masstraffic', 0.5),
    ('tag','military', 2),
    ('tag','miner', 1.5),
    ('faction','argon', 1.2),
    ('*', 1.1) )

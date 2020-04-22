'''
Subpackage with all transforms.
'''

from .Director import Adjust_Mission_Rewards
from .Director import Adjust_Mission_Reward_Mod_Chance

from .Exe import Remove_Modified
from .Exe import Remove_Sig_Errors

from .Jobs import Adjust_Job_Count

# Subpackages; these can import all since these already picked out
#  the individual transforms.
#from .Weapon import *
#from .Director import *

from .Map import Scale_Sector_Size

from .Misc import Apply_Live_Editor_Patches

from .Ships import Adjust_Ship_Speed
from .Text import Color_Text

from .Wares import Adjust_Ware_Price_Spread
from .Wares import Adjust_Ware_Prices


from .Weapons import Adjust_Weapon_Damage
from .Weapons import Adjust_Weapon_Fire_Rate
from .Weapons import Adjust_Weapon_Range
from .Weapons import Adjust_Weapon_Shot_Speed

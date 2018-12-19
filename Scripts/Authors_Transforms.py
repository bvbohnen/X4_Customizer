'''
These transforms are those used by the author.
For early versions, these may be filled more with play than
actual good ideas for game modifications.
'''

# Import all transform functions.
from Plugins import *

Settings(
    path_to_x4_folder = r'C:\Steam\SteamApps\common\X4 Foundations',
    # Keep output in loose files, to double check them.
    output_to_catalog = False,
    )


# Prune some mass traffic.
Adjust_Job_Count(('id masstraffic*', 0.5))


# Toy around with small weapons.
Adjust_Weapon_Damage(
    ('tags small standard weapon'   , 2),
    ('*'                            , 1.2),
    )
Adjust_Weapon_Range(
    ('tags small standard weapon'   , 2),
    ('tags missile'                 , 2),
    )
Adjust_Weapon_Shot_Speed(
    ('tags small standard weapon'   , 2),
    ('tags missile'                 , 2),
    )
Adjust_Weapon_Fire_Rate(
    ('tags small standard weapon'   , 2),
    ('tags missile'                 , 2),
    )
Print_Weapon_Stats()


# Reduce general price spread on wares, to reduce trade profit.
Adjust_Ware_Price_Spread(0.5)
# Reduce the prices on inventory items, since they are often
# obtained for free.
Adjust_Ware_Prices(
    ('container inventory'         , 0.5) ) 
Print_Ware_Stats()

# Reduce generic mission rewards somewhat heavily.
Adjust_Mission_Rewards(0.2)

# Write modified files.
Write_To_Extension()

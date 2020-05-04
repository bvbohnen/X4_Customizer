'''
These transforms are those used by the author.
For early versions, these may be filled more with play than
actual good ideas for game modifications.
'''
# Import all transform functions.
from Plugins import *

# Adjust the exe to point at a saved copy, since X4.exe will be symlinked
# to the customized version.
Settings(X4_exe_name = 'X4_nonsteam.exe')
#Settings(X4_exe_name = 'X4.vanilla.exe')

Apply_Live_Editor_Patches()

#@Transform_Wrapper()
#def Test():
#    assert False
#    return
#
#Test()

# Exe edits.
# Disabled when not refreshing; the prior produced exe will not
# be deleted by the customizer.
if 0:
    Remove_Sig_Errors()
    Remove_Modified()

# Prune some mass traffic.
# (There may also be a way to adjust this in-game now.)
Adjust_Job_Count(('id masstraffic*', 0.5))

# Testing adjusting jobs globally.
#Adjust_Job_Count(('*', .0001))

# Slow down ai scripts a bit for better fps.
# Note on 20k ships save 300km out of vision:
#  1x/1x: 37 fps (vanilla)
#  2x/4x: 41 fps (default args)
#  4x/8x: 46 fps
#Increase_AI_Script_Waits(multiplier = 4, seta_multiplier = 8)

# Toy around with coloring.
# This is Pious Mists.
# Color_Text((20005,3021,'C'))

# Speed up all smaller ships by a bit.
'''
Adjust_Ship_Speed(
    ('class ship_s' , 1.3),
    ('class ship_m' , 1.1),
    )
'''

# Toy around with small weapons.
'''
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
    ('tags small standard weapon'   , 4),
    #('tags missile'                 , 2),
    )
Print_Weapon_Stats()
'''


# Reduce general price spread on wares, to reduce trade profit.
# (Remove for now, until getting a better feel for the game.)
#Adjust_Ware_Price_Spread(0.5)

# Reduce the prices on inventory items, since they are often
# obtained for free.
#Adjust_Ware_Prices(('container inventory', 0.5) ) 
#Print_Ware_Stats()

# Reduce generic mission rewards somewhat heavily.
#Adjust_Mission_Rewards(0.3)
# Make mods more likely from missions.
#Adjust_Mission_Reward_Mod_Chance(3)

# Rescale the sectors.
# -Removed for now; while it works, it requires a new game, and
# so isn't as suitable for sharing with others.
#Scale_Sector_Size(0.4)

# Write modified files.
Write_To_Extension()


'''
Testing setup, for faster game loading and a fast starter ship.
'''
# Import all transform functions.
from Plugins import *

Settings(
    extension_name = 'sn_test_universe',
    generate_sigs = False,
)

# Prune some mass traffic.
Adjust_Job_Count(('id masstraffic*', 0.2))

# Slow down ai scripts a bit for better fps.
#Increase_AI_Script_Waits(
#    oos_multiplier = 2,
#    oos_seta_multiplier = 6,
#    oos_max_wait = 20,
#    iv_multiplier = 1,
#    iv_seta_multiplier = 2,
#    iv_max_wait = 5,
#    include_extensions = False,
#    skip_combat_scripts = False,
#    )

# Lighter job file for quicker testing.
Adjust_Job_Count(('*', .01))

# Speed up paranid warrior start ship for tests.
Set_Ship_Radar_Ranges(('name ship_par_s_fighter_01_a_macro', 50))
Adjust_Ship_Speed(('name ship_par_s_fighter_01_a_macro'    , 10))

# Write modified files.
Write_To_Extension()


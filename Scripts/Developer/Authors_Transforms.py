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


# Exe edits.
# Disabled when not refreshing; the prior produced exe will not
# be deleted by the customizer.
if 0:
    Remove_Sig_Errors()
    Remove_Modified()

# Prune some mass traffic.
# (There may also be a way to adjust this in-game now.)
# Update: "trafficdensity" option added to extra game options mod to help out.
# This might still help with many stations near each other.
Adjust_Job_Count(('id masstraffic*', 0.5))

# Testing adjusting jobs globally.
Adjust_Job_Count(('*', .0001))

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

# Sector/speed rescaling stuff. Requires new game to work well.
if 1:
    # Slow down ai scripts a bit for better fps.
    # Note on 20k ships save 300km out of vision:
    #  1x/1x: 37 fps (vanilla)
    #  2x/4x: 41 fps (default args)
    #  4x/8x: 46 fps
    Increase_AI_Script_Waits(
        oos_multiplier = 2,
        oos_seta_multiplier = 6,
        oos_max_wait = 20,
        iv_multiplier = 1,
        # TODO: is iv wait modification safe?
        iv_seta_multiplier = 2,
        iv_max_wait = 5,
        include_extensions = False,
        skip_combat_scripts = False,
        )
    
    # Disable travel drives for ai.
    Disable_AI_Travel_Drive()

    # Nerf travel speed for player.
    Remove_Engine_Travel_Bonus()

    # Enable seta when not piloting.
    # TODO: couldn't find a way to do this.

    # Reduce weapon rofs; seta impact is a bit much on the faster stuff (6 rps).
    # Prevent dropping below 1 rps.
    Adjust_Weapon_Fire_Rate(
        {'match_any' : ['tags standard weapon','tags standard turret'],  
         'multiplier' : 0.5, 'min' : 1},
        )

    # Retune radars to shorter range, for fps and for smaller sectors.
    Set_Default_Radar_Ranges(
        ship_xl       = 30,
        ship_l        = 30,
        ship_m        = 25,
        ship_s        = 20,
        ship_xs       = 20,
        spacesuit     = 15,
        station       = 30,
        satellite     = 20,
        adv_satellite = 30,
        )
    Set_Ship_Radar_Ranges(
        # Bump scounts back up. 30 or 40 would be good.
        ('type scout'  , 30),
        # Give carriers more stategic value with highest radar.
        ('type carrier', 40),
        )
    
    # Adjust engines to remove the split base speed advantage, and shift
    # the travel drive bonus over to base stats.
    # TODO: think about how race/purpose adjustments multiply; do any engines
    # end up being strictly superior to another?
    Rebalance_Engines(        
        race_speed_mults = {
            'argon'   : {'thrust' : 1,    'boost'  : 1,    'boost_time' : 1   },
            # Slightly better base speed, worse boost.
            'paranid' : {'thrust' : 1.05, 'boost'  : 0.80, 'boost_time' : 0.8 },
            # Fast speeds, short boost.
            'split'   : {'thrust' : 1.10, 'boost'  : 1.20, 'boost_time' : 0.7 },
            # Slower teladi speeds, but balance with long boosts.
            'teladi'  : {'thrust' : 0.95, 'boost'  : 0.90, 'boost_time' : 1.3 },
            },
        purpose_speed_mults = {
            'allround' : {'thrust' : 1,    'boost' : 1,    'boost_time' : 1,    },
            # Combat will be slowest but best boost.
            'combat'   : {'thrust' : 0.9,  'boost' : 1.2,  'boost_time' : 1.5,  },
            # Travel is fastest, worst boost.
            'travel'   : {'thrust' : 1.1,  'boost' : 0.8,  'boost_time' : 0.8,  },
            },
        )
    
    # Note: with speed rescale, boost ends up being a bit crazy good, with
    # ship overall travel distance coming largely from boosting regularly.
    # Example:
    # - ship speed of 300
    # - vanilla boost mult of 8x, duration of 10s.
    # - boosting moves +21km (24km total vs 3km without boost)
    # - small shield with 10s recharge delay, 9s recharge time.
    # - can boost every 29s.
    # - in 29s: 8.7km from base speed, 21km from boost.
    # AI doesn't use boost for general travel, which breaks immersion when
    # it would be so beneficial.
    # Ideally, boosting would benefit travel less than +20% or so.
    # Cannot change shield recharge delay/rate without other effects.
    # In above example: change boost to only add +2km or so per 29s.
    # - boost mult of 2x, duration of 5s = 2.7km.
    Adjust_Engine_Boost_Duration(1/2)
    Adjust_Engine_Boost_Speed   (1/4)


    # Adjust speeds per ship class.
    # Note: vanilla averages and ranges are:    
    # xs: 130 (58 to 152)
    # s : 328 (71 to 612)
    # m : 319 (75 to 998)
    # l : 146 (46 to 417)
    # xl: 102 (55 to 164)
    # Try clamping variation to within 0.5x (mostly affects medium).
    # TODO: more fine-grain, by purpose (corvette vs frigate, etc.).    
    Rescale_Ship_Speeds(
        # Ignore the python (unfinished).
        {'match_any' : ['name ship_spl_xl_battleship_01_a_macro'], 'skip' : True},
        {'match_all' : ['type  scout' ],  'average' : 500, 'variation' : 0.2},
        {'match_all' : ['class ship_s'],  'average' : 400, 'variation' : 0.25},
        {'match_all' : ['class ship_m'],  'average' : 300, 'variation' : 0.3},
        {'match_all' : ['class ship_l'],  'average' : 200, 'variation' : 0.4},
        {'match_all' : ['class ship_xl'], 'average' : 150, 'variation' : 0.4})
    
    # Rescale the sectors.
    Scale_Sector_Size(
        # Whatever this is set to, want around 0.4 or less at 250 km sectors.
        scaling_factor                     = 0.4,
        scaling_factor_2                   = 0.3,
        transition_size_start              = 200000,
        transition_size_end                = 400000,
        precision_steps                    = 20,
        remove_ring_highways               = True,
        remove_nonring_highways            = False,
        extra_scaling_for_removed_highways = 0.7,
        )
    
    # Miners can struggle to keep up. Increase efficiency somewhat by
    # letting them haul more cargo.
    # Traders could also use a little bump, though not as much as miners
    # since stations are closer than regions.
    Adjust_Ship_Cargo_Capacity(
        {'match_all' : ['purpose  mine' ],  'multiplier' : 2},
        {'match_all' : ['purpose  trade' ], 'multiplier' : 1.5})


# Write modified files.
Write_To_Extension()



__all__ = [
    'Remove_Engine_Travel_Bonus',
    'Adjust_Engine_Boost_Duration',
    'Adjust_Engine_Boost_Speed',
    'Rebalance_Engines',
    ]

from fnmatch import fnmatch
from collections import defaultdict
from Framework import Transform_Wrapper, Plugin_Log
from ..Classes import *
from .Ships import Adjust_Ship_Cargo_Capacity

# TODO: change ship engine mods to swap travel bonuses to something else.
@Transform_Wrapper()
def Remove_Engine_Travel_Bonus():
    '''
    Removes travel mode bonus from all engines by setting the speed multiplier
    to 1 and engage time to 0.
    '''
    database = Database()
    engine_macros = database.Get_Macros('engine_*') + database.Get_Macros('generic_engine_*')
    for macro in engine_macros:
        # -Removed; use dummy values for safety.
        #macro.Remove_Travel()
        macro.Set_Travel_Mult(1)
        macro.Set_Travel_Charge(0)
    database.Update_XML()
    return


def Adjust_Engine_Boost_Duration(multiplier):
    '''
    Adjust the boost time (eg. inverse of shield % drain rate) for all engines.
    '''
    database = Database()
    engine_macros = database.Get_Macros('engine_*') + database.Get_Macros('generic_engine_*')
    for macro in engine_macros:
        value = macro.Get_Boost_Time()
        # Skip if undefined.
        if not value:
            continue
        macro.Set_Boost_Time( value * multiplier)
    database.Update_XML()
    return


def Adjust_Engine_Boost_Speed(multiplier):
    '''
    Adjust the boost speed for all engines.
    '''
    database = Database()
    engine_macros = database.Get_Macros('engine_*') + database.Get_Macros('generic_engine_*')
    for macro in engine_macros:
        value = macro.Get_Boost_Thrust()
        # Skip if undefined.
        if not value:
            continue
        macro.Set_Boost_Thrust(value * multiplier)
    database.Update_XML()
    return



# TODO: ratios per engine size, as the split M travel ratios are wildly
# different than the split L/XL ratios.
@Transform_Wrapper()
def Rebalance_Engines(
        race_speed_mults = {
            'argon'   : {'thrust' : 1,    'boost'  : 1,    'boost_time' : 1,   'travel' : 1    },
            'paranid' : {'thrust' : 1.03, 'boost'  : 1.03, 'boost_time' : 1.2, 'travel' : 0.90 },
            'split'   : {'thrust' : 1.35, 'boost'  : 1.08, 'boost_time' : 1.2, 'travel' : 0.843},
            'teladi'  : {'thrust' : 0.97, 'boost'  : 0.97, 'boost_time' : 1,   'travel' : 0.97 },
            },
        purpose_speed_mults = {
            'allround' : {'thrust' : 1,    'boost' : 1,    'boost_time' : 1,    'travel' : 1    },
            'combat'   : {'thrust' : 1.05, 'boost' : 1.05, 'boost_time' : 1.43, 'travel' : 0.933},
            'travel'   : {'thrust' : 1,    'boost' : 0.75, 'boost_time' : 0.57, 'travel' : 1.33 },
            },
        adjust_cargo = False,
    ):
    '''
    Rebalances engine speed related properties across purposes and maker races.
    Race balance set relative to argon engines of a corresponding size, purpose,
    mark 1. Higher marks receive the same scaling as their mark 1 counterpart.
    Purpose balance set relative to allround engines of a corresponding size
    and mark.

    * race_speed_mults
      - Dict, keyed by race name, with relative  multipliers for engine speed
        properties: 'thrust', 'boost', 'travel'.
      - Relative to corresponding argon engines.
      - Set to None to disable race rebalancing.
      - Defaults tuned to vanilla medium mark 1 combat engines, and will
        nearly reproduce the vanilla medium engine values (with discrepencies
        for other sizes):
        ```
        race_speed_mults = {
            'argon'   : {'thrust' : 1,    'boost'  : 1,    'boost_time' : 1,   'travel' : 1    },
            'paranid' : {'thrust' : 1.03, 'boost'  : 1.03, 'boost_time' : 1.2, 'travel' : 0.90 },
            'split'   : {'thrust' : 1.35, 'boost'  : 1.08, 'boost_time' : 1.2, 'travel' : 0.843},
            'teladi'  : {'thrust' : 0.97, 'boost'  : 0.97, 'boost_time' : 1,   'travel' : 0.97 },
            }
        ```
    * purpose_speed_mults
      - Dict, keyed by engine purpose name, with relative  multipliers for
        engine speed properties: 'thrust', 'boost', 'travel'.
      - Purposes are 'combat', 'allround', and 'travel'.
      - Set to None to disable purpose rebalancing.
      - Defaults tuned to vanilla medium mark 1 argon engines, and will
        nearly reproduce the vanilla medium engine values (with discrepencies
        for other sizes):
        ```
        purpose_speed_mults = {
            'allround' : {'thrust' : 1,    'boost'  : 1,    'boost_time' : 1,    'travel' : 1    },
            'combat'   : {'thrust' : 1.05, 'boost'  : 1,    'boost_time' : 0.89, 'travel' : 1.43 },
            'travel'   : {'thrust' : 1,    'boost'  : 0.75, 'boost_time' : 1.33, 'travel' : 0.57 },
            }
        ```
    * adjust_cargo
      - Bool, if True then trader and miner ship cargo bays will be adjusted in
        inverse of the ship's travel thrust change, to maintain roughly the
        same transport of cargo/time. Assumes trade ships spend 50% of their
        time in travel mode, and mining ships spend 10%.
      - Defaults False.
      - May cause oddities when applied to an existing save.
    '''
    '''

    Notes:
    mk2 engines cost 5x more than mk1, with 21% more speed.
    mk3 engines cost 5x more than mk2, with 11% more speed.
    mk3 engines cost 25x more than mk1, with 34% more speed.

    Medium combat mk1, thrust / boost / travel / boost duration (as % vs arg):
        arg: 1052 / 8   / 8 / 10 ( 1    / 1    / 1     / 1  )
        kha: 1400 / 4   / 7 /  6 ( 1.33 / 0.66 / 1.16  / 0.6)
        par: 1084 / 8   / 7 / 12 ( 1.03 / 1.03 / 0.90  / 1.2)
        spl: 1420 / 6.4 / 5 / 12 ( 1.35 / 1.08 / 0.843 / 1.2)
        tel: 1021 / 8   / 8 / 10 ( 0.97 / 0.97 / 0.97  / 1  )
        xen: 1286 / 8   / 8 /  8 ( 1.22 / 1.22 / 1.22  / 0.8)
    (Prices are about the same, 16k all but 15k split.)

    Note: in practice, the above is pretty accurate across engines with
    the exception of split travel drives, which are significantly slower
    in l and xl (0.52), slightly slower in other M and S engines.
    The base and boost speeds are pretty exact.
    TODO: maybe per-size multipliers, to recreate vanilla.

    Note: large/xl has no combat engine, to avoid using combat as center point.
    Medium arg mk1, thrust / boost / travel / boost duration, (as % vs allrnd):
        alr: 1002 / 8   / 9  / 7  ( 1    / 1    / 1     / 1    )
        cbt: 1052 / 8   / 8  / 10 ( 1.05 / 1.05 / 0.933 / 1.43 )
        trv: 1002 / 6   / 12 / 4  ( 1    / 0.75 / 1.33  / 0.57 )
    '''
    database = Database()
    engine_macros = database.Get_Macros('engine_*') + database.Get_Macros('generic_engine_*')

    # Match up names of properties to engine get/set methods.
    property_gets = {
        'thrust'     : lambda e: getattr(e, 'Get_Forward_Thrust')(),
        'boost'      : lambda e: getattr(e, 'Get_Boost_Thrust'  )(),
        'travel'     : lambda e: getattr(e, 'Get_Travel_Thrust' )(),
        'boost_time' : lambda e: getattr(e, 'Get_Boost_Time'    )(),
        }
    property_sets = {
        # Forward thrust changes will also rescale reverse thrust.
        'thrust'     : lambda e,v: getattr(e, 'Set_Forward_Thrust_And_Rescale')(v),
        'boost'      : lambda e,v: getattr(e, 'Set_Boost_Thrust'  )(v),
        'travel'     : lambda e,v: getattr(e, 'Set_Travel_Thrust' )(v),
        'boost_time' : lambda e,v: getattr(e, 'Set_Boost_Time'    )(v),
        }

    # Classify the engines in a heavily nested dict, list at the bottom.
    # Only expect one entry at the bottom list, but mods might add more.
    # First versions is designed for race balancing.
    size_purpose_mark_race_engines = defaultdict(
                                        lambda: defaultdict(
                                            lambda: defaultdict(
                                                lambda: defaultdict(list))))
    # Second version is designed for purpose balancing.
    size_race_mark_purpose_engines = defaultdict(
                                        lambda: defaultdict(
                                            lambda: defaultdict(
                                                lambda: defaultdict(list))))

    for macro in engine_macros:
        mk      = macro.Get_mk()
        race    = macro.Get_makerrace()
        purpose = macro.Get_Purpose()
        size    = macro.Get_Size()

        # Skip if any entry missing.
        if not size or not purpose or not race or not mk:
            continue
        # Store it.
        size_purpose_mark_race_engines[size][purpose][mk][race].append(macro)
        size_race_mark_purpose_engines[size][race][mk][purpose].append(macro)

    # Record originals for debug.
    orig_engine_speeds = defaultdict(dict)


    # Reuse this code between race and purpose rebalance.
    for mode, group_speed_mults, nested_engine_dict in [
        ('race'   , race_speed_mults   , size_purpose_mark_race_engines),
        ('purpose', purpose_speed_mults, size_race_mark_purpose_engines)
        ]:
        # Skip if no adjustments specified.
        if group_speed_mults == None:
            continue

        # Work through each group that will be balanced.
        for size, subdict in nested_engine_dict.items():
            for unused, subsubdict in subdict.items():

                # There is an issue with mk4 engines: there are no references
                #  in either case: argon or allround.
                # So, break this into two stages.
                # Stage 1: search through marks until finding a ref (probably
                # mk1), determine scaling multipliers per race/purpose and
                # engine property.
                # Stage 2: loop again, applying the above multipliers.

                # Gather multipliers.
                group_prop_mults = defaultdict(dict)
                for mk, group_engines in sorted(subsubdict.items()):

                    # Pick out the argon/allround engine (or sample the first).
                    base_engines = group_engines['argon' if mode=='race' else 'allround']
                    # Skip if not found.
                    if not base_engines:
                        continue
                    base_engine = base_engines[0]

                    # Pick out base properties.
                    base_values = {}
                    for prop, get in property_gets.items():
                        base_values[prop] = get(base_engine)
                
                    # Check the other group engines.
                    for group, speed_mults in group_speed_mults.items():
                        if not group_engines[group]:
                            continue

                        # Sample the first engine.
                        engine = group_engines[group][0]

                        # Go through properties.
                        for prop, get in property_gets.items():
                            # Skip properties without scalings, or just at 1x.
                            if prop in speed_mults and speed_mults[prop] != 1:
                                # Ratio is between actual value, and wanted value.
                                value  = get(engine)
                                wanted = base_values[prop] * speed_mults[prop]
                                group_prop_mults[group][prop] = wanted / value
                            

                # Apply the multipliers.
                for mk, group_engines in subsubdict.items():

                    for group, engines in group_engines.items():
                        prop_mults = group_prop_mults[group]
                        for engine in engines:

                            # Go through properties.
                            for prop, get in property_gets.items():
                                # Skip if no mult was found.
                                if prop not in prop_mults:
                                    continue

                                orig = get(engine)
                                # Record the unmodified for debug.
                                # Only do this when first seen.
                                if prop not in orig_engine_speeds[engine]:
                                    orig_engine_speeds[engine][prop] = orig

                                mult = prop_mults[prop]
                                new = orig * mult
                                # Write it back.
                                property_sets[prop](engine, new)


    # Printout results.
    lines = ['\nRebalance_Engines:']
    for size, subdict in sorted(size_purpose_mark_race_engines.items()):
        for purpose, subsubdict in sorted(subdict.items()):
            for mk, race_engines in sorted(subsubdict.items()):

                # Sort engines by name.
                name_engine_dict = {}
                for engines in race_engines.values():
                    for engine in engines:
                        if engine in orig_engine_speeds:
                            name_engine_dict[engine.Get_Game_Name()] = engine

                for name, engine in sorted(name_engine_dict.items()):
                    line = f'{name:<30} : '
                    not_first = False
                    for prop, get in property_gets.items():
                        # Note: original is not recorded if this value
                        # was not changed.
                        orig = orig_engine_speeds[engine].get(prop)
                        new  = get(engine)
                        if orig == None:
                            # TODO: maybe indicate equivelence below.
                            orig = new

                        line += '{}{:<6}: {:6.0f} -> {:6.0f}'.format(
                            ' , ' if not_first else '',
                            prop,
                            orig,
                            new,
                            )
                        not_first = True
                    lines.append(line)

    Plugin_Log.Print('\n'.join(lines) + '\n')


    # Load all ships, categorize by race and size, check the engine
    # travel speed change (original to new), and rescale the ship cargo
    # for mine/trade to balance it somewhat.
    # TODO: maybe scrap this in favor of a ship transport rate balancer
    # that can run after this and similar transforms.
    if adjust_cargo:
        ship_macros = database.Get_Ship_Macros()

        # Ships don't spend all of their time in travel mode.
        # As a quick estimate, assume traders spend 50%, miners 10%.
        purpose_travel_ratio_dict = {'mine' : 0.1, 'trade' : 0.5}
        # Prep rules to send to Adjust_Ship_Cargo_Capacity.
        cargo_scaling_rules = []

        for ship in ship_macros:
            purpose = ship.Get_Primary_Purpose()
            if purpose not in purpose_travel_ratio_dict:
                continue

            # Look up the engine speeds.
            engine = ship.Select_Engine(engine_macros = engine_macros)
            # If no engine was found skip; something weird happened.
            if not engine:
                continue
            # If this engine wasn't modified, skip.
            if engine not in orig_engine_speeds:
                continue

            # Add the base and bonus thrusts.
            orig = orig_engine_speeds[engine]['thrust'] + orig_engine_speeds[engine]['travel']
            new = engine.Get_Forward_Thrust() + engine.Get_Travel_Thrust()
            speed_ratio = new / orig

            # Calc the esimated overall trip time ratio.
            # <1 means the ship takes less time, and should hold less cargo.
            ratio = purpose_travel_ratio_dict[purpose]
            trip_time_ratio = (1 - ratio) + ratio * orig / new

            cargo_scaling_rules.append({
                'match_all' : [f'name {ship.name}'],
                'multiplier': trip_time_ratio,
                })

        Adjust_Ship_Cargo_Capacity(*cargo_scaling_rules)

    database.Update_XML()
    return


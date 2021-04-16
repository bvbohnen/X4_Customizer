
__all__ = [
    'Rescale_Ship_Speeds',
    'Adjust_Ship_Cargo_Capacity',
    ]

from fnmatch import fnmatch
import math
from collections import defaultdict
from Framework import Transform_Wrapper, Plugin_Log
from ...Classes import *
from ..Support import Fill_Defaults, Group_Objects_To_Rules
from .Shared import *

# TODO: support auto-scaling of ship cargo capacities for traders, and
# maybe for miners (perhaps to a lesser extent, since they spend part
# of their time gathering ore, particularly large ships using drones).
@Transform_Wrapper(shared_docs = doc_matching_rules)
def Rescale_Ship_Speeds(
        *scaling_rules
    ):
    '''
    Rescales the speeds of different ship classes, centering on the give
    target average speeds. Ships are assumed to be using their fastest race
    engines. Averaged across all ships of the rule match.

    Cargo capacity of traders and miners is adjusted to compensate for
    speed changes, so they move a similar amount of wares. If multiple
    ships use the same cargo macro, it is adjusted by an average of
    their speed adjustments.
    
    Args are one or more dictionaries with these fields, where matching
    rules are applied in order, with a ship being grouped by the first
    rule it matches:

    * average
      - Float, the new average speed to adjust to.
      - If None, keeps the original average.
    * variation
      - Float, less than 1, how much ship speeds are allowed to
        differ from the average relative to the average.
      - If None, keeps the original variation.
      - If original variation is less than this, it will not be changed.
      - Only applies strictly to 90% of ships; 10% are treated as outliers,
        and will have their speed scaled similarly but will be outside
        this band.
      - Eg. 0.5 means 90% of ships will be within +/- 50% of
        their group average speed.
    * match_any
      - List of matching rules. Any ship matching any of these is included,
        if not part of match_none.
    * match_all
      - List of matching rules. Any ship matching all of these is included,
        if not part of match_none.
    * match_none
      - List of matching rules. Any ship matching any of these is excluded.
    * use_arg_engine
      - Bool, if True then Argon engines will be assumed for all ships
        instead of their faction engines.
    * use_split_engine
      - Bool, if True then Split engines will be assumed.
      - This will tend to give high estimates for ship speeds, eg. mk4 engines.
    * skip
      - Optional, bool, if True then this group is not edited.
      - Can be used in early matching rules to remove ships from all later
        matching rules.
        
    Example:
    ```
    Rescale_Ship_Speeds(
        {'match_any' : ['name ship_spl_xl_battleship_01_a_macro'], 'skip' : True},
        {'match_all' : ['type  scout' ],  'average' : 500, 'variation' : 0.2},
        {'match_all' : ['class ship_s'],  'average' : 400, 'variation' : 0.5},
        {'match_all' : ['class ship_m'],  'average' : 300, 'variation' : 0.5},
        {'match_all' : ['class ship_l'],  'average' : 200, 'variation' : 0.5},
        {'match_all' : ['class ship_xl'], 'average' : 150, 'variation' : 0.5})
    ```
    '''
    '''
    Note:
    Vanilla ship speeds have these approximate averages (race engines):
    xs: 130 (58 to 152)
    s : 328 (71 to 612)
    m : 319 (75 to 998)
    l : 146 (46 to 417)
    xl: 102 (55 to 164)

    Split ships exaggerate the high end, eg. alligator(gas) hitting 998.
    The xs includes boarding pods (29 speed), drones, mass traffic.


    TODO: option to also bring down variance? Important to keep the ships
    in tighter bands by class.
    '''
    # Polish the scaling rules with defaults.
    Fill_Defaults(scaling_rules, {
        'average'          : None,
        'variation'        : None,
        'use_arg_engine'   : False,
        'use_split_engine' : False,
        })

    database = Database()
    ship_macros = database.Get_Ship_Macros()
    engine_macros = database.Get_Macros('engine_*') + database.Get_Macros('generic_engine_*')
    # Remove mk4 engines, since they throw things off a bit.
    engine_macros = [x for x in engine_macros if x.Get_mk() != '4']
    
    # Group the ships according to rules.
    Group_Objects_To_Rules(ship_macros, scaling_rules, Is_Match)

    # Gather speed mult factors for all ships, to be used later to adjust cargo.
    ship_mults = {}
    
    # Loop over the rule/groups.
    for rule in scaling_rules:
        if rule['skip']:
            continue
        # Unpack the fields for convenience.
        ship_macros      = rule['matches']
        average          = rule['average']
        variation        = rule['variation']
        use_arg_engine   = rule['use_arg_engine']
        use_split_engine = rule['use_split_engine']


        # If neither average or variation given, do nothing.
        if average == None and variation == None:
            return

        # If there were no matches, skip.
        if not ship_macros:
            continue

        # Select an engine for every ship, to use in speed estimation.
        for ship in ship_macros:
            ship.Select_Engine(
                engine_macros = engine_macros,
                owner = 'argon' if use_arg_engine else 'split' if use_split_engine else None,
                )
        # TODO: maybe filter out 0 speed ships here, instead of below.

        # Collect ship speeds into a dict.
        ship_orig_speeds = {}
        for ship in ship_macros:
            ship_orig_speeds[ship] = ship.Get_Speed()
        orig_speeds = [x for x in ship_orig_speeds.values() if x > 0]
        orig_avg = sum(orig_speeds) / len(orig_speeds)
        

        # Figure out adjustment based on original and wanted averages.
        if average != None:
            # Collect speeds of the ships. Ignore 0s for later stats.
            # Reuse stored values above.        
            ratio = average / orig_avg
            # Apply this ratio to all individual ships.
            for ship in ship_macros:
                ship.Adjust_Speed(ratio)


        # Variation adjustment will be per-ship.
        if variation != None:
            # Gather the speeds of each ship (maybe with above average change).
            ship_speed_dict = {}
            for ship in ship_macros:
                ship_speed_dict[ship] = ship.Get_Speed()

            # Compute current average, again tossing 0s.
            speeds = [x for x in ship_speed_dict.values() if x > 0]
            current_avg = sum(speeds) / len(speeds)

            # Gather the differences in ship speeds from average, per ship,
            # ignoring those with 0 speed.
            ship_delta_dict = {}
            for ship in ship_macros:
                if ship_speed_dict[ship] != 0:
                    ship_delta_dict[ship] = abs(ship_speed_dict[ship] - current_avg)

            # Sort the ships by deltas.
            sorted_ships = [k for k,v in sorted(ship_delta_dict.items(), key = lambda x: x[1])]

            # Get the ship count that covers 90% of the ships.
            ship_count_90p = math.ceil(len(sorted_ships) * 0.9)
        
            # From the above, can pick the ship at the 90% cuttoff.
            # Eg. if 10 ships cover 90%, then the 10th is the cuttoff (index 9).
            cuttoff_ship = sorted_ships[ship_count_90p - 1]
            cuttoff_delta = ship_delta_dict[cuttoff_ship]

            # Knowing this original delta, can determine the rescaling of deltas
            # that is needed to match the wanted variation.
            ratio = (variation * current_avg) / cuttoff_delta

            # Only continue if tightening the range.
            if ratio < 1:
                # For each ship, rescale its delta, and translate back into a 
                # new ship speed.
                for ship, orig_delta in ship_delta_dict.items():
                    orig_speed = ship_speed_dict[ship]
                    new_delta = orig_delta * ratio

                    # Handle based on if this was faster or slower than average.
                    if orig_speed > current_avg:
                        new_speed = current_avg + new_delta
                    else:
                        # TODO: safety clamp to something reasonable, if the
                        # variation was set too high.
                        new_speed = current_avg - new_delta
                        if new_speed <= 0:
                            raise Exception('Variation set too large; ship speed went negative')

                    # Apply back this speed.
                    speed_ratio = new_speed / orig_speed
                    ship.Adjust_Speed(speed_ratio)
                    

        # Report changes.
        # List pairing ship macro to display name.
        # Note: names can be reused.
        ship_name_macro_list = [(x, x.Get_Game_Name()) for x in ship_macros]
        lines = ['\nRescale_Ship_Speeds:']
        new_speeds = []

        # Loop over sorted names.
        for ship, game_name in sorted(ship_name_macro_list, key = lambda x: x[1]):

            orig_speed = ship_orig_speeds[ship]
            new_speed = ship.Get_Speed()
            if new_speed > 0:
                new_speeds.append(new_speed)

            # Record the multiplier.
            # If a ship is in multiple groups, multipliers will stack.
            # (Note: currently don't expect ships to be in multiple groups.)
            if orig_speed > 0:
                if ship not in ship_mults:
                    ship_mults[ship] = 1
                ship_mults[ship] *= new_speed / orig_speed

            lines.append('  {:<65}: {:>3.0f} -> {:>3.0f} ( {:>2.1f}% ) (using {})'.format(
                f'{game_name} ({ship.name})',
                orig_speed,
                new_speed,
                new_speed / orig_speed * 100 if orig_speed > 0 else 0,
                ship.engine_macro.Get_Game_Name(),
                ))

        # Also give some overall stats.
        new_average = sum(new_speeds) / len(new_speeds)
        lines.append(f' Orig average: {orig_avg:.0f} ({min(orig_speeds):.0f} to {max(orig_speeds):.0f})')
        lines.append(f' New  average: {new_average:.0f} ({min(new_speeds):.0f} to {max(new_speeds):.0f})')
        Plugin_Log.Print('\n'.join(lines) + '\n')


    # Adjust ship storage as well.
    storage_macro_mults = defaultdict(list)

    for ship, speed_mult in ship_mults.items():
        # If a trade or mining ship, adjust cargo.
        purpose = ship.Get_Primary_Purpose()
        if purpose in ['mine', 'trade']:

            # Full adjustment to traders.
            if purpose == 'trade':
                cargo_mult = (1 / speed_mult)
                tags = ['container']

            # Reduced adjustment to miners, since they spend more time
            # collecting rocks or waiting on drones.
            # TODO: maybe just full adjustment as well.
            if purpose == 'mine':
                cargo_mult = (1 / speed_mult)
                cargo_mult = 1 + (cargo_mult - 1) * 0.75
                tags = ['solid', 'liquid']

            for storage in ship.Get_Storage_Macros():
                # Filter unwanted storage types (not expected to catch anything
                # in vanilla).
                storage_tags = storage.Get_Tags()
                if not any(x in storage_tags for x in tags):
                    continue
                # Record the multiplier.
                storage_macro_mults[storage].append(cargo_mult)


    # Adjust cargo bays by average mult.
    # Report adjustments.
    # TODO: reuse Adjust_Ship_Cargo_Capacity somehow.
    # TODO: maybe scrap this in favor of a ship transport rate balancer
    # that can run after this and similar transforms.
    lines = ['Storage adjustments:']
    for storage, mults in storage_macro_mults.items():

        multiplier = sum(mults) / len(mults)
        volume = storage.Get_Volume()
        new_volume = int(volume * multiplier)

        # Round a bit to look nicer in game.
        if new_volume > 10000:
            new_volume = round(new_volume / 100) * 100
        else:
            new_volume = round(new_volume / 10) * 10

        storage.Set_Volume(new_volume)
        lines.append(f'  {storage.name:<45} : {volume:<6} -> {new_volume:<6}')
            
    if len(lines) > 1:
        Plugin_Log.Print('\n'.join(lines[0:1] + sorted(lines[1:])) + '\n')

    # Apply the xml changes.
    database.Update_XML()

    return


# TODO: not a rescaling, just adjustment, but this uses database stuff; think
# renaming modules based on database/not-database.
@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Ship_Cargo_Capacity(
        *scaling_rules
    ):
    '''
    Adjusts the cargo capacities of matching ships.  If multiple ships
    use the same storage macro, it is modified by an average of the
    ship multipliers.
    
    Args are one or more dictionaries with these fields, where matching
    rules are applied in order, with a ship being grouped by the first
    rule it matches:

    * multiplier
      - Float, how much to multiply current cargo capacity by.
    * match_any
      - List of matching rules. Any ship matching any of these is included,
        if not part of match_none.
    * match_all
      - List of matching rules. Any ship matching all of these is included,
        if not part of match_none.
    * match_none
      - List of matching rules. Any ship matching any of these is excluded.
    * cargo_tag
      - Optional, tag name of cargo types to modify.
      - Expected to be one of: 'solid', 'liquid', 'container'.
      - If not given, all cargo types are modified.
    * skip
      - Optional, bool, if True then this group is not edited.
      - Can be used in early matching rules to remove ships from all later
        matching rules.
        
    Example:
    ```
    Adjust_Ship_Cargo_Capacity(
        {'match_all' : ['purpose mine'],  'multiplier' : 2,},
        {'match_all' : ['purpose trade'], 'multiplier' : 1.5},
        )
    ```
    '''
    '''
    This one is tricky, since cargo is part of a separate storage macro.
    This macro needs to be looked up for each ship, along with the
    wanted multiplier.

    Since ships can share a storage macro, first pass will find multipliers 
    associated with each macro, second pass will resolve conflicts and make 
    changes.
    '''
    # Polish the scaling rules with defaults.
    Fill_Defaults(scaling_rules, {
        'multiplier' : 1,
        'cargo_tag'  : None,
        })

    # Load the ships.
    database = Database()
    ship_macros = database.Get_Ship_Macros()

    # Group the ships according to rules.
    Group_Objects_To_Rules(ship_macros, scaling_rules, Is_Match)
    

    # Ships in different rules might use the same storage; average
    # then together.
    storage_macro_mults = defaultdict(list)

    # Loop over the rule/groups.
    for rule in scaling_rules:
        if rule['skip'] or rule['multiplier'] == 1:
            continue
        ship_macros = rule['matches']
        multiplier  = rule['multiplier']
        cargo_tag   = rule['cargo_tag']

        # Pass over them, collecting storage units.
        for ship in ship_macros:
            for storage in ship.Get_Storage_Macros():
                # Skip if not of the right type.
                if cargo_tag and cargo_tag not in storage.Get_Tags():
                    continue
                # Record the multiplier.
                storage_macro_mults[storage].append(multiplier)


    lines = ['Storage adjustments:']
    # Rescale them all.
    for storage, mults in storage_macro_mults.items():

        multiplier = sum(mults) / len(mults)
        volume = storage.Get_Volume()
        new_volume = int(volume * multiplier)
                    
        # Round a bit to look nicer in game.
        if new_volume > 10000:
            new_volume = round(new_volume / 100) * 100
        else:
            new_volume = round(new_volume / 10) * 10

        storage.Set_Volume(new_volume)
        lines.append(f'  {storage.name:<45} : {volume:<6} -> {new_volume:<6}')
            
    if len(lines) > 1:
        Plugin_Log.Print('\n'.join(lines[0:1] + sorted(lines[1:])) + '\n')
        
    # Apply the xml changes.
    database.Update_XML()
    return


def Is_Match(ship, match_all = None, match_any = None, match_none = None, **kwargs):
    '''
    Checks a ship macro against the given rules, and returns True if a match,
    else False.

    * ship
      - Ship macro object.
    * match_all
      - List of match rules (tuple of key, value) that must all match.
    * match_any
      - List of match rules of which any need to match.
    * match_none
      - List of match rules that must all mismatch.
    '''
    # Look up properties of interest.
    name = ship.name
    class_name = ship.class_name
    type = ship.Get_Ship_Type()
    purpose = ship.Get_Primary_Purpose()

    # Check the matching rules.
    # match_none failures first, then match_all failures, then match_any
    # successes.
    for rules in [match_none, match_all, match_any]:
        # Skip if not given.
        if not rules:
            continue

        for rule in rules:
            key, value = rule.split(' ', 1)
            # Sometimes there may be excess spaces.
            key = key.strip()
            value = value.strip()
            if((key == '*')
            or (key == 'name'    and fnmatch(name, value))
            or (key == 'class'   and class_name == value)
            or (key == 'type'    and type == value)
            or (key == 'purpose' and purpose == value)
            ):
                # If match_none, fail.
                if rules is match_none:
                    return False
                # If match_any, direct pass.
                elif rules is match_any:
                    return True
            else:
                # If match_all, direct fail on a mismatch.
                if rules is match_all:
                    return False

    # If here, assuming no match_any was given, assume match, else mismatch.
    if match_any:
        return False
    return True



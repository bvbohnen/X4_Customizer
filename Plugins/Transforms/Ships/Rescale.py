
__all__ = [
    'Rescale_Ship_Speeds',
    'Adjust_Ship_Cargo_Capacity',
    ]

from fnmatch import fnmatch
import math
from Framework import Transform_Wrapper, Plugin_Log
from ...Classes import *
from .Shared import *


@Transform_Wrapper(shared_docs = doc_matching_rules)
def Rescale_Ship_Speeds(
        average = None,
        variation = None,
        match_all = None,
        match_any = None,
        match_none = None,
        use_arg_engine = False,
        use_split_engine = False,
    ):
    '''
    Rescales the speeds of different ship classes, centering on the give
    target average speeds. Ships are assumed to be using their fastest race
    engines. Averaged across all ships of the rule match.

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
    # If neither average or variation given, do nothing.
    if average == None and variation == None:
        return

    database = Database()
    ship_macros = database.Get_Macros('ship_*') + database.Get_Macros('units_*')
    engine_macros = database.Get_Macros('engine_*') + database.Get_Macros('generic_engine_*')

    # Pick ships that are being modified.
    ship_macros = [x for x in ship_macros if Is_Match(x, match_all, match_any, match_none)]

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
                ship.Adjust_Speed(new_speed / orig_speed)


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


    # Apply the xml changes.
    database.Update_XML()

    return


# TODO: not a rescaling, just adjustment, but this uses database stuff; think
# renaming modules based on database/not-database.
@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Ship_Cargo_Capacity(
        multiplier,
        match_all = None,
        match_any = None,
        match_none = None,
        cargo_tag = None,
    ):
    '''
    Adjusts the cargo capacities of matching ships.
    
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
    '''
    '''
    This one is tricky, since cargo is part of a separate storage macro.
    This macro needs to be looked up for each ship, along with the
    wanted multiplier.

    Since ships can share a storage macro, first pass will find multipliers 
    associated with each macro, second pass will resolve conflicts and make 
    changes.
    '''
    database = Database()
    ship_macros = database.Get_Macros('ship_*') + database.Get_Macros('units_*')
    #storage_macros = database.Get_Macros('storage_*')

    # Pick ships that are being modified.
    ship_macros = [x for x in ship_macros if Is_Match(x, match_all, match_any, match_none)]

    # Pass over them, collecting storage units.
    storage_macros = []
    for ship in ship_macros:
        for storage in ship.Get_Storage_Macros():
            # Skip if not of the right type.
            if cargo_tag and cargo_tag not in storage.Get_Tags():
                continue
            # Record it.
            storage_macros.append(storage)

    # Toss duplicates.
    storage_macros = set(storage_macros)
    # Rescale them all.
    for storage in storage_macros:
        volume = storage.Get_Volume()
        storage.Set_Volume(volume * multiplier)
        
    # Apply the xml changes.
    database.Update_XML()
    return



# TODO: maybe reuse some of this code above with a call.
def Is_Match(ship, match_all = None, match_any = None, match_none = None):
    '''
    Checks a ship macro against the given rules, and returns args from
    the first matched rule (as a tuple of there is more than 1 arg).
    On no match, returns None.

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
            key, value = rule.split()
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
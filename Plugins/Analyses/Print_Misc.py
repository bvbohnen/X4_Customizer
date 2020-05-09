

from Framework import Analysis_Wrapper, Plugin_Log
from ..Classes import *

__all__ = [
    'Print_Ship_Speeds',
    ]

@Analysis_Wrapper()
def Print_Ship_Speeds(
        use_arg_engine = False,
        use_split_engine = False,
    ):
    '''
    Prints out speeds of various ships, under given engine assumptions,
    to the plugin log.

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
    '''    
    database = Database(read_only = True)
    ship_macros = database.Get_Macros('ship_*') + database.Get_Macros('units_*')
    engine_macros = database.Get_Macros('engine_*') + database.Get_Macros('generic_engine_*')

    # Select an engine for every ship, to use in speed estimation.
    for ship in ship_macros:
        ship.Select_Engine(
            engine_macros = engine_macros,
            owner = 'argon' if use_arg_engine else 'split' if use_split_engine else None,
            )

    # Organize ships by class.
    lines = ['Ship speeds: ']
    for ship_class in ['ship_xs','ship_s','ship_m','ship_l','ship_xl']:
        lines.append(f'\n {ship_class}:')
        this_dict = {}

        # Fill in speeds.
        speeds = []
        for macro in ship_macros:
            if macro.class_name == ship_class:
                speed = macro.Get_Speed()
                this_dict[macro.Get_Game_Name()] = macro
                # Ignore mismatches and unfinished ships for stats.
                # Ignore the python.
                if speed > 5 and macro.name != 'ship_spl_xl_battleship_01_a_macro':
                    speeds.append(speed)

        # Sort by name.
        lines += [f'  {k:<35}:{v.Get_Speed():>4.0f}  ({v.name}, {v.engine_macro.name})' 
                    for k,v in sorted(this_dict.items())]
        # Average of the group.
        lines.append('\n  Average: {:.0f} ({:.0f} to {:.0f})'.format(
            sum(speeds)/len(speeds),
            min(speeds),
            max(speeds),
            ))
    Plugin_Log.Print('\n'.join(lines))
    return


'''
Transforms to weapons.

Note: 
Weapon "class" values:
    ['weapon','missilelauncher','turret','missileturret','bomblauncher']
Bullet "class" values:
    ['bullet','missile','bomb','mine','countermeasure']

Notes on reload times:
    There are two basic weapon styles: single shot and burst.
    For single shot weapons:
        fire_rate = 1 / reload_time
    For burst weapons:
        Behavior is tracked in the ammo fields, where the weapon has a
        concept of loading ammo at ammo_reload intervals up to a ammo_max,
        then bursting it out at reload_rate.
        Ammo has to hit max before it can burst, and does a full burst,
        so the overall result is:
        burst_rate = 1 / (ammo_reload_time + 1/reload_rate * (ammo_max-1))

        If ammo_max == 1, then there is no reload_rate contribution
        since there is no time between burst shots, so the result
        is just:
        burst_rate = 1 / ammo_reload_time

        However, the in-game encylopedia seems to mess this up, using
        instead:
        burst_rate = 1 / (ammo_reload_time + 1/(reload_rate * (ammo_max-1)))
        This doesn't make any sense as-is, so consider it a bug.
        -Ingame testing verifies this is a bug.

'''
__all__ = [
    'Adjust_Weapon_Damage',
    'Adjust_Weapon_Range',
    'Adjust_Weapon_Shot_Speed',
    'Adjust_Weapon_Fire_Rate',
    ]

from collections import defaultdict
from fnmatch import fnmatch
import math
from Framework import Transform_Wrapper, Plugin_Log
from ..Classes import *
from .Support import Fill_Defaults, Group_Objects_To_Rules, Convert_Old_Match_To_New

doc_matching_rules = '''
    Weapon transforms will commonly use a group of matching rules
    to determine which weapons get modified, and by how much.

    Args are one or more dictionaries with these fields, where matching
    rules are applied in order, with a weapon being grouped by the first
    rule it matches. If a bullet or missile is used by multiple weapons
    in different match groups, their adjustments will be averaged.

    A dictionary has the following shared fields:

    * match_any, match_all, match_none
      - Lists of matching rules. Weapon is selected if matching nothing
        from match_none, and anything from match_any or everything from
        match_all.
    * skip
      - Optional, bool, if True then this group is not edited.
      - Can be used as a way to blacklist weapons.
      
    Matching rules are strings with the following format:
    * The "key" specifies the xml field to look up, which will
      be checked for a match with "value".
    * Supported keys for weapons:
      - 'name'  : Internal name of the weapon component; supports wildcards.
      - 'class' : The component class.
        - One of: weapon, missilelauncher, turret, missileturret, bomblauncher
        - These are often redundant with tag options.
      - 'tags'  : One or more tags for this weapon, space separated.
        - See Print_Weapon_Stats output for tag listings.
      - '*'     : Matches all wares; takes no value term.

    As a special case, a single multiplier may be given, to be applied
    to all weapons (lasers,  missiles, etc.)

    '''


def Adjust_Generic_Mult(scaling_rules, adjust_method_name):
    '''
    Shared function for generically scaling a weapon by a multiplier.

    * scaling_rules
    * adjust_method_name
      - Name of bullet method to call with an adjustment multiplier.
    '''
    if not scaling_rules:
        return
    # Shared rule/database prep.
    scaling_rules, database = Prep_Rules_And_Database(
        scaling_rules, 
        defaults = {
            'multiplier' : 1,
        }, 
        old_arg_names = ['multiplier'])

    # Collect the wanted multipliers for each bullet; a bullet may
    # occur more than once.
    bullet_new_mults = defaultdict(list)

    # Loop over the rule/groups.
    for rule in scaling_rules:
        if rule['skip'] or rule['multiplier'] == 1:
            continue
        weapon_macros = rule['matches']
        multiplier    = rule['multiplier']
        for weapon in weapon_macros:
            bullet = weapon.Get_Bullet()
            bullet_new_mults[bullet].append(multiplier)

    # Average for each bullet.
    for bullet, mults in bullet_new_mults.items():
        mult = sum(mults) / len(mults)
        getattr(bullet, adjust_method_name)(mult)
        
    # Apply the xml changes.
    database.Update_XML()
    return


@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Weapon_Damage(
        *scaling_rules,
    ):
    '''
    Adjusts damage done by weapons.  If multiple weapons use the same
    bullet or missile, it will be modified by an average of the users.
    
    Args are one or more dictionaries with these fields, where matching
    rules are applied in order, with a ship being grouped by the first
    rule it matches:

    * multiplier
      - Float, amount to multiply damage by.
    * match_any, match_all, match_none
      - Lists of matching rules. Weapon is selected if matching nothing
        from match_none, and anything from match_any or everything from
        match_all.        
    * skip
      - Optional, bool, if True then this group is not edited.
    '''
    Adjust_Generic_Mult(scaling_rules, 'Adjust_Damage')
    return


@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Weapon_Range(
        *scaling_rules,
    ):
    '''
    Adjusts weapon range. Shot speed is unchanged.
    
    Args are one or more dictionaries with these fields, where matching
    rules are applied in order, with a ship being grouped by the first
    rule it matches:

    * multiplier
      - Float, amount to multiply damage by.
    * match_any, match_all, match_none
      - Lists of matching rules. Weapon is selected if matching nothing
        from match_none, and anything from match_any or everything from
        match_all.        
    * skip
      - Optional, bool, if True then this group is not edited.
    '''
    Adjust_Generic_Mult(scaling_rules, 'Adjust_Range')
    return


@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Weapon_Shot_Speed(
        *scaling_rules,
    ):
    '''
    Adjusts weapon projectile speed. Range is unchanged.
    
    Args are one or more dictionaries with these fields, where matching
    rules are applied in order, with a ship being grouped by the first
    rule it matches:

    * multiplier
      - Float, amount to multiply damage by.
    * match_any, match_all, match_none
      - Lists of matching rules. Weapon is selected if matching nothing
        from match_none, and anything from match_any or everything from
        match_all.        
    * skip
      - Optional, bool, if True then this group is not edited.
    '''
    Adjust_Generic_Mult(scaling_rules, 'Adjust_Speed')
    return


# TODO: what about missiles?  Still damage scale, or not? Ignore?
# Maybe args for include_bullets and include_missiles?
# Burden on user?
# Wrapper transforms for just-lasers and just-missiles?
@Transform_Wrapper(shared_docs = doc_matching_rules)
def Adjust_Weapon_Fire_Rate(
        *scaling_rules,
    ):
    '''
    Adjusts weapon rate of fire. DPS and heat/sec remain constant.
    Time between shots in a burst and time between bursts are affected
    equally for burst weapons.  If multiple matched weapons use the
    same bullet or missile, the modifier will be averaged between them.
        
    Args are one or more dictionaries with these fields, where matching
    rules are applied in order, with a ship being grouped by the first
    rule it matches:

    * multiplier
      - Float, amount to multiply fire rate by.
      - If 1, the weapon is not modified.
    * min
      - Float, optional, minimum fire rate allowed by an adjustment, 
        in shots/second.
      - Default is None, no minimum is applied.
    * match_any, match_all, match_none
      - Lists of matching rules. Weapon is selected if matching nothing
        from match_none, and anything from match_any or everything from
        match_all.        
    * skip
      - Optional, bool, if True then this group is not edited.
    '''    
    if not scaling_rules:
        return

    # Shared rule/database prep.
    scaling_rules, database = Prep_Rules_And_Database(
        scaling_rules, 
        defaults = {
            'multiplier' : 1,
            'min'        : None,
        }, 
        old_arg_names = ['multiplier'])

    # Note: these edits largely affect the bullets, and multiple weapons
    # may use the same bullet. To avoid over-modification, first pass
    # will collect the wanted rof for each seen bullet, second pass will
    # average the rofs and apply the change.
    bullet_new_rofs = defaultdict(list)

    # Loop over the rule/groups.
    for rule in scaling_rules:
        if rule['skip'] or rule['multiplier'] == 1:
            continue
        weapon_macros = rule['matches']
        multiplier    = rule['multiplier']
        min           = rule['min']

        for weapon in weapon_macros:
            # Look up the bullet to modify.
            bullet = weapon.Get_Bullet()

            # Prior overall rof.
            rof = bullet.Get_Rate_Of_Fire()

            # Scale, and limit to min.
            new_rof = rof * multiplier
            if min:
                # If original rof already below the min, skip.
                if rof <= min:
                    continue
                if new_rof < min:
                    new_rof = min

            # Save this rof.
            bullet_new_rofs[bullet].append(new_rof)


    # Average the bullet rofs and apply.
    for bullet, new_rofs in bullet_new_rofs.items():
        old_rof = bullet.Get_Rate_Of_Fire()
        new_rof = sum(new_rofs) / len(new_rofs)
        bullet.Set_Rate_Of_Fire(new_rof)

        # Adjust damage and heat to counter this change, eg. half damage
        # at double rof.
        multiplier = new_rof / old_rof
        bullet.Adjust_Damage(1 / multiplier)
        bullet.Adjust_Heat(1 / multiplier)
        
    # Apply the xml changes.
    database.Update_XML()
    return


def Prep_Rules_And_Database(scaling_rules, defaults, old_arg_names):
    '''
    Shared code to prepare the scaling rules and load a database.
    Returns a tuple of (scaling_rules, database).
    '''
    # Convert old style args to new style args, if found.
    if not isinstance(scaling_rules[0], dict):
        scaling_rules = Convert_Old_Match_To_New(scaling_rules, *old_arg_names)
    
    # Polish the scaling rules with defaults.
    Fill_Defaults(scaling_rules, defaults)

    # Load the weapons (and turrets).
    # TODO: skip missiles?
    database = Database()
    weapon_macros = []
    for pattern in ['weapon_*', 'turret_*']:
        weapon_macros += database.Get_Macros(pattern, classes = [Weapon_System])

    # Group according to rules.
    Group_Objects_To_Rules(weapon_macros, scaling_rules, Is_Match)
    return (scaling_rules, database)

    
def Is_Match(weapon, match_none, match_all, match_any, **kwargs):
    '''
    Checks a ship macro against the given rules, and returns True if a match,
    else False.

    * weapon
      - Weapon macro object.
    * match_all
      - List of match rules (tuple of key, value) that must all match.
    * match_any
      - List of match rules of which any need to match.
    * match_none
      - List of match rules that must all mismatch.
    '''
    # Look up properties of interest.
    component = weapon.Get_Component()
    name = component.name
    class_name = component.class_name
    tags = component.Get_Connection_Tags()
    
    # Check the matching rules.
    # match_none failures first, then match_all failures, then match_any
    # successes.
    for rules in [match_none, match_all, match_any]:
        # Skip if not given.
        if not rules:
            continue
        
        for rule in rules:
            if rule == '*':
                key = rule
                value = None
            else:
                key, value = rule.split(' ', 1)
            
            if((key == '*')
            or (key == 'name' and fnmatch(name, value))
            or (key == 'tags' and all(x in tags for x in value.split(' ')))
            or (key == 'class' and class_name == value)):
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

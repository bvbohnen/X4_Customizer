
from collections import OrderedDict
from ... import File_Manager
from ...Common import Flags
from ...Common import Scaling_Equations


@File_Manager.Transform_Wrapper('types/TBullets.txt', 'types/TLaser.txt')
def Adjust_Weapon_DPS(
    # A flat factor to use for damage adjustment.
    # This is applied after the scaling equation below, so that that
    #  equation can be configured to the base xrm numbers.
    # Go with 2.5 to be conservative, or even 2 since some ships have more
    #  turret gun mounts than in vanilla.
    # This helps bring up energy drain as well.
    scaling_factor = 1,

    bullet_name_adjustment_dict = {},

    # If a scaling equation should be used for the damage adjustment.
    use_scaling_equation = False,
    # Set the tuning points.
    # Note: these numbers will have an implicit 10^3 factor, to avoid the
    #  scaling equation overflowing.
    damage_to_adjust_kdps = 9,
    # The damage to pin in place on the low end.
    damage_to_keep_static_kdps = 3,

    # If laser energy efficiency should be modified or not.
    maintain_energy_efficiency = True,

    # Options to change only hull or shield dps.
    adjust_hull_damage_only     = False,
    adjust_shield_damage_only   = False,

    # Don't modify repair lasers, mainly to avoid having to put this
    #  in every transform call individually, since normally these don't
    #  need modification.
    ignore_repair_lasers = True,
    
    print_changes = False
    ):
    '''
    Adjust weapon damage/second by changing bullet damage.
    If a bullet is used by multiple lasers, the first laser will
    be used for DPS calculation.
    Energy efficiency will remain constant, changing energy/second.

    * scaling_factor:
      - The base multiplier to apply to shot speeds.
    * adjust_hull_damage_only:
      - Bool, if True only hull damage is modified. Default False.
    * adjust_shield_damage_only:
      - Bool, if True only shield damage is modified. Default False.
    * use_scaling_equation:
      - If True, a scaling formula will be applied, such
        that shots near damage_to_adjust_kdps see the full scaling_factor,
        and shots near damage_to_keep_static_kdps remain largely unchanged.
    * damage_to_adjust_kdps, damage_to_keep_static_kdps:
      - Equation tuning values, in units of kdps, eg. 1 for 1000 damage/second.
        Scaling values are for shield DPS; hull DPS will be scaled at a
        rate of 1/6 of shield DPS.
    * bullet_name_adjustment_dict:
      - Dict, keyed by bullet name (eg. 'SS_BULLET_PBC'), with the
        multiplier to apply. This also supports matching to bullet
        flags using a 'flag_' prefix, eg. 'flag_beam' will match
        to beam weapons. Flag matches are lower priority than
        name matches.
      - If multiple flag matches are found, the first flag will
        be used if the input is an OrderedDict, otherwise any
        Python default is used (likely equivelent to ordereddict
        in Python 3.6).
      - '*' entry will match all weapons not otherwise matched,
        equivelent to setting scaling_factor and not using the
        scaling equation.
    * maintain_energy_efficiency:
      - Bool, if True (default) then weapon energy usage will be scaled to
        keep the same damage/energy ratio, otherwise damage is adjusted but
        energy is unchanged.
    * ignore_repair_lasers:
      - Bool, if True (default) then repair lasers will be ignored.
    * print_changes:
      - If True, speed adjustments are printed to the summary file.  
    '''
    # Add the ignored entries if not present.
    for name in Ignored_lasers_and_bullets:
        if name not in bullet_name_adjustment_dict:
            bullet_name_adjustment_dict[name] = 1

    tbullets_dict_list = File_Manager.Load_File('types/TBullets.txt')
    
    if print_changes:
        File_Manager.Write_Summary_Line('\nDamage adjustments:')
        
    if use_scaling_equation:
        # Get formula and its coefficients here.
                    
        # Create a set of points to be tuned against.
        # The primary adjustment point.
        x_main = damage_to_adjust_kdps
        y_main = x_main * scaling_factor
        # The secondary, static point, where x=y.
        x_static = damage_to_keep_static_kdps
        y_static = damage_to_keep_static_kdps
            
        # To encourage fitting the lower end more than the higher end, can represent
        #  low end values multiple times.
        # Give two low points for now, the one provided and another nearby, to help
        #  stabalize the equation coefs.
        x_vec   = [x_main, x_static, x_static * .8]
        y_vec   = [y_main, y_static, y_static * .8]
            
        # Get the function and its coefs to use.
        shield_scaling_func = Scaling_Equations.Get_Scaling_Fit(x_vec, y_vec, reversed = False)
        # Also get one for hull damage, which has lower damage values.
        x_vec = [x / Hull_to_shield_factor for x in x_vec]
        y_vec = [y / Hull_to_shield_factor for y in y_vec]
        hull_scaling_func = Scaling_Equations.Get_Scaling_Fit(x_vec, y_vec, reversed = False)
    else:
        shield_scaling_func = None
        hull_scaling_func = None
        
    # Parse out the flag matches from the input dict.
    # This will pull off the 'flag_' prefix.
    # Flag ordering will be kept intact, if an ordered dict was provided.
    flag_match_dict = OrderedDict((key.replace('flag_',''), value)
                       for key,value in bullet_name_adjustment_dict.items() 
                       if key.startswith('flag_'))

    # Set up a dict which tracks modified bullets, to prevent a bullet
    #  being modded more than once by different lasers (which would cause
    #  accumulated damage buffing).
    bullet_indices_seen_list = []

    # Similar to above, need to pair lasers with bullets to get all of the necessary
    #  metrics for this calculation.
    # Step through each laser.
    for laser_dict in File_Manager.Load_File('types/TLaser.txt'):

        # Grab the fire delay, in milliseconds.
        this_fire_delay = int(laser_dict['fire_delay'])

        # Determine fire rate, per second.
        fire_rate = Flags.Game_Ticks_Per_Minute / this_fire_delay / 60            

        # Loop over the bullets created by this laser.
        for bullet_index in Get_Laser_Bullets(laser_dict):

            # Skip if this bullet was already seen.
            if bullet_index in bullet_indices_seen_list:
                continue
            # Add this bullet to the seen list.
            bullet_indices_seen_list.append(bullet_index)

            # Look up the bullet.
            bullet_dict = tbullets_dict_list[bullet_index]

            # Unpack the flags.
            flags_dict = Flags.Unpack_Tbullets_Flags(bullet_dict)

            # If ignoring repair lasers, and this is a repair weapon, skip.
            if flags_dict['repair'] and ignore_repair_lasers:
                continue
                
            # There are two options here:
            #  1) Handle shield and hull damage together, combining them into a
            #     single metric.
            #     -Drawback: a weapon like the ion cannon may be treated as a
            #     lower tier weapon due to its average shield/hull damage being
            #     much lower than its specialized shield damage.
            #  2) Handle shield and hull separately.
            #     -Drawback: it is harder to determine the energy usage adjustment
            #     if the shield/hull factors differ by much.
            #  Go with option (2), but keep some commented code left over from
            #  option (1).
                
            # -Removed; from option (1) above.
            # hull_damage       = int(bullet_dict['hull_damage'])
            # shield_damage     = int(bullet_dict['shield_damage'])                
            ##Calculate hull and shield dps for this weapon.
            # hull_dps   = hull_damage   * fire_rate
            # shield_dps = shield_damage * fire_rate
            ##Calculate overall dps, applying scaling on hull.
            ##The hull scaling
            # overall_dps = (shield_dps + hull_dps * Hull_to_shield_factor)/2

            # Keep a dict to temporarily store scaling factors.
            scaling_factor_dict = {}
            # Loop over the field types; catch the OOS field name as well for
            #  writing back the new damages later, and select the matching
            #  scaling equation.
            for field, oos_field, scaling_func in [
                        ('hull_damage'  , 'hull_damage_oos'  , hull_scaling_func),
                        ('shield_damage', 'shield_damage_oos', shield_scaling_func)]:

                # Skip hull or shield changes as requested.
                if adjust_hull_damage_only and field == 'shield_damage':
                    continue
                elif adjust_shield_damage_only and field == 'hull_damage':
                    continue

                # Look up the IS damage, and calculate dps.
                damage = int(bullet_dict[field])
                overall_dps = damage   * fire_rate

                # Skip ahead if dps is 0, eg. shield dps for mass drivers.
                if overall_dps == 0:
                    continue

                # Determine the scaling factor to apply.
                # Look up this bullet in the override dict first.
                if bullet_dict['name'] in bullet_name_adjustment_dict:
                    this_scaling_factor = bullet_name_adjustment_dict[bullet_dict['name']]

                # Look for any flag match.
                elif any(flags_dict[flag] for flag in flag_match_dict):
                    # Grab the first flag match.
                    for flag, value in flag_match_dict.items():
                        if flags_dict[flag]:
                            this_scaling_factor = value
                            break

                # If there is a wildcard use that.
                elif '*' in bullet_name_adjustment_dict:
                    this_scaling_factor = bullet_name_adjustment_dict['*']

                elif use_scaling_equation:
                    this_scaling_factor = 1
                    # Run the scaling formula.
                    # This takes in a weighted average of original shield/hull dps,
                    #  and returns the replacement dps, from which the scaling
                    #  can be calculated.
                    # This takes dps in kdps, eg. with a 10^3 implicit factor,
                    #  to avoid overflow.
                    new_overall_dps = 1e3* scaling_func(overall_dps/1e3)
                    this_scaling_factor *= new_overall_dps / overall_dps
                    
                elif scaling_factor != 1:
                    this_scaling_factor = scaling_factor
                else:
                    continue

                # Store the factor in the temp dict.
                scaling_factor_dict[field] = this_scaling_factor

                # Debug printout.
                if print_changes:
                    # Give bullet name, old and new dps,
                    #  and the scaling factor.
                    File_Manager.Write_Summary_Line(
                        '{:<30} {:<15}:  {:>10} -> {:>10}, x{}'.format(
                            bullet_dict['name'],
                            field,
                            round(overall_dps),
                            round(overall_dps * this_scaling_factor),
                            # Give only two sig digits for the scaling factor.
                            round(this_scaling_factor, 2)
                        ))

                # Apply the scaling factors to their IS and OOS fields.
                for writeback_field in [field, oos_field]:
                    value = int(bullet_dict[writeback_field])
                    bullet_dict[writeback_field] = str(int(value * this_scaling_factor))

            # If no adjustments were made to the bullet, skip ahead.
            if not scaling_factor_dict:
                continue

            # Adjust energy usage.
            # This can be done with the average of the factors or the max
            #  of the factors.
            # For specialized weapons like ion cannons, which likely had a much
            #  bigger factor on shield damage than hull damage on the expectation
            #  they will only be used against shields, it makes the most sense
            #  to adjust energy based on the biggest factor (the main use case
            #  for the weapon).
            if maintain_energy_efficiency:
                max_factor = max(scaling_factor_dict.values())
                value = int(bullet_dict['energy_used'])
                bullet_dict['energy_used'] = str(int(value * max_factor))
                
    #  Since bullet energies may have been changed, update the max laser energies.
    Floor_Laser_Energy_To_Bullet_Energy()



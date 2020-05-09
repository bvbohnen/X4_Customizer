'''
Transforms to the map.
'''

from Framework import Transform_Wrapper, Load_File, Load_Files, Plugin_Log, Print

from .Classes import Galaxy
from .Scaling import Scale_Regions, Scale_Sectors

'''
TODO:
- Adjust misc md scripts
  - PlacedObjects maybe.
    - Data vaults are close to center anyway (generally within 50km any dim).
    - Abandoned ships can be far, up to 1000km+ per dim.
- Change mass traffic draw distance in parameters.xml.
  - Generally want to reduce this due to performance.
  - Maybe optional, or separate transform.
- Fix slight highway graphic doubling near zone gates (harmless, visual quirk).
  - Possibly a small y offset in the highway, spline, or gate?
  - Could just scrap y changes, probably.
- Per-sector scaling factors, adjust more if highway is removed.
- Dynamic scaling based on initial sector size; smaller sectors scale less.
  - Maybe use four data points: scaling vs gate distance, two points, and
    extrapolate linearly with saturation at endpoints.
  - Or something more automated.

- Sacred Relic spaced out; 250 km to furthest station.
- Hatikvah station 308km from gate (cluster_29).
  - Not due to god, when checking godlog.
  - Standard zones have up to a ~415 km distance (one or two outliers).
  - Should have been scaled to 166 km?
- debuglog complaint about superhighway002_cluster_29_macro (Hatikvah) splines?


Note on regions:
    These are referenced in cluster.xml, but are defined over in
    libraries/region_definitions.xml. They mostly include resource fields,
    but also lockbox spawns, audio sounds, wrecks, etc.
  
Note: at a glance, vanilla zones can be as little as 9.5 km apart, though
    normally are further.  Sector highway gates are also spaces this much.
    

Note on gate sizing and distance:
    X4 gates are larger than X3.  Assuming 2x wider (not sure on exact ratio),
    then gates need to be 2x further away to have the same visual footprint.
    Assuming X3 has a 50 km gate-to-gate distance, and X4 has a ~230 km
    distance, then want a scaling of 100/230 = 0.43 (based on argon prime).

    Actual gate distances in x4 range from 133843 to 465930 km, with
    an average of 276060 (for those with distances >50km).
    X3 only ranges ~50km to ~100km (Avarice), so the x4 variance is
    much larger.
    If wanting to scale 465930 to 200000, need 0.43 scaling, which
    matches nicely to the argon prime case above.

Notes on sector properties:
    Sector.size scales with how spaced out the objects are,
    eg. 417 km in vanilla, 180 km at 0.4x scaling (0.43 actual scaler).

    Sector.coresize scales a little but with a hard minimum. The example above
    has 505 km coresize (+20%), but all sectors floor at 424832 core size.
    This is not something that appears accessible; scripts should probably
    be switched to using size instead of coresize.

    Sector.coreposition offsets to the center of objects for the sector
    in some way, presumably based on gates, but does certainly scale.
    Vanilla sectors can vary wildly, eg. >100km x and >100km z coreposition.

    In testing, it appears God station placement is based on coresize.
    Further, when the newzonechance triggers on a placement, if God
    fails to fit a zone, it will completely fail to place the station,
    with no fallback to using existing zones.
    Further, the new zone creation rules are unclear but appear to
    assume very large zone sizes (50km per side like rebirth?).
    As such, to get aggressive shrinks, new zones need to be manually
    added to the sectors, and the god newzonechance dropped a bunch,
    even down to 0.
    However, hand placed zones, even with some rng, means that stations
    will be in the same spots every playthrough, so this approach would
    favor generating very large numbers of such zones.


Note on travel times:
    X3 seta is up to 10x, X4 seta if 5x.
    X3 speeds are 125 typically, X4 are ~300 base and ~3k travel drive.
    (Can be lower, eg. 200 and 3k in x4, but depends wildly on engine).
    
    X4 time to cross AP: 230 km / 3kps = 76s (can't seta in travel)
    X4 time, no travel : 230 km / 300mps / 5 = 153s
    X3 time to cross AP: 50 km / 125mps / 10 = 40s (can seta)

    So X3 takes about half the time of X4 in general.
    If x4 travel drive removed, to meet x3 times, need scaling of 40/153= 0.26.
    To maintain x4 travel drive times, need scaling of 76/153 = 0.5

Overall ideal scaling from the above is between 0.26 and 0.5.
Maybe aim for 0.33?

Note on save game:
    These edits potentially somewhat update an existing save. However, it
    was observed in Guiding Star, in a game with normal sectors and loaded
    with 0.4x sectors, that the superhighway entry/exit gates only moved
    3/4 of the distance they were supposed to, but the actual spline
    moved the full distance, so the gates and the highway entry were offset.
    (Which is weird; taking off the 0.4x scaling returns it to normal.)
    Also, the newly added sector, once used for anything, cannot be
    removed.
    So, in general, this should require a new game, and not be removed.
    Zones can potentially be moved around, but should not be removed
    (eg. the same names should be present).

'''
@Transform_Wrapper()
def Scale_Sector_Size(
        scaling_factor,
        scaling_factor_2 = None,
        transition_size_start = 200000,
        transition_size_end   = 400000,
        # TODO: make a decision on if this is good or not.
        # Maybe helps with hatikvahs highway/asteroid overlap?
        recenter_sectors = False,
        randomize_new_zones = False,
        precision_steps = 10,
        remove_ring_highways = False,
        remove_nonring_highways = False,
        extra_scaling_for_removed_highways = 0.7,
        scale_regions = True,
        move_free_ships = True,
        debug = True,
        _test = False
    ):
    '''
    Change the size of the maps by moving contents (zones, etc.) closer
    together or further apart. Note: this will require a new game to
    take effect, as positions become part of a save file.

    * scaling_factor
      - Float, how much to adjust distances by.
      - Eg. 0.5 to cut sector size roughly in half.
    * scaling_factor_2
      - Float, optional, secondary scaling factor to apply to large sectors.
      - If not given, scaling_factor is used for all sectors.
    * transition_size_start
      - Int, sector size at which to start transitioning from
        scaling_factor to scaling_factor_2.
      - Defaults to 200000.
      - Sectors smaller than this will use scaling_factor.
    * transition_size_end
      - Int, optional, sector size at which to finish transitioning to
        scaling_factor_2.
      - Defaults to 400000 (400 km).
      - Sectors larger than this will use scaling_factor_2.
      - Sectors of intermediate size have their scaling factor interpolated.
    * recenter_sectors
      - Adjust objects in a sector to approximately place the coreposition
        near 0,0,0.
      - Defaults False.
      - In testing, this makes debugging harder, and may lead to unwanted
        results.  Pending further testing to improve confidence.
    * randomize_new_zones
      - Randomizes the positions of new zones each run, instead of using
        the sector name as a seed.
      - Defaults False.
      - Generally should be left false, so that zones don't move around
        for a save game.
    * num_steps
      - Int, over how many movement steps to perform the scaling.
      - Higher step counts take longer to process, but each movement is
        smaller and will better detect objects getting too close to each other.
      - Recommend lower step counts when testing, high step count for
        a final map.
      - Defaults to 10.
    * remove_ring_highways
      - Bool, set True to remove the ring highways.
    * remove_nonring_highways
      - Bool, set True to remove non-ring highways.
    * extra_scaling_for_removed_highways
      - Float, extra scaling factor to apply to sectors that had highways
        removed.
      - Defaults to 0.7.
    * scale_regions
      - Bool, if resource and debris regions should be scaled as well.
      - May be slightly off from sector scalings, since many regions are
        shared between sectors.
      - Defaults True.
    * move_free_ships
      - Bool, if ownerless ships spawned at game start should be moved
        along with the other sector contents.
      - May impact difficulty of finding these ships.
      - Defaults True.
    * debug
      - Bool, if True then write runtime state to the plugin log.
    '''
    
    # Use a pattern to pick up the base and dlc sectors.
    # Store the game_file as key, xml root as value.
    # Below transforms exit the xml root, which gets committed at the end
    # if there were no errors.
    # Note: for quick testing, just grab the basic files, no wildcards.
    if _test:
        gamefile_roots = {
        'sectors'       : [(x, x.Get_Root()) for x in [Load_File('maps/xu_ep2_universe/sectors.xml')]],
        'zones'         : [(x, x.Get_Root()) for x in [Load_File('maps/xu_ep2_universe/zones.xml')]],
        'zone_highways' : [(x, x.Get_Root()) for x in [Load_File('maps/xu_ep2_universe/zonehighways.xml')]],
        'clusters'      : [(x, x.Get_Root()) for x in [Load_File('maps/xu_ep2_universe/clusters.xml')]],
        'sec_highways'  : [(x, x.Get_Root()) for x in [Load_File('maps/xu_ep2_universe/sechighways.xml')]],
        'region_defs'   : [(x, x.Get_Root()) for x in [Load_File('libraries/region_definitions.xml')]],
        'md_hq'         : [(x, x.Get_Root()) for x in [Load_File('md/X4Ep1_Mentor_Subscription.xml')]],
        'md_stations'   : [(x, x.Get_Root()) for x in [Load_File('md/FactionLogic_Stations.xml')]],
        'md_objects'    : [(x, x.Get_Root()) for x in [Load_File('md/PlacedObjects.xml')]],
        'god'           : [(x, x.Get_Root()) for x in [Load_File('libraries/god.xml')]],
        }
    else:
        gamefile_roots = {
        'sectors'       : [(x, x.Get_Root()) for x in Load_Files('*maps/xu_ep2_universe/*sectors.xml')],
        'zones'         : [(x, x.Get_Root()) for x in Load_Files('*maps/xu_ep2_universe/*zones.xml')],
        'zone_highways' : [(x, x.Get_Root()) for x in Load_Files('*maps/xu_ep2_universe/*zonehighways.xml')],
        'clusters'      : [(x, x.Get_Root()) for x in Load_Files('*maps/xu_ep2_universe/*clusters.xml')],
        'sec_highways'  : [(x, x.Get_Root()) for x in Load_Files('*maps/xu_ep2_universe/*sechighways.xml')],
        'region_defs'   : [(x, x.Get_Root()) for x in [Load_File('libraries/region_definitions.xml')]],
        'md_hq'         : [(x, x.Get_Root()) for x in [Load_File('md/X4Ep1_Mentor_Subscription.xml')]],
        'md_stations'   : [(x, x.Get_Root()) for x in [Load_File('md/FactionLogic_Stations.xml')]],
        'md_objects'    : [(x, x.Get_Root()) for x in [Load_File('md/PlacedObjects.xml')]],
        'god'           : [(x, x.Get_Root()) for x in [Load_File('libraries/god.xml')]],
        }
        

    def Safe_Update_MD(xml_root, xpath, attr, old_text, new_text):
        'Helper function for editing md nodes.'
        # Note: add some safety incase the lookups fail.
        nodes = xml_root.xpath(xpath)
        if not nodes:
            msg = 'Scale_Sector_Size failed to find a target MD script node; skipping this node.'
            Plugin_Log.Print(msg)
            Print(msg)
        else:
            nodes[0].set(attr, nodes[0].get(attr).replace(old_text, new_text))


    # Tweak faction logic to spawn stations closer/further.
    faction_stations_file = Load_File('md/FactionLogic_Stations.xml')
    faction_stations_root = faction_stations_file.Get_Root()

    # TODO: what is the difference between sector.size and sector.coresize?
    Safe_Update_MD(
        faction_stations_root, 
        ".//match_distance[@max='[$ChosenSector.coresize / 2.0f, 400km].min']",
        'max',
        '400km',
        str(int(400 * scaling_factor) ))
    
    Safe_Update_MD(
        faction_stations_root, 
        ".//set_value[@exact='[$ChosenSector.size / 2.0f, 400km].min']",
        'exact',
        '400km',
        str(int(400 * scaling_factor) ))
    
    # FactionLogic.xml:
    # (Used in selecting existing sector; coreposition usage okay.)
    # <match_distance space="$Sector" value="$Sector.coreposition" max="[$Sector.coresize, 400km].min"/>
    faction_logic_file = Load_File('md/FactionLogic.xml')
    faction_logic_root = faction_logic_file.Get_Root()
    
    Safe_Update_MD(
        faction_logic_root, 
        ".//match_distance[@max='[$Sector.coresize, 400km].min']",
        'max',
        '400km',
        str(int(400 * scaling_factor) ))


    # Load in data of interest, to the local data structure.
    galaxy = Galaxy(
        gamefile_roots, 
        randomize_new_zones = randomize_new_zones,
        recenter_sectors = recenter_sectors,
        move_free_ships = move_free_ships)

    # TODO: record starting sector size for debug.

    # Set scaling factor per sector based on size.
    sector_scaling_factors = {}
    for sector in galaxy.class_macros['sectors'].values():
        # Get raw size, with no minimum.
        size = sector.Get_Size(apply_minimum = False)
        if scaling_factor_2 == None or size < transition_size_start:
            sector_scaling_factors[sector] = scaling_factor
        elif size > transition_size_end:
            sector_scaling_factors[sector] = scaling_factor_2
        else:
            # Linear interpolate.
            ratio = (size - transition_size_start) / (transition_size_end - transition_size_start)
            scaling = scaling_factor_2 * ratio + scaling_factor * (1 - ratio)
            sector_scaling_factors[sector] = scaling


    # Handle highway removal.
    for sector in galaxy.class_macros['sectors'].values():
        # Two types of removal, but one flag to indicate removal happened.
        highways_removed = False

        if remove_ring_highways and sector.Has_Ring_Highway():
            sector.Remove_Ring_Highways()
            highways_removed = True

        if remove_nonring_highways and sector.Has_Nonring_Highway():
            sector.Remove_Nonring_Highways()
            highways_removed = True

        # Adjust the scaling.
        if highways_removed:
            sector_scaling_factors[sector] *= extra_scaling_for_removed_highways
        


    # Run the repositioning routines.
    # TODO: region scaling factor?
    if scale_regions:
        Scale_Regions(galaxy, sector_scaling_factors, debug)
    Scale_Sectors(galaxy, sector_scaling_factors, debug, precision_steps = precision_steps)

    # Update the xml nodes.
    galaxy.Update_XML()

    # TODO: print sector size change summary.

    
    # If here, everything worked, so commit the updates.
    for file_roots in gamefile_roots.values():
        # TODO: maybe skip clusters, as unmodified.
        for game_file, new_root in file_roots:
            game_file.Update_Root(new_root)

    faction_stations_file.Update_Root(faction_stations_root)
    faction_logic_file.Update_Root(faction_logic_root)

    return



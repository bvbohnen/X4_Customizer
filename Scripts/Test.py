'''
Place to test individual transforms.
Note: the newest tests tend to be near the top.
'''

from pathlib import Path

# Import all transform functions.
import Framework
from Plugins import *

this_dir = Path(__file__).resolve().parent

Settings(
    path_to_x4_folder = r'C:\Steam\SteamApps\common\X4 Foundations',
    developer = 1,
    )

# For all tests to run, mostly to tease out exceptions after
# code changes. Note: some tests may be a bit outdated.
test_all = 0

if 0:
    GUI.Start_GUI()


# Test sector resizing.
if 0 or test_all:
    Scale_Sector_Size(
        scaling_factor                     = 0.4, 
        scaling_factor_2                   = 0.3,        
        #transition_size_start              = 200000,
        #transition_size_end                = 400000,
        recenter_sectors                   = False,
        randomize_new_zones                = False,
        precision_steps                    = 10,
        remove_ring_highways               = True,
        remove_nonring_highways            = True,
        extra_scaling_for_removed_highways = 0.7,
        _test = True)
    
# Test exe edits.
if 0:
    Remove_Sig_Errors()
if 0:
    Remove_Modified()
if 0:
    High_Precision_Systemtime()
if 0:
    Remove_Workshop_Tool_Dependency_Check()
   
if 1:
    Increase_AI_Script_Waits(
        oov_multiplier = 2,
        oov_seta_multiplier = 4,
        oov_max_wait = 15,
        iv_multiplier = 1,
        iv_seta_multiplier = 2,
        iv_max_wait = 5,
        filter = '*',
        include_extensions = False,
        skip_combat_scripts = False,
        )

if 0:
    Adjust_OOV_Damage(0.5)

# Diff generator test.
if 0 or test_all:
    Generate_Diff(
        original_file_path = this_dir / '../private/test' / 'test_original_node.xml',
        modified_file_path = this_dir / '../private/test' / 'test_modified_node.xml',
        output_file_path   = this_dir / '../private/test' / 'test_patch_node.xml',
        )
    Generate_Diffs(
        original_dir_path = this_dir / '../private/test' / 'orig_files',
        modified_dir_path = this_dir / '../private/test' / 'mod_files',
        output_dir_path   = this_dir / '../private/test' / 'diff_files',
        )
    
if 0 or test_all:
    # Try forcing an attribute.
    Settings(forced_xpath_attributes = 'id,method,tags')
    Generate_Diffs(
        original_dir_path = this_dir / '../private/test/deadair/orig',
        modified_dir_path = this_dir / '../private/test/deadair/mod',
        output_dir_path   = this_dir / '../private/test/deadair/diff',
        )

# Test the extension checker.
if 0 or test_all:
    Check_Extension('test_mod')
if 0:
    # Alternatively, check everything (may take longer).
    Check_All_Extensions()


if 0 or test_all:
    Color_Text((20005,3012,'C'))

if 0 or test_all:
    # Live editor tree builders.
    edit_tree = Framework.Live_Editor.Get_Tree_View('components')
    edit_tree = Framework.Live_Editor.Get_Tree_View('weapons')
if 0 or test_all:
    edit_tree = Framework.Live_Editor.Get_Tree_View('ships')


if 0 or test_all:
    Adjust_Mission_Reward_Mod_Chance(10)

# Ship transforms.
if 0 or test_all:
    Adjust_Ship_Speed(
        ('name ship_xen_xl_carrier_01_a*', 1.2),
        ('class ship_s'                  , 2.0),
        ('type corvette'                 , 1.5),
        ('purpose fight'                 , 1.2),
        ('*'                             , 1.1) )

    Adjust_Ship_Crew_Capacity(
        ('class ship_xl'                 , 2.0),
        ('*'                             , 1.5)
        )
    Adjust_Ship_Drone_Storage(
        ('class ship_xl'                 , 2.0),
        ('*'                             , 1.5)
        )
    Adjust_Ship_Missile_Storage(
        ('class ship_xl'                 , 2.0),
        ('*'                             , 1.5)
        )
    Adjust_Ship_Hull(
        ('class ship_xl'                 , 2.0),
        ('*'                             , 1.5)
        )
    Adjust_Ship_Turning(
        ('class ship_xl'                 , 2.0),
        ('*'                             , 1.5)
        )
    
    Print_Ship_Stats('ship_stats_postmod')

if 0:
    Adjust_Ship_Hull(
        ('class ship_l' , 1.5), 
        ('class ship_xl', 1.5))
    
if 0:
    Set_Default_Radar_Ranges(
        ship_xl       = 50,
        ship_l        = 40,
        ship_m        = 30,
        ship_s        = 20,
        ship_xs       = 20,
        spacesuit     = 20,
        station       = 40,
        satellite     = 30,
        adv_satellite = 50,
        )
    Set_Ship_Radar_Ranges(
        ('type scout', 40),
        )

if 0:
    Remove_Travel_Drive()

if 0:
    Rebalance_Engines(purpose_speed_mults = None)
    Rebalance_Engines(race_speed_mults = None)

if 0:
    # Adjust speeds per ship class.
    # Note: vanilla averages and ranges are:    
    # xs: 130 (58 to 152)
    # s : 328 (71 to 612)
    # m : 319 (75 to 998)
    # l : 146 (46 to 417)
    # xl: 102 (55 to 164)
    # Try clamping variation to within 0.5x (mostly affects medium).
    Rescale_Ship_Speeds(match_all = ['type  scout' ],  average = 500, variation = 0.2)
    Rescale_Ship_Speeds(match_all = ['class ship_s'],  average = 400, variation = 0.5, match_none=['type  scout'])
    Rescale_Ship_Speeds(match_all = ['class ship_m'],  average = 300, variation = 0.5)
    Rescale_Ship_Speeds(match_all = ['class ship_l'],  average = 200, variation = 0.5)
    # Ignore the python (unfinished).
    Rescale_Ship_Speeds(match_all = ['class ship_xl'], average = 150, variation = 0.5,
                        match_none = ['name ship_spl_xl_battleship_01_a_macro'])


# Test the gui live editor, doing a transform before and after
# the patch application. Transform before should show up in the
# gui edit tables; transform after should show up in the final
# game files (along with the hand edits from the gui).
if 0:
    # Pre-editor should have halved damage, post-editor 2x damage,
    # compared to vanilla or the input extensions.
    #Adjust_Weapon_Damage(0.5)
    Apply_Live_Editor_Patches()
    #Adjust_Weapon_Damage(4)


if 0 or test_all:
    Adjust_Mission_Rewards(0.5)
    #Write_To_Extension()

# Ware transforms and printout.
if 0 or test_all:
    #Print_Ware_Stats('ware_stats_premod')
    Adjust_Ware_Price_Spread(
        ('id        energycells'       , 2  ),
        ('group     shiptech'          , 0.8),
        ('container ship'              , 1.5),
        ('tags      crafting'          , 0.2),
        ('*'                           , 0.1) )
    Adjust_Ware_Prices(
        ('container inventory'         , 0.5) )
    #Print_Ware_Stats('ware_stats_postmod')


# Weapon transforms and printout.
if 0 or test_all:
    #Print_Weapon_Stats('weapon_stats_premod')    
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
        ('tags small standard weapon'   , 2),
        ('tags missile'                 , 2),
        )
    #Print_Weapon_Stats('weapon_stats_postmod')
    

# Testing ways to call Jobs.
if 0 or test_all:    
    Adjust_Job_Count(
        ('id        masstraffic*'      , 0.5),
        ('tags      military destroyer', 2  ),
        ('tags      miner'             , 1.5),
        ('size      s'                 , 1.5),
        ('faction   argon'             , 1.2),
        ('*'                           , 1.1) )
    

# Simple cat unpack, allowing errors.
if 0 or test_all:
    Settings.allow_cat_md5_errors = True
    Cat_Unpack(
        source_cat_path = r'D:\X4\Pack',
        dest_dir_path   = r'D:\X4\UnPack',
        )


# Slightly more complex cat unpack.
if 0 or test_all:
    # Pick where to grab cats from.
    # Could also call this script from that directory and use relative
    #  paths for the cat file names.
    # Append the name of a cat file if wanting to unpack just one.
    cat_dir = Path(r'C:\Steam\SteamApps\common\X4 Foundations')

    # Pick the output folder. This script places it under the cat_dir.
    dest_dir_path = 'extracted'

    # Optional wildcard pattern to use for matching.
    # Just lua for quick test.
    include_pattern = ['*.lua']#['*.xml','*.xsd'] #,'*.xpl']
    exclude_pattern = None

    # Call the unpacker.
    Cat_Unpack(
        source_cat_path = cat_dir,
        #dest_dir_path   = cat_dir / dest_dir_path,
        dest_dir_path   = r'D:\X4_extracted',
        include_pattern = include_pattern,
        exclude_pattern = exclude_pattern
        )


# Cat pack test.
if 0 or test_all:
    # Pick where to grab files from.
    # Could also call this script from that directory and use relative
    # paths for the cat file names.
    dir_path = Path(r'C:\Steam\SteamApps\common\X4 Foundations\extensions\test_mod')

    # Optional wildcard pattern to use for matching.
    include_pattern = '*.xml'
    exclude_pattern = None

    # Name of the cat file.
    # For extensions, use prefix 'ext_' for patching game files, or
    # prefix 'subst_' for overwriting game files.
    cat_name = 'ext_01.cat'

    Cat_Pack(
        source_dir_path = dir_path,
        dest_cat_path   = dir_path / cat_name,
        include_pattern = include_pattern,
        exclude_pattern = exclude_pattern,
        generate_sigs   = True,
        separate_sigs   = True,
        )

    

# Run diff patch test on whatever xml.
if 0 or test_all:
    jobs_game_file = Framework.Load_File('libraries/jobs.xml')
    Framework.File_Manager.XML_Diff.Unit_Test(
        test_node      = jobs_game_file.Get_Root(), 
        # Shorten test count when in test_all mode.
        num_tests      = 100 if not test_all else 5, 
        edits_per_test = 5,
        rand_seed      = 1,
        )
    

# Manual testing of cat reading.
if 0 or test_all:
    Framework.File_Manager.File_System.Delayed_Init()
    # Test: open up a cat file, the one with text pages.
    cat09 = Framework.File_Manager.Cat_Reader.Cat_Reader(
        Settings.path_to_x4_folder / '09.cat')
    
    # Read the files from it.
    t44 = cat09.Read('t/0001-L044.xml')
    
    # Now try out the source reader.
    reader = Framework.File_Manager.Source_Reader.Source_Reader_class()
    reader.Init_From_Settings()
    t44_game_file = reader.Read('t/0001-L044.xml')
    jobs_game_file = reader.Read('libraries/jobs.xml')
    
    # Write to a new cat file.
    binary = t44_game_file.Get_Binary()
    cat_dir = Settings.path_to_x4_folder / 'extensions' / 'test_mod'
    if not cat_dir.exists():
        cat_dir.mkdir(parents = True)
    
    cat_writer = Framework.File_Manager.Cat_Writer.Cat_Writer(
        cat_path = cat_dir / 'test_01.cat')
    cat_writer.Add_File(t44_game_file)
    cat_writer.Write()


print('Test done')
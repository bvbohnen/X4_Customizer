'''
Place to test individual transforms.
Note: the newest tests tend to be near the top.
'''

from pathlib import Path

# Import all transform functions.
import Framework
from Plugins import *


Settings(
    path_to_x4_folder = r'C:\Steam\SteamApps\common\X4 Foundations',
    )

# For all tests to run, mostly to tease out exceptions after
# code changes.
test_all = 0

if 0:
    GUI.Start_GUI()
    
# Test the extension checker.
if 1 or test_all:
    Check_Extension('AAI-Deployables')
if 0 or test_all:
    # Alternatively, check everything (may take longer).
    Check_All_Extensions()


if 0:
    Color_Text((20005,3012,'C'))

if 0:
    # Live editor tree builders.
    edit_tree = Framework.Live_Editor.Get_Tree_View('weapons')


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
    Write_To_Extension()


# Ware transforms and printout.
if 0 or test_all:
    Print_Ware_Stats('ware_stats_premod')
    Adjust_Ware_Price_Spread(
        ('id        energycells'       , 2  ),
        ('group     shiptech'          , 0.8),
        ('container ship'              , 1.5),
        ('tags      crafting'          , 0.2),
        ('*'                           , 0.1) )
    Adjust_Ware_Prices(
        ('container inventory'         , 0.5) )    
    Print_Ware_Stats('ware_stats_postmod')


# Weapon transforms and printout.
if 0 or test_all:
    Print_Weapon_Stats('weapon_stats_premod')
    #Adjust_Weapon_Damage(1.2)
    #Adjust_Weapon_Damage(
    #    ('name weapon_tel_l_beam_01_mk1', 10),
    #    ('tags large standard turret'   , 5),
    #    ('tags medium missile weapon'   , 3),
    #    ('class bomblauncher'           , 20),
    #    ('*'                            , 1.2) )
    #Adjust_Weapon_Range(
    #    ('name weapon_tel_l_beam_01_mk1', 10),
    #    ('tags large standard turret'   , 5),
    #    ('tags medium missile weapon'   , 3),
    #    ('class bomblauncher'           , 20),
    #    ('*'                            , 1.2) )
    
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
    Print_Weapon_Stats('weapon_stats_postmod')
    

# Testing ways to call Jobs.
if 0 or test_all:
    #Adjust_Job_Count(
    #    ('id'     ,'masstraffic*'      , 0.5),
    #    ('tags'   ,'military destroyer', 2  ),
    #    ('tags'   ,'miner'             , 1.5),
    #    ('size'   ,'s'                 , 1.5),
    #    ('faction','argon'             , 1.2),
    #    ('id'     ,'*'                 , 1.1) )
    #
    #Adjust_Job_Count(
    #    ('id      : masstraffic*'      , 0.5),
    #    ('tags    : military destroyer', 2  ),
    #    ('tags    : miner'             , 1.5),
    #    ('size    : s'                 , 1.5),
    #    ('faction : argon'             , 1.2),
    #    ('*'                           , 1.1) )
    
    Adjust_Job_Count(
        ('id        masstraffic*'      , 0.5),
        ('tags      military destroyer', 2  ),
        ('tags      miner'             , 1.5),
        ('size      s'                 , 1.5),
        ('faction   argon'             , 1.2),
        ('*'                           , 1.1) )
    
    #Adjust_Job_Count(
    #    ('id        masstraffic*'      , 0.5),
    #    ('tags      military destroyer', 2  ),
    #    ('tags      miner'             , 1.5),
    #    ('size      s'                 , 1.5),
    #    ('faction   argon'             , 1.2),
    #                                     1.1 )


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
        exclude_pattern = exclude_pattern
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
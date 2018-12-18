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


# Documentation writers.
if 0 or test_all:
    Print_Weapon_Stats('weapon_stats_premod')
    Adjust_Weapon_Damage(('*',1.2))
    Adjust_Weapon_Damage(
        ('name weapon_tel_l_beam_01_mk1', 10),
        ('tags large standard turret'   , 5),
        ('tags medium missile weapon'   , 3),
        ('class mine'                   , 20),
        ('*'                            , 1.2) )
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


# Test the extension checker.
if 0 or test_all:
    Check_Extension('test_mod')
if 0 or test_all:
    # Alternatively, check everything (may take longer).
    Check_All_Extensions()

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
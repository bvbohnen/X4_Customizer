X4 Customizer 1.2
-----------------

This tool offers a framework for modding the X4 and extension game files programmatically, guided by user selected plugins (analyses, transforms, utilities). Features include:

  * Integrated catalog read/write support.
  * XML diff patch read/write support.
  * Automatic detection and loading of enabled extensions.
  * Three layer design: framework, plugins, and control script.
  * Framework handles the file system, plugin management, etc.
  * Plugins include analysis, transforms, and utilities.
  * Plugins operate on a user's unique mixture of mods, and can easily be rerun after game patches or mod updates.
  * Transforms can dynamically read and alter game files, instead of being limited to static changes like standard extensions.
  * Transforms are parameterized, to adjust their behavior.
  * Analyses can generate customized documentation.
  * Transformed files are written to a new or specified X4 extension.
  * Utilities offer extension error checking and cat pack/unpack support.

This tool is available as runnable Python source code (tested on 3.7 with the lxml package) or as a compiled executable for 64-bit Windows.

The control script:

  * This tool works by executing a user supplied python script specifying any system paths, settings, and desired plugins to run.

  * The key control script sections are:
    - "from Plugins import *" to make all major functions available.
    - Call Settings() to change paths and set non-default options; this can also be done through a setttings.json file.
    - Call a series of plugins with desired input parameters.
    - Call to Write_Extension() to write any modified files if transforms were used.
    
  * The quickest way to set up the control script is to copy and edit the "Scripts/Default_Script_template.py" file, renaming it to "Default_Script.py" for recognition by Launch_X4_Customizer.bat.

Usage for compiled version:

  * "Launch_X4_Customizer.bat [script_name] [args]"
    - Call from the command line for full options (-h for help), or run directly to execute the default script at "Scripts/Default_Script.py".
    - Script name may be given without a .py extension, and without a path if it is in the Scripts folder.
  * "Clean_X4_Customizer.bat [script_name] [args]"
    - Removes files generated in a prior run of the given or default control script.
  * "Check_Extensions.bat [args]"
    - Runs a command line script which will test extensions for errors, focusing on diff patching and dependency checks.
  * "Cat_Unpack.bat [args]"
    - Runs a command line script which unpacks catalog files.
  * "Cat_Pack.bat [args]"
    - Runs a command line script which packs catalog files.

Usage for Python source code:

  * "python Framework\Main.py [script_name] [args]"
    - This is the primary entry function for the python source code, and equivalent to using Launch_X4_Customizer.bat.

***

Example input file:

    '''
    Example for using the Customizer, setting a path to
    the X4 directory and running some simple transforms.
    '''
    
    # Import all transform functions.
    from Plugins import *
    
    # This could also be done in settings.json or through the gui.
    Settings(
        # Set the path to the X4 installation folder.
        path_to_x4_folder   = r'C:\Steam\SteamApps\common\X4 Foundations',
        # Set the path to the user documents folder.
        #path_to_user_folder = r'C:\Users\charname\Documents\Egosoft\X4\12345678',
        # Switch output to be in the user documents folder.
        output_to_user_extensions = True,
        )
    
    # Reduce mass traffic and increase military jobs.
    Adjust_Job_Count(
        ('id   masstraffic*', 0.5),
        ('tags military'   , 1.3)
        )
    
    # Make weapons in general, and turrets in particular, better.
    Adjust_Weapon_Damage(
        ('tags turret standard'   , 2),
        ('*'                      , 1.2),
        )
    Adjust_Weapon_Shot_Speed(
        ('tags turret standard'   , 2),
        ('*'                      , 1.2),
        )
    
    # Get csv and html documentation with weapon changes.
    Print_Weapon_Stats()
    
    # Write modified files.
    Write_To_Extension()

***

* Settings:


    This holds general settings and paths to control the customizer. Adjust these settings as needed prior to running the first plugin, using direct writes to attributes.
    
    Settings may be updated individually, or as arguments of a call to Settings, OR through a "settings.json" file in the top X4 Customizer folder (eg. where documentation resides). Any json settings will overwrite defaults, and be overwritten by settings in the control script. Changes made using the GUI will be applied to the json settings.
    
    Examples:
    * In the control script (prefix paths with 'r' to support backslashes):
    
          Settings.path_to_x4_folder   = r'C:\...'
          Settings.path_to_user_folder = r'C:\...'
          Settings(
               path_to_x4_folder   = r'C:\...',
               path_to_user_folder = r'C:\...'
               )
    
    * In settings.json (sets defaults for all scripts):
    
          {
            "path_to_x4_folder"        : "C:\...",
            "path_to_user_folder"      : "C:\...",
            "output_to_user_extensions": "true"
          }
    
    
    Paths:
    * path_to_x4_folder
      - Path to the main x4 folder.
      - Defaults to HOMEDRIVE/"Steam/steamapps/common/X4 Foundations"
    * path_to_user_folder
      - Path to the folder where user files are located.
      - Should include config.xml, content.xml, etc.
      - Defaults to HOMEPATH/"Documents/Egosoft/X4" or a subfolder with an 8-digit name.
    * path_to_source_folder
      - Optional path to a source folder that holds high priority source files, which will be used instead of reading the x4 cat/dat files.
      - For use when running plugins on manually edited files.
      - Defaults to None
    * allow_path_error
      - Bool, if True and the x4 or user folder path looks wrong, the customizer will still attempt to run (with a warning).
      - Defaults to False
          
    Input:
    * prefer_single_files
      - Bool, if True then loose files will be used before those in cat/dat files, otherwise cat/dat takes precedence.
      - Only applies within a single search location, eg. within an extension, within the source folder, or within the base X4 folder; a loose file in the source folder will still be used over those in the X4 folder regardless of setting.
      - Defaults to False
    * ignore_extensions
      - Bool, if True then extensions will be ignored, and files are only sourced from the source_folder or x4_folder.
      - Defaults to False
    * allow_cat_md5_errors
      - Bool, if True then when files extracted from cat/dat fail to verify their md5 hash, no exception will be thrown.
      - Defaults to False; consider setting True if needing to unpack incorrectly assembled catalogs.
    * ignore_output_extension
      - Bool, if True, the target extension being generated will have its prior content ignored.
      - Defaults to True; should only be set False if not running transforms and wanting to analyse prior output.
    
    Output:
    * extension_name
      - String, name of the extension being generated.
      - Spaces will be replaced with underscores for the extension id.
      - Defaults to 'X4_Customizer'
    * output_to_user_extensions
      - Bool, if True then the generated extension holding output files will be under <path_to_user_folder/extensions>.
      - Warning: any prior output on the original path will still exist, and is not cleaned out automatically at the time of this note.
      - Defaults to False, writing to <path_to_x4_folder/extensions>
    * output_to_catalog
      - Bool, if True then the modified files will be written to a single cat/dat pair, otherwise they are written as loose files.
      - Defaults to False
    * make_maximal_diffs
      - Bool, if True then generated xml diff patches will do the maximum full tree replacement instead of using the algorithm to find and patch only edited nodes.
      - Turn on to more easily view xml changes.
      - Defaults to False.
    
    Logging:
    * plugin_log_file_name
      - String, name a text file to write plugin output messages to; content depends on plugins run.
      - File is located in the output extension folder.
      - Defaults to 'plugin_log.txt'
    * customizer_log_file_name
      - String, name a json file to write customizer log information to, including a list of files written.
      - File is located in the output extension folder.
      - Defaults to 'customizer_log.json'
    * log_source_paths
      - Bool, if True then the path for any source files read will be printed in the plugin log.
      - Defaults to False
    * verbose
      - Bool, if True some extra status messages may be printed to the console.
      - Defaults to True
    
    Behavior:
    * disable_cleanup_and_writeback
      - Bool, if True then cleanup from a prior run and any final writes will be skipped.
      - For use when testing plugins without modifying files.
      - Defaults to False
    * skip_all_plugins
      - Bool, if True all plugins will be skipped.
      - For use during cleaning mode.
      - Defaults to False
    * developer
      - Bool, if True then enable some behavior meant just for development, such as leaving exceptions uncaught.
      - Defaults to False
    * disable_threading
      - Bool, if True then threads will not be used in the gui to call scripts and plugins. Will cause the gui to lock up during processing.
      - Intended for development use, to enable breakpoints during calls.
      - Defaults to False
    * use_scipy_for_scaling_equations
      - Bool, if True then scipy will be used to optimize scaling equations, for smoother curves between the boundaries.
      - If False or scipy is not found, then a simple linear scaling will be used instead.
      - Defaults to True
    * show_scaling_plots
      - Bool, if True and matplotlib and numpy are available, any generated scaling equations will be plotted (and their x and y vectors printed for reference). Close the plot window manually to continue plugin processing.
      - Primarily for development use.
      - Defaults to False
        


***

Analyses:

  * Print_Ware_Stats

    Gather up all ware statistics, and print them out. Produces csv and html output. Will include changes from enabled extensions.
    
    * file_name
      - String, name to use for generated files, without extension.
      - Defaults to "ware_stats".
        

  * Print_Weapon_Stats

    Gather up all weapon statistics, and print them out. Produces csv and html output. Will include changes from enabled extensions.
    
    * file_name
      - String, name to use for generated files, without extension.
      - Defaults to "weapon_stats".
    * return_tables
      - Bool, if True then this transform returns a list of tables (themselves lists of lists) holding the weapon data, and file writeback is skipped.
      - Defaults to False.
        


***

Director Transforms:

  * Adjust_Mission_Rewards

    Adjusts generic mission credit and notoriety rewards by a flat multiplier.
    
    * multiplier
      - Float, value to adjust rewards by.
    * adjust_credits
      - Bool, if True (default) changes the credit reward.
    * adjust_notoriety
      - Bool, if True (default) changes the notoriety reward.
        


***

Jobs Transforms:

  * Adjust_Job_Count

    Adjusts job ship counts using a multiplier, affecting all quota fields. Input is a list of matching rules, determining which jobs get adjusted.
    
    Resulting non-integer job counts are rounded, with a minimum of 1 unless the multiplier or original count were 0.
    
    * job_multipliers:
      - Tuples holding the matching rules and job count multipliers, ("key  value", multiplier).
      - The "key" specifies the job field to look up, which will be checked for a match with "value".
      - If a job matches multiple rules, the first match is used.
      - Supported keys:
        - 'id'      : Name of the job entry; supports wildcards.
        - 'faction' : The name of the faction.
        - 'tags'    : One or more tags, space separated.
        - 'size'    : The ship size suffix, 's','m','l', or 'xl'.
        - '*'       : Matches all jobs; takes no value term.
    
    Examples:
    
        Adjust_Job_Count(1.2)
        Adjust_Job_Count(
            ('id       masstraffic*'      , 0.5),
            ('tags     military destroyer', 2  ),
            ('tags     miner'             , 1.5),
            ('size     s'                 , 1.5),
            ('faction  argon'             , 1.2),
            ('*'                          , 1.1) )
    
        


***

Wares Transforms:

  * Common documentation

    Ware transforms will commonly use a group of matching rules to determine which wares get modified, and by how much.    
    
    * Matching rules:
      - These are tuples pairing a matching rule (string) with transform defined args, eg. ("key  value", arg0, arg1, ...).
      - The "key" specifies the ware field to look up, which will be checked for a match with "value".
      - If a ware matches multiple rules, the first match is used.
      - Supported keys:
        - 'id'        : Name of the ware entry; supports wildcards.
        - 'group'     : The ware group category.
        - 'container' : The ware container type.
        - 'tags'      : One or more tags, space separated.
          - See Print_Wares output for tag listings.
        - '*'         : Matches all wares; takes no value term.
    
    Examples:
    
        Adjust_Ware_Price_Spread(0.5)
        Adjust_Ware_Price_Spread(
            ('id        energycells'       , 2  ),
            ('group     shiptech'          , 0.8),
            ('container ship'              , 1.5),
            ('tags      crafting'          , 0.2),
            ('*'                           , 0.5) )
    
        

  * Adjust_Ware_Price_Spread

    Adjusts ware min to max price spreads. This primarily impacts trading profit. Spread will be limited to ensure 10 credits from min to max, to avoid impairing AI decision making.
    
    * match_rule_multipliers:
      - Series of matching rules paired with the spread multipliers to use.
        

  * Adjust_Ware_Prices

    Adjusts ware prices. This should be used with care when selecting production chain related wares.
        
    * match_rule_multipliers:
      - Series of matching rules paired with the spread multipliers to use.
        


***

Weapons Transforms:

  * Common documentation

    Weapon transforms will commonly use a group of matching rules to determine which weapons get modified, and by how much.   
    
    * Matching rules:
      - These are tuples pairing a matching rule (string) with transform defined args, eg. ("key  value", arg0, arg1, ...).
      - The "key" specifies the xml field to look up, which will be checked for a match with "value".
      - If a target object matches multiple rules, the first match is used.
      - If a bullet or missile is shared across multiple weapons, only the first matched weapon will modify it.
      - Supported keys for weapons:
        - 'name'  : Internal name of the weapon component; supports wildcards.
        - 'class' : The component class.
          - One of: weapon, missilelauncher, turret, missileturret, bomblauncher
          - These are often redundant with tag options.
        - 'tags'  : One or more tags for this weapon, space separated.
          - See Print_Weapon_Stats output for tag listings.
        - '*'     : Matches all wares; takes no value term.
    
    Examples:
    
        Adjust_Weapon_Range(1.5)
        Adjust_Weapon_Fire_Rate(
            ('name *_mk1', 1.1) )
        Adjust_Weapon_Damage(
            ('name weapon_tel_l_beam_01_mk1', 1.2),
            ('tags large standard turret'   , 1.5),
            ('tags medium missile weapon'   , 1.4),
            ('class bomblauncher'           , 4),
            ('*'                            , 1.1) )
    
        

  * Adjust_Weapon_Damage

    Adjusts damage done by weapons.  If multiple weapons use the same bullet or missile, it will be modified for only the first weapon matched.
    
    * match_rule_multipliers:
      - Series of matching rules paired with the damage multipliers to use.
        

  * Adjust_Weapon_Fire_Rate

    Adjusts weapon rate of fire. DPS remains constant.
    
    * match_rule_multipliers:
      - Series of matching rules paired with the RoF multipliers to use.
        

  * Adjust_Weapon_Range

    Adjusts weapon range. Shot speed is unchanged.
    
    * match_rule_multipliers:
      - Series of matching rules paired with the range multipliers to use.
        

  * Adjust_Weapon_Shot_Speed

    Adjusts weapon projectile speed. Range is unchanged.
    
    * match_rule_multipliers:
      - Series of matching rules paired with the speed multipliers to use.
        


***

Utilities:

  * Cat_Pack

    Packs all files in subdirectories of the given directory into a new catalog file.  Only subdirectories matching those used in the X4 file system are considered.
    
    * source_dir_path
      - Path to the directory holding subdirectories to pack.
      - Subdirectories are expected to match typical X4 folder names, eg. 'aiscripts','md', etc.
    * dest_cat_path
      - Path and name for the catalog file being generated.
      - Prefix the cat file name with 'ext_' when patching game files, or 'subst_' when overwriting game files.
    * include_pattern
      - String or list of strings, optional, wildcard patterns for file names to include in the unpacked output.
      - Eg. "*.xml" to unpack only xml files, "md/*" to  unpack only mission director files, etc.
      - Case is ignored.
    * exclude_pattern
      - String or list of strings, optional, wildcard patterns for file names to include in the unpacked output.
      - Eg. "['*.lua','*.dae']" to skip lua and dae files.
        

  * Cat_Unpack

    Unpack a single catalog file, or a group if a folder given. When a file is in multiple catalogs, the latest one in the list will be used. If a file is already present at the destination, it is compared to the catalog version and skipped if the same.
    
    * source_cat_path
      - Path to the catalog file, or to a folder.
      - When a folder given, catalogs are read in X4 priority order according to its expected names.
    * dest_dir_path
      - Path to the folder where unpacked files are written.
    * include_pattern
      - String or list of strings, optional, wildcard patterns for file names to include in the unpacked output.
      - Eg. "*.xml" to unpack only xml files
      - Case is ignored.
    * exclude_pattern
      - String or list of strings, optional, wildcard patterns for file names to include in the unpacked output.
      - Eg. "['*.lua']" to skip lua files.
    * allow_md5_errors
      - Bool, if True then files with md5 errors will be unpacked, otherwise they are skipped.
      - Such errors may arise from poorly constructed catalog files.
        

  * Check_All_Extensions

    Calls Check_Extension on all enabled extensions, looking for errors. Returns True if no errors found, else False.
        

  * Check_Extension

    Checks an extension for xml diff patch errors and dependency errors. Performs two passes: scheduling this extension as early as possible (after its dependencies), and as late as possible (after all other extensions that can go before it). Problems are printed to the console. Returns True if no errors found, else False.
    
    * extension_name
      - Name of the extension being checked.
      - This should match an enabled extension name findable on the normal search paths set in Settings.
        

  * Write_To_Extension

    Write all currently modified game files to the extension folder. Existing files at the location written on a prior call will be cleared out. Content.xml will have dependencies added for files modified from existing extensions.
    
    * skip_content
      - Bool, if True then the content.xml file will not be written.
      - Defaults to False.
        


***

Change Log:
 * 0.9
   - Initial version, quick adaption of X3_Customizer for X4.
   - Added first transform, Adjust_Job_Count.
 * 0.9.1
   - Major framework development.
   - Settings overhauled for X4.
   - Source_Reader overhauled, now finds and pulls from extensions.
   - Xml diff patch support added for common operations, merging extensions and base files prior to transforms. Pending further debug.
 * 0.9.2
   - Fix for when the user content.xml isn't present.
 * 0.9.3
   - Major development of diff patch generation, now using close to minimal patch size instead of full tree replacement, plus related debug of the patch application code.
   - Framework largely feature complete, except for further debug.
 * 0.9.4
   - Applied various polish: documentation touchup, gathered misc file_manager functions into a class, etc.
   - Added dependency nodes to the output extension.
 * 0.10
   - Major reorganization, moving transforms into a separate Plugins package that holds runtime script imports.
   - Added utilities for simple cat operations.
   - Added Print_Weapon_Stats.
 * 0.10.1
   - Added workaround for a bug in x4 catalogs that sometimes use an incorrect empty file hash; also added an optional setting to allow hash mismatches to support otherwise problematic catalogs.
 * 0.10.2
   - Bug fix in cat unpacker.
 * 0.11
   - Added plugins Check_Extension, Check_All_Extensions.
   - Added passthrough argparse support, along with command line callable scripts for extension check and cat pack/unpack.
   - Swapped the default script from User_Transforms to Default_Script.
 * 0.11.1
   - Added support for case insensitive path matching, instead of requiring a match to the catalogs.
 * 1.0
   - Scattered framework refinements.
   - Added Adjust_Weapon_Damage.
   - Added Adjust_Weapon_Fire_Rate.
   - Added Adjust_Weapon_Range.
   - Added Adjust_Weapon_Shot_Speed.
   - Refined Print_Weapon_Stats further.
   - Refined matching rule format for Adjust_Job_Count.
 * 1.1
   - Worked around lxml performance issue with index based xpaths, to speed up diff patch verification.
   - Added Print_Ware_Stats.
   - Added Adjust_Ware_Prices.
   - Added Adjust_Ware_Price_Spread.
   - Added Adjust_Mission_Rewards.
 * 1.1.1
   - Bugfix for ambiguous xpaths that still require indexes, and cleaned up quotes to avoid nesting double quotes.
 * 1.2
   - Added the initial Gui, featuring: python syntax and plugin highlighter, documentation viewer, settings editor, script launcher, preliminary weapon info viewer; plus niceties like changing font, remembering layout, and processing on a background thread.
   - Some unfortunate file size bloat in the compiled version.
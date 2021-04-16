X4 Customizer 1.24.4
-----------------

This tool offers a framework for modding the X4 and extension game files programmatically, guided by user selected plugins (analyses, transforms, utilities). Features include:

  * GUI to improve accessibility, designed using Qt.
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

This tool is available as runnable Python source code (tested on 3.7 with the lxml and PyQt5 packages) or as a compiled executable for 64-bit Windows.


Running the compiled release:

  * "Start_Gui.bat"
    - This starts up the Customizer GUI.
    - Equivelent to running "bin/X4_Customizer.exe"
  * "Run_Script.bat [script_name] [args]"
    - This runs a script directly without loading the GUI.
    - Call from the command line for full options (-h for help), or run directly to execute the default script at "Scripts/Default_Script.py".
    - Script name may be given without a .py extension, and without a path if it is in the Scripts folder.
  * "Clean_Script.bat [script_name] [args]"
    - Removes files generated in a prior run of the given or default control script.
  * "Check_Extensions.bat [args]"
    - Runs a command line script which will test extensions for errors, focusing on diff patching and dependency checks.
  * "Cat_Unpack.bat [args]"
    - Runs a command line script which unpacks catalog files.
  * "Cat_Pack.bat [args]"
    - Runs a command line script which packs catalog files.

Running the Python source code:

  * "python Framework\Main.py [script_name] [args]"
    - This is the primary entry function for the python source code, and equivalent to X4_Customizer.exe.
    - When no script is given, this launches the GUI.


GUI sections:

  * "Script" displays the current control script, alongside documentation on available plugins.  Drag plugins to the script window for a fast templated copy.  Scripts can be opened or saved, and default to the Scripts folder.  Syntax is highlighted as Python code. Press "Run Script" to run the current script; other tabs displaying game information will be updated automatically with the script changes.

  * "Config" allows customization of settings. These are saved to a json file in the main tool directory when the window closes.

  * The "Edit" menu opens up tabs with editable tables of game object information. Objects may be displayed individually or in a table. See further below for details. All edits made are saved in a json file in the main tool directory when a script is run or the window closes.

  * The "Utilities" menu currently has one option, the Virtual File System. This shows which game files the Customizer has loaded, patched from other extensions (blue), or modified itself (red). Right click a file for the option to view its contents.

  * The File Viewer tabs display individual file contents, in their pre-diff patch, post-diff patch, and post-customizer versions. Select two versions and press "Compare" to get a summary on lines changed. Press "Reload" to force the file to be reloaded from disk, including any diff patches; this may be used to test customize diff patch files in another extension.

The control script:

  * This tool is primarily controlled by a user supplied python script which will specify the desired plugins to run. Generally this acts as a build script to create a custom extension.

  * The key control script sections are:
    - "from Plugins import *" to make all major functions available.
    - Optionally call Settings() to change paths and set non-default options; this can also be done through a setttings.json file or through the GUI.
    - Call a series of plugins with desired input parameters; see plugin documentation for available options.
    - Call Write_Extension() to write out any modified files, formatted as diff patches.
    
  * Scripts of varying complexity are available in the Scripts folder, and may act as examples.
    

GUI based object editing:

  * In addition to script selected transforms, game information can be directly edited for select objects on the appropriate edit tabs. Tabs include "weapons", "wares", and others as time goes on.

  * Press "Refresh" on the tab to load the game information.
  * The "vanilla" column shows the object field values for the base version of the game files loaded.
  * The "patched" column shows field values after other extensions have had their diff patches applied.
  * The "edited" column is where you may change values manually.
  * Running a script that includes the Apply_Live_Editor_Patches plugin will apply edits to the game files.
  * The "current" column will show the post-script field values, and mainly exists for verification of hand edits as well as other transform changes.


Writing custom edit code:

  * This framework may be used to write custom file editing routines.
  * The general steps are: use Load_File() to obtain the patched file contents, use Get_Root() to obtain the current file root xml (which includes any prior transform changes), make any custom edits with the help of the lxml package, and to put the changes back using Update_Root().
  * Existing plugins offer examples of this approach.
  * Edits made using the framework will automatically support diff patch generation.
  * Non-xml file support is more rudimentary, operating on file binary data pending further support for specific formats.
  * Routines may be written as plugin functions and put up for inclusion in later Customizer releases to share with other users.

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
    
        # Set the path to the user documents folder, if the auto-find
        # doesn't work. Commented out here.
        #path_to_user_folder = r'C:\Users\charname\Documents\Egosoft\X4\12345678',
    
        # Optionally change the output extension name. Default is "x4_customizer".
        extension_name = 'x4_customizer'
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
    
    Settings may be updated individually, or as arguments of a call to Settings, or through a "settings.json" file in the top X4 Customizer folder (eg. where documentation resides). Any json settings will overwrite defaults, and be overwritten by settings in the control script. Changes made using the GUI will be applied to the json settings.
    
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
      - Not needed in general use.
      - All files from the source folder will be copied into the extension.
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
      - Bool, if True then all extensions will be ignored, and files are only sourced from the source_folder or x4_folder.
      - Defaults to False
    * extension_whitelist
      - String, optional, semicolon separated list of lowercase extension folder names to consider loading (if found and enabled).
      - If not given, all extension folders are checked, except those in the blacklist.
    * extension_blacklist
      - String, optional, semicolon separated list of lowercase extension folder names to always ignore.
    * allow_cat_md5_errors
      - Bool, if True then when files extracted from cat/dat fail to verify their md5 hash, no exception will be thrown.
      - Defaults to False; consider setting True if needing to unpack incorrectly assembled catalogs.
    * ignore_output_extension
      - Bool, if True, the target extension being generated will have its prior content ignored (this run works on the original files, and not those changes made last run).
      - Defaults to True; should only be set False if not running transforms and wanting to analyse prior output.
    * X4_exe_name
      - String, name of the X4.exe file, to be used when sourcing the file for any exe transforms (if used), assumed to be in the x4 folder.
      - Defaults to "X4.exe", but may be useful to change based on the source exe file for transforms, eg. "X4_nonsteam.exe", "X4_steam.exe", or similar.
      - Note: the modified exe is written to the x4 folder with a ".mod.exe" extension, and will not be removed on subsequent runs even if they do not select any exe editing transforms. If wanting this to work with steam, then the X4.exe may need to be replaced with this modified exe manually.
    
    Output:
    * extension_name
      - String, name of the extension being generated.
      - Spaces will be replaced with underscores for the extension id.
      - A lowercase version of this will be used for the output folder name.
      - Defaults to 'x4_customizer'
    * output_to_user_extensions
      - Bool, if True then the generated extension holding output files will be under <path_to_user_folder/extensions>.
      - Warning: any prior output on the original path will still exist, and is not cleaned out automatically at the time of this note.
      - Defaults to False, writing to <path_to_x4_folder/extensions>
    * path_to_output_folder
      - Optional, Path to the location to write the extension files to, instead of the usual X4 or user documents extensions folders.
      - This is the parent directory to the extension_name folder.
    * output_to_catalog
      - Bool, if True then the modified files will be written to a single cat/dat pair, otherwise they are written as loose files.
      - Defaults to False
    * generate_sigs
      - Bool, if True then dummy signature files will be created.
      - Defaults to True.
    * make_maximal_diffs
      - Bool, if True then generated xml diff patches will do the maximum full tree replacement instead of using the algorithm to find and patch only edited nodes.
      - Turn on to more easily view xml changes.
      - Defaults to False.
    * forced_xpath_attributes
      - String, optional comma separate list of XML node attributes which, if found when constructing xpaths for output diffs, will be included in the xpath regardless of if they are needed.
      - Example: "id,name" will always include "id" and "name" attributes of elements in the xpath.
      - Also supports child node or attributes referenced using a relative xpath. Example: "parts/part/uv_animations/uv_animation" to require a uv_animation great-great-grandchild element, or "component/@ref" to include the "ref" attribute of a "component" child.
      - Can be used to make xpaths more specific, and more likely to break if an unknown extension is applied before the output extension (eg. when the customizer output is distributed to other users).
    * root_file_tag
      - String, extra tag added to names of modified files in the root folder and not placed in an extension, eg. X4.exe, to avoid overwriting the originals.
      - Defaults to ".mod", eg. "X4.mod.exe".
    
    Logging:
    * live_editor_log_file_name
      - String, name a json file which the live editor (tracking hand edits in the gui) will save patches to, and reload from.
      - Patches will capture any hand edits made by the user.
      - File is located in the output extension folder.
      - Defaults to 'live_editor_log.json'
    * plugin_log_file_name
      - String, name of a text file to write plugin output messages to; content depends on plugins run.
      - File is located in the output extension folder.
      - Defaults to 'plugin_log.txt'
    * customizer_log_file_name
      - String, name a json file to write customizer log information to, including a list of files written, information that will be loaded on the next run to guide the file handling logic.
      - File is located in the output extension folder.
      - Defaults to 'customizer_log.json'
    * log_source_paths
      - Bool, if True then the path for any source files read will be printed in the plugin log.
      - Defaults to False
    * verbose
      - Bool, if True some extra status messages may be printed to the console.
      - Defaults to True
    
    Behavior:
    * show_tab_close_button
      - Bool, if True then a gui tab close button will be shown.
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
    * profile
      - Bool, if True then some extra profiling of customizer operations is performed, and times printed. For use during development.
      - Defaults to False.
    * disable_threading
      - Bool, if True then threads will not be used in the gui to call scripts and plugins. Will cause the gui to lock up during processing.
      - Intended for development use, to enable breakpoints during calls.
      - Defaults to False
    * use_scipy_for_scaling_equations
      - Bool, if True then scipy will be used to optimize scaling equations, for smoother curves between the boundaries.
      - If False or scipy is not found, then a simple linear scaling will be used instead.
      - May be unused currently.
      - Defaults to True
    * show_scaling_plots
      - Bool, if True and matplotlib and numpy are available, any generated scaling equations will be plotted (and their x and y vectors printed for reference). Close the plot window manually to continue plugin processing.
      - Primarily for development use.
      - May be unused currently.
      - Defaults to False
        


***

Analyses:

  * Print_Object_Stats

    Print out statistics for objects of a given category. This output will be similar to that viewable in the gui live editor pages, except formed into one or more tables. Produces csv and html output. Will include changes from enabled extensions.
    
    * category
      - String, category name of the objects, eg. 'weapons'.
    * file_name
      - String, name to use for generated files, without extension.
    * version
      - Optional string, version of the objects to use.
      - One of ['vanilla','patched','current','edited'].
      - Defaults to 'current'.
        

  * Print_Ship_Speeds

    Prints out speeds of various ships, under given engine assumptions, to the plugin log.
    
    * use_arg_engine
      - Bool, if True then Argon engines will be assumed for all ships instead of their faction engines.
    * use_split_engine
      - Bool, if True then Split engines will be assumed.
      - This will tend to give high estimates for ship speeds, eg. mk4 engines.
        

  * Print_Ship_Stats

    Gather up all ship statistics, and print them out. This is a convenience wrapper around Print_Object_Stats, filling in the category and a default file name.
    
    * file_name
      - String, name to use for generated files, without extension.
      - Defaults to "ship_stats".
    * version
      - Optional string, version of the objects to use.
        

  * Print_Ware_Stats

    Gather up all ware statistics, and print them out. This is a convenience wrapper around Print_Object_Stats, filling in the category and a default file name.
    
    * file_name
      - String, name to use for generated files, without extension.
      - Defaults to "ware_stats".
    * version
      - Optional string, version of the objects to use.
        

  * Print_Weapon_Stats

    Gather up all weapon statistics, and print them out. This is a convenience wrapper around Print_Object_Stats, filling in the category and a default file name.
    
    * file_name
      - String, name to use for generated files, without extension.
      - Defaults to "weapon_stats".
    * version
      - Optional string, version of the objects to use.
        


***

Adjust Transforms:

  * Common documentation

    Ship transforms will commonly use a group of matching rules to determine which ships get modified, and by how much.   
    
    * Matching rules:
      - These are tuples pairing a matching rule (string) with transform defined args, eg. ("key  value", arg0, arg1, ...).
      - The "key" specifies the xml field to look up, which will be checked for a match with "value".
      - If a target object matches multiple rules, the first match is used.
      - Supported keys for ships:
        - 'name'    : Internal name of the ship macro; supports wildcards.
        - 'purpose' : The primary role of the ship. List of purposes:
          - mine
          - trade
          - build
          - fight
        - 'type'    : The ship type. List of types:
          - courier, resupplier, transporter, freighter, miner, largeminer, builder
          - scout, interceptor, fighter, heavyfighter
          - gunboat, corvette, frigate, scavenger
          - destroyer, carrier, battleship
          - xsdrone, smalldrone, police, personalvehicle, escapepod, lasertower
        - 'class'   : The class of ship. List of classes:
          - 'ship_xs'
          - 'ship_s'
          - 'ship_m'
          - 'ship_l'
          - 'ship_xl'
          - 'spacesuit'
        - '*'       : Matches all ships; takes no value term.
    
    Examples:
    
        Adjust_Ship_Speed(1.5)
        Adjust_Ship_Speed(
            ('name ship_xen_xl_carrier_01_a*', 1.2),
            ('class ship_s'                  , 2.0),
            ('type corvette'                 , 1.5),
            ('purpose fight'                 , 1.2),
            ('*'                             , 1.1) )
    
        

  * Adjust_Ship_Crew_Capacity

    Adjusts the crew capacities of ships. Note: crewmen contributions to ship combined skill appears to adjust downward based on max capacity, so increasing capacity can lead to a ship performing worse (unverified).
    
    * match_rule_multipliers:
      - Series of matching rules paired with the multipliers to use.
        

  * Adjust_Ship_Drone_Storage

    Adjusts the drone ("unit") storage of ships.
    
    * match_rule_multipliers:
      - Series of matching rules paired with the multipliers to use.
        

  * Adjust_Ship_Hull

    Adjusts the hull values of ships.
    
    * match_rule_multipliers:
      - Series of matching rules paired with the multipliers to use.
        

  * Adjust_Ship_Missile_Storage

    Adjusts the missile storage of ships.
    
    * match_rule_multipliers:
      - Series of matching rules paired with the multipliers to use.
        

  * Adjust_Ship_Speed

    Adjusts the speed and acceleration of ships, in each direction.
    
    * match_rule_multipliers:
      - Series of matching rules paired with the multipliers to use.
        

  * Adjust_Ship_Turning

    Adjusts the turning rate of ships, in each direction.
    
    * match_rule_multipliers:
      - Series of matching rules paired with the multipliers to use.
        

  * Set_Default_Radar_Ranges

    Sets default radar ranges.  Granularity is station, type of satellite, or per ship size.  Ranges are in km, eg. 40 for vanilla game defaults of non-satellites. Note: ranges below 40km will affect when an unidentified object becomes identified, but objects will still show up out to 40km.
            
    Supported arguments:
    * ship_s
    * ship_m
    * ship_l
    * ship_xl
    * spacesuit
    * station
    * satellite
    * adv_satellite
        

  * Set_Ship_Radar_Ranges

    Sets radar ranges. Defaults are changed per object class. Note: ranges below 40km will affect when an unidentified object becomes identified, but objects will still show up out to 40km.
            
    * ship_match_rule_ranges:
      - Series of matching rules paired with the new ranges to apply for individual ships.
      - Ranges are in km.
        


***

Director Transforms:

  * Adjust_Mission_Reward_Mod_Chance

    Adjusts generic mission chance to reward a mod instead of credits. The vanilla chance is 2% for a mod, 98% for credits.
    
    Pending update for x4 3.0+.
    
    * mod_chance
      - Int, the new percent chance of rewarding a mod.
      - Should be between 0 and 100.
        

  * Adjust_Mission_Rewards

    Adjusts generic mission credit and notoriety rewards by a flat multiplier.
    
    * multiplier
      - Float, value to adjust rewards by.
    * adjust_credits
      - Bool, if True (default) changes the credit reward.
    * adjust_notoriety
      - Bool, if True (default) changes the notoriety reward.
        


***

Exe Transforms:

  * High_Precision_Systemtime

    Changes the player.systemtime property to use a higher precision underlying timer, where a printed "second" will actually have a stepping of 100 ns. Useful for performance profiling of code blocks.
    
    Underlying precision comes from Windows GetSystemTimePreciseAsFileTime, which is presumably as accurate as its 100 ns unit size.
    
    Time will roll over roughly every 7 minutes, going back to 1970, due to limitations of the underlying string format functions.
    
    For short measurements, roughly 8 ms or less, just the lower part of the timer may be used, up to hour: player.systemtime.{'%H,%M,%S'}. For longer measurements, this needs to expand into the day field and account for leap years: player.systemtime.{'%G,%j,%H,%M,%S'}.
    
    As these are strings, conversion to an actual time relies on processing outside of the normal script engine, eg. in lua. Note: 1972 was a leap year, and every 4 after, which needs to be considered for full accuracy.
        

  * Remove_Modified

    Partially removes the modified flag, eg. from the top menu. Written for Windows v3.10 exe.
        

  * Remove_Sig_Errors

    Suppresses file sigature errors from printing to the debug log, along with file-not-found errors. Written for Windows v3.10 exe.
        
    TODO: pending x4 4.0 update.
        


***

Jobs Transforms:

  * Adjust_Job_Count

    Adjusts job ship counts using a multiplier, affecting all quota fields. Input is a list of matching rules, determining which jobs get adjusted.
    
    Resulting non-integer job counts are rounded, with a minimum of 1 unless the multiplier or original count were 0.
    
    * job_multipliers
      - Tuples holding the matching rules and job count multipliers, ("key  value", multiplier).
      - The "key" specifies the job field to look up, which will be checked for a match with "value".
      - If a job matches multiple rules, the first match is used.
      - Subordinates will never be matched except by an exact 'id' match, to avoid accidental job multiplication (eg. XL ship with a wing of L ships which have wings of M ships which have wings of S ships).
      - Supported keys:
        - 'id'      : Name of the job entry; supports wildcards for non-wings.
        - 'faction' : The name of the faction.
        - 'tags'    : One or more tags, space separated.
        - 'size'    : The ship size suffix, 'xs','s','m','l', or 'xl'.
        - '*'       : Matches all non-wing jobs; takes no value term.
    
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

Live_Editor Transforms:

  * Apply_Live_Editor_Patches

    This will apply all patches created by hand through the live editor in the GUI. This should be called no more than once per script, and currently should be called before any other transforms which might read the edited values. Pending support for running some transforms prior to hand edits.
    
    * file_name
      - Optional, alternate name of a json file holding the Live_Editor generated patches file.
      - Default uses the name in Settings.
        


***

Rescale Transforms:

  * Common documentation

    Ship transforms will commonly use a group of matching rules to determine which ships get modified, and by how much.   
    
    * Matching rules:
      - These are tuples pairing a matching rule (string) with transform defined args, eg. ("key  value", arg0, arg1, ...).
      - The "key" specifies the xml field to look up, which will be checked for a match with "value".
      - If a target object matches multiple rules, the first match is used.
      - Supported keys for ships:
        - 'name'    : Internal name of the ship macro; supports wildcards.
        - 'purpose' : The primary role of the ship. List of purposes:
          - mine
          - trade
          - build
          - fight
        - 'type'    : The ship type. List of types:
          - courier, resupplier, transporter, freighter, miner, largeminer, builder
          - scout, interceptor, fighter, heavyfighter
          - gunboat, corvette, frigate, scavenger
          - destroyer, carrier, battleship
          - xsdrone, smalldrone, police, personalvehicle, escapepod, lasertower
        - 'class'   : The class of ship. List of classes:
          - 'ship_xs'
          - 'ship_s'
          - 'ship_m'
          - 'ship_l'
          - 'ship_xl'
          - 'spacesuit'
        - '*'       : Matches all ships; takes no value term.
    
    Examples:
    
        Adjust_Ship_Speed(1.5)
        Adjust_Ship_Speed(
            ('name ship_xen_xl_carrier_01_a*', 1.2),
            ('class ship_s'                  , 2.0),
            ('type corvette'                 , 1.5),
            ('purpose fight'                 , 1.2),
            ('*'                             , 1.1) )
    
        

  * Adjust_Ship_Cargo_Capacity

    Adjusts the cargo capacities of matching ships.  If multiple ships use the same storage macro, it is modified by an average of the ship multipliers.
        
    Args are one or more dictionaries with these fields, where matching rules are applied in order, with a ship being grouped by the first rule it matches:
    
    * multiplier
      - Float, how much to multiply current cargo capacity by.
    * match_any
      - List of matching rules. Any ship matching any of these is included, if not part of match_none.
    * match_all
      - List of matching rules. Any ship matching all of these is included, if not part of match_none.
    * match_none
      - List of matching rules. Any ship matching any of these is excluded.
    * cargo_tag
      - Optional, tag name of cargo types to modify.
      - Expected to be one of: 'solid', 'liquid', 'container'.
      - If not given, all cargo types are modified.
    * skip
      - Optional, bool, if True then this group is not edited.
      - Can be used in early matching rules to remove ships from all later matching rules.
            
    Example:
    ```
    Adjust_Ship_Cargo_Capacity(
        {'match_all' : ['purpose mine'],  'multiplier' : 2,},
        {'match_all' : ['purpose trade'], 'multiplier' : 1.5},
        )
    ```
        

  * Rescale_Ship_Speeds

    Rescales the speeds of different ship classes, centering on the give target average speeds. Ships are assumed to be using their fastest race engines. Averaged across all ships of the rule match.
    
    Cargo capacity of traders and miners is adjusted to compensate for speed changes, so they move a similar amount of wares. If multiple ships use the same cargo macro, it is adjusted by an average of their speed adjustments.
        
    Args are one or more dictionaries with these fields, where matching rules are applied in order, with a ship being grouped by the first rule it matches:
    
    * average
      - Float, the new average speed to adjust to.
      - If None, keeps the original average.
    * variation
      - Float, less than 1, how much ship speeds are allowed to differ from the average relative to the average.
      - If None, keeps the original variation.
      - If original variation is less than this, it will not be changed.
      - Only applies strictly to 90% of ships; 10% are treated as outliers, and will have their speed scaled similarly but will be outside this band.
      - Eg. 0.5 means 90% of ships will be within +/- 50% of their group average speed.
    * match_any
      - List of matching rules. Any ship matching any of these is included, if not part of match_none.
    * match_all
      - List of matching rules. Any ship matching all of these is included, if not part of match_none.
    * match_none
      - List of matching rules. Any ship matching any of these is excluded.
    * use_arg_engine
      - Bool, if True then Argon engines will be assumed for all ships instead of their faction engines.
    * use_split_engine
      - Bool, if True then Split engines will be assumed.
      - This will tend to give high estimates for ship speeds, eg. mk4 engines.
    * skip
      - Optional, bool, if True then this group is not edited.
      - Can be used in early matching rules to remove ships from all later matching rules.
            
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
        


***

Scale_Sector_Size Transforms:

  * Scale_Sector_Size

    Change the size of the maps by moving contents (zones, etc.) closer together or further apart. Note: this will require a new game to take effect, as positions become part of a save file.
    
    * scaling_factor
      - Float, how much to adjust distances by.
      - Eg. 0.5 to cut sector size roughly in half.
    * scaling_factor_2
      - Float, optional, secondary scaling factor to apply to large sectors.
      - If not given, scaling_factor is used for all sectors.
    * transition_size_start
      - Int, sector size at which to start transitioning from scaling_factor to scaling_factor_2.
      - Defaults to 200000.
      - Sectors smaller than this will use scaling_factor.
    * transition_size_end
      - Int, optional, sector size at which to finish transitioning to scaling_factor_2.
      - Defaults to 400000 (400 km).
      - Sectors larger than this will use scaling_factor_2.
      - Sectors of intermediate size have their scaling factor interpolated.
    * recenter_sectors
      - Adjust objects in a sector to approximately place the coreposition near 0,0,0.
      - Defaults False.
      - In testing, this makes debugging harder, and may lead to unwanted results.  Pending further testing to improve confidence.
    * num_steps
      - Int, over how many movement steps to perform the scaling.
      - Higher step counts take longer to process, but each movement is smaller and will better detect objects getting too close to each other.
      - Recommend lower step counts when testing, high step count for a final map.
      - Defaults to 10.
    * remove_ring_highways
      - Bool, set True to remove the ring highways.
    * remove_nonring_highways
      - Bool, set True to remove non-ring highways.
    * extra_scaling_for_removed_highways
      - Float, extra scaling factor to apply to sectors that had highways removed.
      - Defaults to 0.7.
    * scale_regions
      - Bool, if resource and debris regions should be scaled as well.
      - May be slightly off from sector scalings, since many regions are shared between sectors.
      - Defaults True.
    * move_free_ships
      - Bool, if ownerless ships spawned at game start should be moved along with the other sector contents.
      - May impact difficulty of finding these ships.
      - Defaults True.
    * debug
      - Bool, if True then write runtime state to the plugin log.
        


***

Scripts Transforms:

  * Adjust_OOS_Damage

    Adjusts all out-of-vision damage-per-second by a multiplier. For instance, if OOS combat seems to run too fast, it can be multiplied by 0.5 to slow it down by half.
        
    * multiplier
      - Float, how much to multiply damage by.
        

  * Disable_AI_Travel_Drive

    Disables usage of travel drives for all ai scripts. When applied to a save, existing move orders may continue to use travel drive until they complete.
        

  * Increase_AI_Script_Waits

    Increases wait times in ai scripts, to reduce their background load and improve performance.  Separate modifiers are applied to "in-vision" and "out-of-vision" parts of scripts. Expected to have high impact on fps, at some cost of ai efficiency.
    
    * oos_multiplier
      - Float, how much to multiply OOS wait times by. Default is 2.
    * oos_seta_multiplier
      - Float, alternate OOS multiplier to apply if the player is in SETA mode. Default is 4.
      - Eg. if multiplier is 2 and seta_multiplier is 4, then waits will be 2x longer when not in SETA, 4x longer when in SETA.
    * oos_max_wait
      - Float, optional, the longest OOS wait that this multiplier can achieve, in seconds.
      - Defaults to 15.
      - If the original wait is longer than this, it will be unaffected.
    * iv_multiplier
      - As above, but for in-vision.
      - Defaults to 1x, eg. no change.
    * iv_seta_multiplier
      - As above, but for in-vision.
      - Defaults to 1x, eg. no change.
    * iv_max_wait
      - As above, but for in-vision.
      - Defaults to 5.
    * filter
      - String, possibly with wildcards, matching names of ai scripts to modify; default is plain '*' to match all aiscripts.
      - Example: "*trade.*" to modify only trade scripts.
    * include_extensions
      - Bool, if True then aiscripts added by extensions are also modified.
      - Defaults False.
    * skip_combat_scripts
      - Bool, if True then scripts which control OOS damage application will not be modified. Otherwise, they are modified and their attack strength per round is increased to match the longer wait times.
      - Defaults False.
    * skip_mining_scripts
      - Bool, if True then scripts which control OOS mining rates will not be modified. Currently has no extra code to adjust mining rates when scaled.
      - Defaults True.
      - Note currently expected to signicantly matter with max_wait of 15s, since OOS mining waits at least 16s between gathers.
        


***

Surface_Elements Transforms:

  * Rebalance_Engines

    Rebalances engine speed related properties across purposes and maker races. Race balance set relative to argon engines of a corresponding size, purpose, mark 1. Higher marks receive the same scaling as their mark 1 counterpart. Purpose balance set relative to allround engines of a corresponding size and mark.
    
    * race_speed_mults
      - Dict, keyed by race name, with relative  multipliers for engine speed properties: 'thrust', 'boost', 'travel'.
      - Relative to corresponding argon engines.
      - Set to None to disable race rebalancing.
      - Defaults tuned to vanilla medium mark 1 combat engines, and will nearly reproduce the vanilla medium engine values (with discrepencies for other sizes):
        ```
        race_speed_mults = {
            'argon'   : {'thrust' : 1,    'boost'  : 1,    'boost_time' : 1,   'travel' : 1    },
            'paranid' : {'thrust' : 1.03, 'boost'  : 1.03, 'boost_time' : 1.2, 'travel' : 0.90 },
            'split'   : {'thrust' : 1.35, 'boost'  : 1.08, 'boost_time' : 1.2, 'travel' : 0.843},
            'teladi'  : {'thrust' : 0.97, 'boost'  : 0.97, 'boost_time' : 1,   'travel' : 0.97 },
            }
        ```
    * purpose_speed_mults
      - Dict, keyed by engine purpose name, with relative  multipliers for engine speed properties: 'thrust', 'boost', 'travel'.
      - Purposes are 'combat', 'allround', and 'travel'.
      - Set to None to disable purpose rebalancing.
      - Defaults tuned to vanilla medium mark 1 argon engines, and will nearly reproduce the vanilla medium engine values (with discrepencies for other sizes):
        ```
        purpose_speed_mults = {
            'allround' : {'thrust' : 1,    'boost'  : 1,    'boost_time' : 1,    'travel' : 1    },
            'combat'   : {'thrust' : 1.05, 'boost'  : 1,    'boost_time' : 0.89, 'travel' : 1.43 },
            'travel'   : {'thrust' : 1,    'boost'  : 0.75, 'boost_time' : 1.33, 'travel' : 0.57 },
            }
        ```
    * adjust_cargo
      - Bool, if True then trader and miner ship cargo bays will be adjusted in inverse of the ship's travel thrust change, to maintain roughly the same transport of cargo/time. Assumes trade ships spend 50% of their time in travel mode, and mining ships spend 10%.
      - Defaults False.
      - May cause oddities when applied to an existing save.
        

  * Remove_Engine_Travel_Bonus

    Removes travel mode bonus from all engines by setting the speed multiplier to 1 and engage time to 0.
        


***

Text Transforms:

  * Color_Text

    Applies coloring to selected text nodes, for all versions of the text found in the current X4 files. Note: these colors will override any prior color in effect, and will return to standard text color at the end of the colored text node.
    
    * page_t_colors
      - One or more groups of (page id, text id, color code) to apply.
    
    Example:
    
        Color_Text(
            (20005,1001,'B'),
            (20005,3012,'C'),
            (20005,6046,'Y'),
            )
    
        


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
    
    Args are one or more dictionaries with these fields, where matching rules are applied in order, with a weapon being grouped by the first rule it matches. If a bullet or missile is used by multiple weapons in different match groups, their adjustments will be averaged.
    
    A dictionary has the following shared fields:
    
    * match_any, match_all, match_none
      - Lists of matching rules. Weapon is selected if matching nothing from match_none, and anything from match_any or everything from match_all.
    * skip
      - Optional, bool, if True then this group is not edited.
      - Can be used as a way to blacklist weapons.
          
    Matching rules are strings with the following format:
    * The "key" specifies the xml field to look up, which will be checked for a match with "value".
    * Supported keys for weapons:
      - 'name'  : Internal name of the weapon component; supports wildcards.
      - 'class' : The component class.
        - One of: weapon, missilelauncher, turret, missileturret, bomblauncher
        - These are often redundant with tag options.
      - 'tags'  : One or more tags for this weapon, space separated.
        - See Print_Weapon_Stats output for tag listings.
      - '*'     : Matches all wares; takes no value term.
    
    As a special case, a single multiplier may be given, to be applied to all weapons (lasers,  missiles, etc.)
    
        

  * Adjust_Weapon_Damage

    Adjusts damage done by weapons.  If multiple weapons use the same bullet or missile, it will be modified by an average of the users.
        
    Args are one or more dictionaries with these fields, where matching rules are applied in order, with a ship being grouped by the first rule it matches:
    
    * multiplier
      - Float, amount to multiply damage by.
    * match_any, match_all, match_none
      - Lists of matching rules. Weapon is selected if matching nothing from match_none, and anything from match_any or everything from match_all.        
    * skip
      - Optional, bool, if True then this group is not edited.
        

  * Adjust_Weapon_Fire_Rate

    Adjusts weapon rate of fire. DPS and heat/sec remain constant. Time between shots in a burst and time between bursts are affected equally for burst weapons.  If multiple matched weapons use the same bullet or missile, the modifier will be averaged between them.
            
    Args are one or more dictionaries with these fields, where matching rules are applied in order, with a ship being grouped by the first rule it matches:
    
    * multiplier
      - Float, amount to multiply fire rate by.
      - If 1, the weapon is not modified.
    * min
      - Float, optional, minimum fire rate allowed by an adjustment, in shots/second.
      - Default is None, no minimum is applied.
    * match_any, match_all, match_none
      - Lists of matching rules. Weapon is selected if matching nothing from match_none, and anything from match_any or everything from match_all.        
    * skip
      - Optional, bool, if True then this group is not edited.
        

  * Adjust_Weapon_Range

    Adjusts weapon range. Shot speed is unchanged.
        
    Args are one or more dictionaries with these fields, where matching rules are applied in order, with a ship being grouped by the first rule it matches:
    
    * multiplier
      - Float, amount to multiply damage by.
    * match_any, match_all, match_none
      - Lists of matching rules. Weapon is selected if matching nothing from match_none, and anything from match_any or everything from match_all.        
    * skip
      - Optional, bool, if True then this group is not edited.
        

  * Adjust_Weapon_Shot_Speed

    Adjusts weapon projectile speed. Range is unchanged.
        
    Args are one or more dictionaries with these fields, where matching rules are applied in order, with a ship being grouped by the first rule it matches:
    
    * multiplier
      - Float, amount to multiply damage by.
    * match_any, match_all, match_none
      - Lists of matching rules. Weapon is selected if matching nothing from match_none, and anything from match_any or everything from match_all.        
    * skip
      - Optional, bool, if True then this group is not edited.
        


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
    * generate_sigs
      - Bool, if True then dummy signature files will be created.
    * separate_sigs
      - Bool, if True then any signatures will be moved to a second cat/dat pair suffixed with .sig.
        

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

    Checks an extension for xml diff patch errors and dependency errors. Problems are printed to the console. Returns True if no errors found, else False.
    
    Performs up to three passes that adjust extension loading order: in alphabetical folder order, as early as possible (after its dependencies), and as late as possible (after all other extensions that can go before it).
    
    * extension_name
      - Name (folder) of the extension being checked.
      - May be given in original or lower case.
      - This should match an enabled extension name findable on the normal search paths set in Settings.
    * check_other_orderings
      - Bool, if True then the 'earliest' and 'latest' loading orders will be checked, else only 'alphabetical' is checked.
      - These are recommended to identify where dependencies should be added to extensions, to protect against other extensions changing their folder name and thereby their loading order.
      - Defaults to False, to avoid printing errors that won't be present with the current extension order.
    * return_log_messages
      - Bool, if True then instead of the normal True/False return, this will instead return a list of logged lines that contain any error messages.
      - Does not stop the normal message Prints.
        

  * Generate_Diff

    Generate a diff of changes between two xml files, creating a diff patch.
    
    * original_file_path
      - Path to the original xml files that act as the baseline.
    * modified_file_path
      - Path to the modified versions of the xml files.
    * output_file_path
      - Path to write the diff patches to.
    * skip_unchanged
      - Bool, skip output for files that are unchanged (removing any existing diff patch).
      - Default will generate empty diff patches.
    * verbose
      - Bool, print the path of the outputs on succesful writes.
        

  * Generate_Diffs

    Generate diffs for changes between two xml containing folders, creating diff patches.
    
    * original_dir_path
      - Path to the original xml file that acts as the baseline.
    * modified_dir_path
      - Path to the modified version of the xml file.
    * output_dir_path
      - Path to write the diff patch to.
    * skip_unchanged
      - Bool, skip output for files that are unchanged (removing any existing diff patch).
      - Default will generate empty diff patches.
    * verbose
      - Bool, print the path of the outputs on succesful writes.
        

  * Write_Modified_Binaries

    Write out any modified binaries.  These are placed in the main x4 folder, not in an extension.
        

  * Write_To_Extension

    Write all currently modified game files to the extension folder. Existing files at the location written on a prior call will be cleared out. Content.xml will have dependencies added for files modified from existing extensions.
    
    * skip_content
      - Bool, if True then the content.xml file will not be written.
      - Content is automatically skipped if Make_Extension_Content_XML was already called.
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
 * 1.3
   - Added the Live_Editor, an extension for supporting gui based hand editing of game files.
   - Gui refined further, and live editor support added.
   - Weapon tables updated for the live editor.
   - Swapped the release exe to run without a console, and fixed a bug when running from outside the main directory.
 * 1.3.1
   - Fix a couple small bugs that crept in.
 * 1.4
   - Added wares to the GUI live editor.
   - Support added in the GUI for changing a laser's bullet.
   - Used several tricks to accelerate wares.xml parsing (multithreading, xpath bypassing, etc.) to accelerate Print_Ware_Stats and GUI display.
   - Background work to reorganize gui code for easy tab expansion, and tab thread requests will now queue up for service.
   - Further development of the Live_Editor, supporting object tree views and dynamically updating inter-object references.
   - Various debugging.
 * 1.4.1
   - Fixed bug when changing paths in the gui.
   - Added Shields and Bullets tabs to the gui.
 * 1.5
   - Redesign of the gui Live_Editor tabs.
   - Added dynamic tab support: create, move, remove, restore.
   - Tabs will load game information automatically if paths are set up.
   - Added editing support for engines, scanners, storage, dockingbays.
   - Various other polish, mostly in the gui.
 * 1.6
   - Added support for basic ship editing.
   - Added a virtual file system tab to the gui.
   - Added file viewing tabs to the gui, with xml syntax highlighting and diff comparison output.
 * 1.6.1
   - Bug fixes for hidden tabs and a threading conflicts.
 * 1.6.2
   - Added coloring to the VFS tree view.
   - Added more fields for missile editing.
   - Bug fix for tabs forgetting order between sessions.
   - Swapped around inter-tab signalling and added more threading safety.
 * 1.7
   - Added multi-object table views to the gui object editor tabs.
 * 1.7.1
   - Fixed an issue with lxml find/findall not properly handling xpaths using indexes after predicates.
 * 1.8
   - Tested with the top 100 Nexus mods to guide various debug and refinement.
   - Added the Extensions tab to the gui, allowing viewing, enabling, disabling, and testing of extensions.
   - Added the Color_Text transform.
 * 1.8.1
   - Fixed a couple crash bugs when script or configuration tabs are hidden.
 * 1.9
   - Added Adjust_Ship_Speed.
   - Added Adjust_Mission_Reward_Mod_Chance.
   - Fixed a couple crash bugs.
 * 1.9.1
   - Replaced excess commas in csv files with semicolons.
   - Added a missing comma that cause index and extension folders to be ignored when looking for loose files.
   - Gui script window will now check for external changes to the script.
   - Script editor swapped to using tab and shift-tab for indentation.
 * 1.10
   - Added Gui option to save xml files from the VFS tab.
 * 1.11
   - Support all file types in the VFS viewer, with extract support.
 * 1.12
   - Fixed an xml diff bug and reduced warnings, so that the Split dlc loads cleanly.
   - Improved catalog unpack plugin's support for extensions.
   - Adjusted newline encoding of packed dat files to better match the egosoft tools.
 * 1.13
   - Added Scale_Sector_Size transform.
   - Added path_to_output_folder setting.
   - Added symlink resolution when determining if an extension is the current output target.
   - Removes empty folders when cleaning up files from a prior run.
   - Added safety check for a file already existing on an output path.
   - Minor bug fixes.
 * 1.14
   - Added wildcards to capture extension objects when listing weapons, shields, etc. in the gui editor.
   - Fixed bug in weapon rate of fire calc for burst weapons in the editor.
 * 1.15
   - Added Generate_Diff support, for auto diff generation between two files.
   - Improved diff patch support for comment nodes.
 * 1.15.1
   - Removed dependency on Settings paths when using Generate_Diff.
 * 1.15.2
   - Diff patcher now ignores namespaced attribute changes due to lack of support or necessity on x4 side.
   - Extension checker now better supports mods patching other mods.
 * 1.15.3
   - Tweaked Adjust_Job_Count to generally ignore subordinate counts, to avoid ship counts multiplying to very large numbers.
 * 1.16
   - Tweaked xpath generation to select more human pleasing attributes.
   - Added support for generating dummy sig files.
   - Added Remove_Sig_Errors exe transform.
 * 1.16.1
   - Improved handling of extensions with no defined id.
 * 1.17
   - Added High_Precision_Systemtime transform for code profiling.
   - Various refinements to Scale_Sector_Size.
   - Fixed gui crash bug when saving files before Settings path polishing.
 * 1.17.1
   - Fixed bug in generate_diffs that could miss files with just attribute changes.
 * 1.17.2
   - Performance optimizations for XML_Diff.Make_Patch, Find_Files, and gui VFS.
   - Improved quality of generate_diff output patches.
 * 1.18
   - Added support for forcing xpath attributes in generated diff patches.
   - Added transforms: Increase_AI_Script_Waits, Adjust_OOS_Damage, Adjust_Ship_Turning, Adjust_Ship_Hull, Adjust_Ship_Crew_Capacity, Adjust_Ship_Drone_Storage, Adjust_Ship_Missile_Storage.
 * 1.18.1
   - Bug fix when forced xpath attributes not specified.
   - Bug fixed when copying files at the path_to_source_folder.
 * 1.18.2
   - Changed user folder check to look for uidata.xml instead of config.xml.
   - Added support for 0001.xml language files. Text lookups should now be done through File_System.Read_Text.
   - Added better support for XR ship pack file naming and quirks.
   - Refinements to Scale_Sector_Size size estimation of sectors.
 * 1.18.3
   - Improved support for extensions patching other extensions.
   - Added better support for VRO quirks.
 * 1.18.4
   - Tweaked Generate_Diffs script mixed file/folder error check.
 * 1.18.5
   - Teaked Cat_Pack to include "extensions" subfolder files.
 * 1.19
   - Added forced xpath attribute support for matching child nodes and attributes.
   - New parameters for Scale_Sector_Size.
   - Changed parameters for Increase_AI_Script_Waits to support also scaling in-vision waits.
   - Added transforms: Rescale_Ship_Speeds, Remove_Engine_Travel_Bonus, Rebalance_Engines, Adjust_Engine_Boost_Duration, Adjust_Engine_Boost_Speed.
   - Added several example scripts.
 * 1.20
   - Added automatic packing of replacement files into subst cat/dats.
   - Scale_Sector_Size includes split start locations.
   - Switched Rescale_Ship_Speeds to handle multiple groups in one call.
   - Added Adjust_Ship_Cargo_Capacity.
   - Switched weapon transforms to new style match rule args.
   - Changed engine scaline transforms to adjust additional boost/thrust speed over normal speed, instead of total boost/thrust speed.
 * 1.21
   - Added gui tab close button. Can be disabled in settings.
   - Set shader files to go into a subst catalog.
   - Added automatic ship storage capacity adjustment to Rescale_Ship_Speeds and Rebalance_Engines for traders and miners.
 * 1.22
   - Added Settings.root_file_tag.
   - Adjusted cat unpacker to no longer treat egosoft's bad empty file hashes as changed files.
   - Updates to content.xml generation, and support for updating an existing content file with new dependencies.
 * 1.23
   - Added extension_whitelist and extension_blacklist settings to control which extensions are loaded by the customizer.
   - Fixed content.xml not being generated, introduced by 1.22.
 * 1.23.1
   - Added python configparser module to the packaged customizer.
 * 1.24
   - Added Enable_Windows_File_Cache exe transform (experimental).
   - Refinements to Check_Extensions and extension error handling.
   - Added basic diff patch support for xpaths in parentheses.
 * 1.24.1
   - More consistent lowercasing of file paths for better linux support.
 * 1.24.2
   - Stopped content.xml being packed in a catalog when output_to_catalog is enabled.
 * 1.24.3
   - Suppressed error check on SV/CoH dlcs for duplicate background jpgs.
   - Added shader files to default Cat_Unpack.
 * 1.24.4
   - Updated Remove_Sig_Errors for x4 4.0.
   - Removed Enable_Windows_File_Cache, no longer applies to x4 4.0.
   - Various minor fixes for CoH.
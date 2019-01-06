X4 Customizer 1.7
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
        # Set the path to the user documents folder.
        #path_to_user_folder = r'C:\Users\charname\Documents\Egosoft\X4\12345678',
        # Switch output to be in the user documents folder if needed.
        output_to_user_extensions = False,
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

Live_Editor Transforms:

  * Apply_Live_Editor_Patches

    This will apply all patches created by hand through the live editor in the GUI. This should be called no more than once per script, and currently should be called before any other transforms which might read the edited values. Pending support for running some transforms prior to hand edits.
    
    * file_name
      - Optional, alternate name of a json file holding the Live_Editor generated patches file.
      - Default uses the name in Settings.
        


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
X4 Customizer 1.24.8
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

Full documentation found in Documentation.md, describing settings and transform parameters.

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

Analyses:

  * Print_Object_Stats

    Print out statistics for objects of a given category. This output will be similar to that viewable in the gui live editor pages, except formed into one or more tables. Produces csv and html output. Will include changes from enabled extensions.

  * Print_Ship_Speeds

    Prints out speeds of various ships, under given engine assumptions, to the plugin log.

  * Print_Ship_Stats

    Gather up all ship statistics, and print them out. This is a convenience wrapper around Print_Object_Stats, filling in the category and a default file name.

  * Print_Ware_Stats

    Gather up all ware statistics, and print them out. This is a convenience wrapper around Print_Object_Stats, filling in the category and a default file name.

  * Print_Weapon_Stats

    Gather up all weapon statistics, and print them out. This is a convenience wrapper around Print_Object_Stats, filling in the category and a default file name.


***

Adjust Transforms:


  * Adjust_Ship_Crew_Capacity

    Adjusts the crew capacities of ships. Note: crewmen contributions to ship combined skill appears to adjust downward based on max capacity, so increasing capacity can lead to a ship performing worse (unverified).

  * Adjust_Ship_Drone_Storage

    Adjusts the drone ("unit") storage of ships.

  * Adjust_Ship_Hull

    Adjusts the hull values of ships.

  * Adjust_Ship_Missile_Storage

    Adjusts the missile storage of ships.

  * Adjust_Ship_Speed

    Adjusts the speed and acceleration of ships, in each direction.

  * Adjust_Ship_Turning

    Adjusts the turning rate of ships, in each direction.

  * Set_Default_Radar_Ranges

    Sets default radar ranges.  Granularity is station, type of satellite, or per ship size.  Ranges are in km, eg. 40 for vanilla game defaults of non-satellites. Note: ranges below 40km will affect when an unidentified object becomes identified, but objects will still show up out to 40km.

  * Set_Ship_Radar_Ranges

    Sets radar ranges. Defaults are changed per object class. Note: ranges below 40km will affect when an unidentified object becomes identified, but objects will still show up out to 40km.


***

Director Transforms:

  * Adjust_Mission_Reward_Mod_Chance

    Adjusts generic mission chance to reward a mod instead of credits. The vanilla chance is 2% for a mod, 98% for credits.

  * Adjust_Mission_Rewards

    Adjusts generic mission credit and notoriety rewards by a flat multiplier.


***

Exe Transforms:

  * High_Precision_Systemtime

    Changes the player.systemtime property to use a higher precision underlying timer, where a printed "second" will actually have a stepping of 100 ns. Useful for performance profiling of code blocks.

  * Remove_Modified

    Partially removes the modified flag, eg. from the top menu. Written for Windows v3.10 exe.

  * Remove_Sig_Errors

    Suppresses file sigature errors from printing to the debug log, along with file-not-found errors. Written for Windows v3.10 exe.


***

Jobs Transforms:

  * Adjust_Job_Count

    Adjusts job ship counts using a multiplier, affecting all quota fields. Input is a list of matching rules, determining which jobs get adjusted.


***

Live_Editor Transforms:

  * Apply_Live_Editor_Patches

    This will apply all patches created by hand through the live editor in the GUI. This should be called no more than once per script, and currently should be called before any other transforms which might read the edited values. Pending support for running some transforms prior to hand edits.


***

Rescale Transforms:


  * Adjust_Ship_Cargo_Capacity

    Adjusts the cargo capacities of matching ships.  If multiple ships use the same storage macro, it is modified by an average of the ship multipliers.

  * Rescale_Ship_Speeds

    Rescales the speeds of different ship classes, centering on the give target average speeds. Ships are assumed to be using their fastest race engines. Averaged across all ships of the rule match.


***

Scale_Sector_Size Transforms:

  * Scale_Sector_Size

    Change the size of the maps by moving contents (zones, etc.) closer together or further apart. Note: this will require a new game to take effect, as positions become part of a save file.


***

Scripts Transforms:

  * Adjust_OOS_Damage

    Adjusts all out-of-vision damage-per-second by a multiplier. For instance, if OOS combat seems to run too fast, it can be multiplied by 0.5 to slow it down by half.

  * Disable_AI_Travel_Drive

    Disables usage of travel drives for all ai scripts. When applied to a save, existing move orders may continue to use travel drive until they complete.

  * Increase_AI_Script_Waits

    Increases wait times in ai scripts, to reduce their background load and improve performance.  Separate modifiers are applied to "in-vision" and "out-of-vision" parts of scripts. Expected to have high impact on fps, at some cost of ai efficiency.


***

Surface_Elements Transforms:

  * Rebalance_Engines

    Rebalances engine speed related properties across purposes and maker races. Race balance set relative to argon engines of a corresponding size, purpose, mark 1. Higher marks receive the same scaling as their mark 1 counterpart. Purpose balance set relative to allround engines of a corresponding size and mark.

  * Remove_Engine_Travel_Bonus

    Removes travel mode bonus from all engines by setting the speed multiplier to 1 and engage time to 0.


***

Text Transforms:

  * Color_Text

    Applies coloring to selected text nodes, for all versions of the text found in the current X4 files. Note: these colors will override any prior color in effect, and will return to standard text color at the end of the colored text node.


***

Wares Transforms:


  * Adjust_Ware_Price_Spread

    Adjusts ware min to max price spreads. This primarily impacts trading profit. Spread will be limited to ensure 10 credits from min to max, to avoid impairing AI decision making.

  * Adjust_Ware_Prices

    Adjusts ware prices. This should be used with care when selecting production chain related wares.


***

Weapons Transforms:


  * Adjust_Weapon_Damage

    Adjusts damage done by weapons.  If multiple weapons use the same bullet or missile, it will be modified by an average of the users.

  * Adjust_Weapon_Fire_Rate

    Adjusts weapon rate of fire. DPS and heat/sec remain constant. Time between shots in a burst and time between bursts are affected equally for burst weapons.  If multiple matched weapons use the same bullet or missile, the modifier will be averaged between them.

  * Adjust_Weapon_Range

    Adjusts weapon range. Shot speed is unchanged.

  * Adjust_Weapon_Shot_Speed

    Adjusts weapon projectile speed. Range is unchanged.


***

Utilities:

  * Cat_Pack

    Packs all files in subdirectories of the given directory into a new catalog file.  Only subdirectories matching those used in the X4 file system are considered.

  * Cat_Unpack

    Unpack a single catalog file, or a group if a folder given. When a file is in multiple catalogs, the latest one in the list will be used. If a file is already present at the destination, it is compared to the catalog version and skipped if the same.

  * Check_All_Extensions

    Calls Check_Extension on all enabled extensions, looking for errors. Returns True if no errors found, else False.

  * Check_Extension

    Checks an extension for xml diff patch errors and dependency errors. Problems are printed to the console. Returns True if no errors found, else False.

  * Generate_Diff

    Generate a diff of changes between two xml files, creating a diff patch.

  * Generate_Diffs

    Generate diffs for changes between two xml containing folders, creating diff patches.

  * Write_Modified_Binaries

    Write out any modified binaries.  These are placed in the main x4 folder, not in an extension.

  * Write_To_Extension

    Write all currently modified game files to the extension folder. Existing files at the location written on a prior call will be cleared out. Content.xml will have dependencies added for files modified from existing extensions.


***

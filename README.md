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

Analyses:

  * Print_Ware_Stats

    Gather up all ware statistics, and print them out. Produces csv and html output. Will include changes from enabled extensions.

  * Print_Weapon_Stats

    Gather up all weapon statistics, and print them out. Produces csv and html output. Will include changes from enabled extensions.


***

Director Transforms:

  * Adjust_Mission_Rewards

    Adjusts generic mission credit and notoriety rewards by a flat multiplier.


***

Jobs Transforms:

  * Adjust_Job_Count

    Adjusts job ship counts using a multiplier, affecting all quota fields. Input is a list of matching rules, determining which jobs get adjusted.


***

Wares Transforms:


  * Adjust_Ware_Price_Spread

    Adjusts ware min to max price spreads. This primarily impacts trading profit. Spread will be limited to ensure 10 credits from min to max, to avoid impairing AI decision making.

  * Adjust_Ware_Prices

    Adjusts ware prices. This should be used with care when selecting production chain related wares.


***

Weapons Transforms:


  * Adjust_Weapon_Damage

    Adjusts damage done by weapons.  If multiple weapons use the same bullet or missile, it will be modified for only the first weapon matched.

  * Adjust_Weapon_Fire_Rate

    Adjusts weapon rate of fire. DPS remains constant.

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

    Checks an extension for xml diff patch errors and dependency errors. Performs two passes: scheduling this extension as early as possible (after its dependencies), and as late as possible (after all other extensions that can go before it). Problems are printed to the console. Returns True if no errors found, else False.

  * Write_To_Extension

    Write all currently modified game files to the extension folder. Existing files at the location written on a prior call will be cleared out. Content.xml will have dependencies added for files modified from existing extensions.


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
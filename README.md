X4 Customizer 0.9.3
-----------------

Current status: functional, most features in place, but still in beta testing.

This tool will programatically apply a variety of user selected transforms to X4 game files, optionally pre-modded. Features include:

 * Integrated catalog read/write support.
 * Basic XML diff patch support.
 * Automatic detection and loading of enabled extensions.
 * Framework for developing modular, customizable transforms of varying complexity.
 * Transforms can dynamically read and alter game files, instead of being limited to static changes like standard extensions.
 * Transforms operate on a user's unique mixture of mods, and can easily be rerun after game patches or mod updates.
 * Changes are written to a new or specified extension.

This tool is available as platform portable Python source code (tested on 3.7 with the lxml package) or as a compiled executable for 64-bit Windows.

The control script:

  * This tool works by executing a user supplied python script specifying any system paths, settings, and desired transforms to run.

  * The key control script sections are:
    - "from X4_Customizer import *" to make all transform functions available.
    - Call Settings() to change paths and set non-default options.
    - Call a series of transforms.
    
  * The quickest way to set up the control script is to copy and edit the "input_scripts/User_Transforms_template.py" file, renaming it to "User_Transforms.py" for recognition by Launch_X4_Customizer.bat.

Usage for compiled releases:

  * "Launch_X4_Customizer.bat <optional path to control script>"
    - Call from the command line for full options (-h for help), or run directly to execute the default script at "input_scripts/User_Transforms.py".
  * "Clean_X4_Customizer.bat <optional path to control script>"
    - Removes files generated in a prior run of the given or default3 control script.

Usage for Python source code:

  * "python X4_Customizer\Main.py <optional path to control script>"
    - This is the primary entry function for the python source code.
    - Add the "-default_script" option to behave like the bat launcher.
    - Control scripts may freely use any python packages, instead of being limited to those included with the release.
  * "python X4_Customizer\Make_Documentation.py"
    - Generates updated documentation for this project, as markdown formatted files README.md and Documentation.md.
  * "python X4_Customizer\Make_Executable.py"
    - Generates a standalone executable and support files, placed in the bin folder. Requires the PyInstaller package be available. The executable will be created for the system it was generated on.
  * "python X4_Customizer\Make_Release.py"
    - Generates a zip file with all necessary binaries, source files, and example scripts for general release.


Full documentation found in Documentation.md.

***

Example input file:

    '''
    Example for using the Customizer, setting a path to
    the X4 directory and running some simple transforms.
    '''
    
    # Import all transform functions.
    from X4_Customizer import *
    
    Settings(
        # Set the path to the X4 installation folder.
        path_to_x4_folder   = r'C:\Steam\SteamApps\common\X4 Foundations',
        # Set the path to the user documents folder.
        path_to_user_folder = r'C:\Users\charname\Documents\Egosoft\X4\12345678',
        # Switch output to be in the user documents folder.
        output_to_user_extensions = True,
        )
    
    # Reduce mass traffic and increase military jobs.
    Adjust_Job_Count(
        ('id','masstraffic', 0.5),
        ('tag','military', 2)
        )


***

Job Transforms:

 * Adjust_Job_Count

      Adjusts job ship counts using a multiplier, affecting all quota fields. Caller provided matching rules determine which jobs get adjusted. Resulting non-integer job counts are rounded, with a minimum of 1 unless the multiplier or original count were 0.


***

Change Log:
 * 0.9
   - Initial version, after a long evening of adapting X3_Customizer for X4.
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
X4 Customizer 0.10
-----------------

Current status: functional, framework being refined.

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

This tool is available as platform portable Python source code (tested on 3.7 with the lxml package) or as a compiled executable for 64-bit Windows.

The control script:

  * This tool works by executing a user supplied python script specifying any system paths, settings, and desired plugins to run.

  * The key control script sections are:
    - "from Plugins import *" to make all major functions available.
    - Call Settings() to change paths and set non-default options.
    - Call a series of plugins with desired input parameters.
    - Call to Write_Extension() to write any modified files if transforms were used.
    
  * The quickest way to set up the control script is to copy and edit the "Scripts/User_Transforms_template.py" file, renaming it to "User_Transforms.py" for recognition by Launch_X4_Customizer.bat.

Usage for compiled releases:

  * "Launch_X4_Customizer.bat <optional path to control script>"
    - Call from the command line for full options (-h for help), or run directly to execute the default script at "Scripts/User_Transforms.py".
  * "Clean_X4_Customizer.bat <optional path to control script>"
    - Removes files generated in a prior run of the given or default3 control script.

Usage for Python source code:

  * "python Framework\Main.py <optional path to control script>"
    - This is the primary entry function for the python source code.
    - Add the "-default_script" option to behave like the bat launcher.
    - Control scripts may freely use any python packages, instead of being limited to those included with the release.
  * "python Framework\Make_Documentation.py"
    - Generates updated documentation for this project, as markdown formatted files README.md and Documentation.md.
  * "python Framework\Make_Executable.py"
    - Generates a standalone executable and support files, placed in the bin folder. Requires the PyInstaller package be available. The executable will be created for the system it was generated on.
  * "python Framework\Make_Release.py"
    - Generates a zip file with all necessary binaries, source files, and example scripts for general release.

Full documentation found in Documentation.md, describing settings and transform parameters.

***

Example input file:

    '''
    Example for using the Customizer, setting a path to
    the X4 directory and running some simple transforms.
    '''
    
    # Import all transform functions.
    from Plugins import *
    
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
    
    # Write modified files.
    Write_To_Extension()


***

Analyses:

  * Print_Weapon_Stats

    Gather up all weapon statistics, and print them out. Currently only supports csv output. Will include changes from enabled extensions.


***

Job Transforms:

  * Adjust_Job_Count

    Adjusts job ship counts using a multiplier, affecting all quota fields. Input is a list of matching rules, determining which jobs get adjusted.


***

Catalog Utilities:

  * Cat_Pack

    Packs all files in subdirectories of the given directory into a new catalog file.  Only subdirectories matching those used in the X4 file system are considered.

  * Cat_Unpack

    Unpack a single catalog file, or a group if a folder given. When a file is in multiple catalogs, the latest one in the list will be used. If a file is already present at the destination, it is compared to the catalog version and skipped if the same.


***

Write_To_Extension Utilities:

  * Write_To_Extension

    Write all currently modified game files to the extension folder. Existing files at the location written on a prior call will be cleared out. Content.xml will have dependencies added for files modified from existing extensions.


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
 * 0.9.4
   - Applied various polish: documentation touchup, gathered misc file_manager functions into a class, etc.
   - Added dependency nodes to the output extension.
 * 0.10
   - Major reorganization, moving transforms into a separate Plugins package that holds runtime script imports.
   - Added utilities for simple cat operations.
   - Added Print_Weapon_Stats.
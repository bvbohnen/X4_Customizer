X4 Customizer 0.10.1
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

* Settings:


    This holds general settings and paths to control the customizer. Adjust these settings as needed prior to running the first plugin, using direct writes to attributes.
    
    Settings may be updated individually, or as arguments of a call to Settings. Examples:
    * Settings.path_to_x4_folder   = 'C:\...'
    * Settings.path_to_user_folder = 'C:\...'
    * Settings( path_to_x4_folder = 'C:\...', path_to_user_folder = 'C:\...')
    
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
    
    Output:
    * extension_name
      - String, name of the extension being generated.
      - Spaces will be replaced with underscores for the extension id.
      - Defaults to 'X4_Customizer'
    * output_to_user_extensions
      - Bool, if True then the generated extension holding output files will be under <path_to_user_folder/extensions>.
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
      - Defaults to False
    
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

  * Print_Weapon_Stats

    Gather up all weapon statistics, and print them out. Currently only supports csv output. Will include changes from enabled extensions.
        


***

Job Transforms:

  * Adjust_Job_Count

    Adjusts job ship counts using a multiplier, affecting all quota fields. Input is a list of matching rules, determining which jobs get adjusted.
    
    Resulting non-integer job counts are rounded, with a minimum of 1 unless the multiplier or original count were 0.
    
    * job_factors:
      - Tuples holding the matching rules and job count  multipliers, (match_key, match_value, multiplier).
      - The match_key is one of a select few fields from the job nodes, against which the match_value will be compared.
      - Multiplier is an int or float, how much to adjust the job count by.
      - If a job matches multiple entries, the first match is used.
      - Supported keys:
        - 'faction' : The name of the category/faction.
        - 'tag'     : A possible value in the category/tags list.
        - 'id'      : Name of the job entry, partial matches supported.
        - '*'       : Wildcard, always matches, takes no match_value.
    
    Example:
    
        Adjust_Job_Count(
            ('id','masstraffic', 0.5),
            ('tag','military', 2),
            ('tag','miner', 1.5),
            ('faction','argon', 1.2),
            ('*', 1.1) )
    
        


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
      - Path to the folder to place unpacked files.
    * include_pattern
      - String or list of strings, optional, wildcard patterns for file names to include in the unpacked output.
      - Eg. "*.xml" to unpack only xml files, "md/*" to  unpack only mission director files, etc.
      - Case is ignored.
    * exclude_pattern
      - String or list of strings, optional, wildcard patterns for file names to include in the unpacked output.
      - Eg. "['*.lua','*.dae']" to skip lua and dae files.
        

  * Write_To_Extension

    Write all currently modified game files to the extension folder. Existing files at the location written on a prior call will be cleared out. Content.xml will have dependencies added for files modified from existing extensions.
    
    * skip_content
      - Bool, if True then the content.xml file will not be written.
      - Defaults to False.
        


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
 * 0.10.1
   - Added workaround for a bug in x4 catalogs that sometimes use an incorrect empty file hash; also added an optional setting to allow hash mismatches to support otherwise problematic catalogs.
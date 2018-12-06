X4 Customizer 0.9
-----------------

Note: work in progress.

This tool will read in source files from X4, modify on them based on user selected transforms, and write the results back to the game directory. Transforms will often perform complex or repetitive tasks succinctly, avoiding the need for hand editing of source files. Many transforms will also do analysis of game files, to intelligently select appropriate edits to perform.  Some transforms carry out binary code edits, allowing for options not found elsewhere.

Source files will generally support any prior modding. Most transforms support input arguments to set parameters and adjust behavior, according to user preferences. Most transforms will work on an existing save.

This tool is written in Python, and tested on version 3.7.

Usage for Releases:

 * "Launch_X4_Customizer.bat [path to user_transform_module.py]"
   - Call from the command line for full options, or run directly for default options.
   - Runs the customizer, using the provided python user_transform_module which will specify the path to the X4 directory and the transforms to be run.
   - By default, attempts to run User_Transforms.py in the input_scripts folder.
   - Call with '-h' to see any additional arguments.
 * "Clean_X4_Customizer.bat [path to user_transform_module.py]"
   - Similar to Launch_X4_Customizer, except appends the "-clean" flag, which will undo any transforms from a prior run.

Usage for the Python source code:

 * "X4_Customizer\Main.py [path to user_transform_module.py]"
   - This is the primary entry function for the python source code.
   - Does not fill in a default transform file unless the -default_script option is used.
   - Supports general python imports in the user_transform_module.
   - If the scipy package is available, this supports smoother curve fits for some transforms, which were omitted from the Release due to file size.
 * "X4_Customizer\Make_Documentation.py"
   - Generates updated documentation for this project, as markdown formatted files README.md and Documentation.md.
 * "X4_Customizer\Make_Executable.py"
   - Generates a standalone executable and support files, placed in the bin folder. Requires the PyInstaller package be available. The executable will be created for the system it was generated on.
 * "X4_Customizer\Make_Patches.py"
   - Generates patch files for this project from some select modified game scripts. Requires the modified scripts be present in the patches folder; these scripts are not included in the repository.
 * "X4_Customizer\Make_Release.py"
   - Generates a zip file with all necessary binaries and source files for general release.

Setup and behavior:

  * Source files will be read from the X4 cat/dat files automatically, with mods applied according to those selected in the user's content.xml and possibly any loose files under the X4 directory.

  * The user controls the customizer using a command script which will set the path to the X4 installation to customize (using the Set_Path function), and will call the desired transforms with any necessary parameters. This script is written using Python code, which will be executed by the customizer.
  
  * The key command script sections are:
    - "from X4_Customizer import *" to make all transform functions available.
    - Call Set_Path to specify the X4 directory, along with some other path options. See documentation for parameters.
    - Call a series of transform functions, as desired.
  
  * The quickest way to set up the command script is to copy and edit the "input_scripts/User_Transforms_template.py" file, renaming it to "User_Transforms.py" for recognition by Launch_X4_Customizer.bat. Included in the repository is Authors_Transforms, the author's personal set of transforms, which can be checked for futher examples.

  * Transformed output files will be generated to a new extension folder, as loose files or packged in a cat/dat pair.

***

Example input file:

    '''
    Example for using the Customizer, setting a path to
    the X4 directory and running some simple transforms.
    '''
    
    # Import all transform functions.
    from X4_Customizer import *
    
    Set_Path(
        # Set the path to the X4 installation folder.
        path_to_x4_folder = r'C:\Steam\SteamApps\common\X4 Foundations',
    )
    
    # Reduce mass traffic and increase military jobs.
    Adjust_Job_Count(
        ('id','masstraffic', 0.5),
        ('tag','military', 2)
        )

***

Setup methods:

  * Set_Path

       Sets the paths to be used for file loading and writing.
   
       * path_to_x4_folder
         - Path to the X4 base folder, where the executable is located.
       * path_to_output_folder
         - Optional, path to a folder to place output files in.
         - Defaults to match path_to_x4_folder, so that outputs are directly readable by the game.
       * path_to_source_folder
         - Optional, alternate folder which contains source files to be modified.
         - Maybe be given as a relative path to the "addon" directory, or as an absolute path.
         - Files located here should have the same directory structure as standard games files, eg. 'source_folder/types/Jobs.txt'.
       * summary_file
         - Name for where a summary file will be written, with any transform results, relative to the output folder.
         - Defaults to 'summary.txt'.
       * log_file
         - Name for where a json log file will be written, including a summary of files written.
         - This is also the file which will be read for any log from a prior run.
         - Defaults to 'log.json'.
       


***

Job Transforms:

 * Adjust_Job_Count

      Adjusts job ship counts using a multiplier, affecting all quota fields. Caller provided matching rules determine which jobs get adjusted. Resulting non-integer job counts are rounded, with a minimum of 1 unless the multiplier or original count were 0.
  
      * job_factors:
        - Tuples holding the matching rules and job count  multipliers, (match_key, match_value, multiplier).
        - The match_key is one of a select few fields from the job nodes, against which the match_value will be compared.
        - Multiplier is an int or float, how much to adjust the job count by.
        - If a job matches multiple entries, the first match is used.
        - Supported keys:
          - 'faction': The name of the category/faction.
          - 'tag'    : A possible value in the category/tags list.
          - 'id'     : Name of the job entry, partial matches supported.
          - '*'      : Wildcard, always matches, takes no match_value.
          - 'masstraffic' : Mass traffic ship, takes no match_value.
  
      Example: Adjust_Job_Count( ('id','masstraffic', 0.5), ('tag','military', 2), ('tag','miner', 1.5), ('faction','argon', 1.2), ('*', 1.1) )
      


***

Change Log:
 * 0.9
   - Initial version, after a long evening of adapting X3_Customizer for X4.
   - Added first transform, Adjust_Job_Count.
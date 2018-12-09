'''
X4 Customizer
-----------------

Current status: functional, most features in place, but still in beta testing.

This tool will programatically apply a variety of user selected transforms
to X4 game files, optionally pre-modded. Features include:

 * Integrated catalog read/write support.
 * Basic XML diff patch support.
 * Automatic detection and loading of enabled extensions.
 * Framework for developing modular, customizable transforms of
   varying complexity.
 * Transforms can dynamically read and alter game files, instead of being
   limited to static changes like standard extensions.
 * Transforms operate on a user's unique mixture of mods, and can
   easily be rerun after game patches or mod updates.
 * Changes are written to a new or specified extension.

This tool is available as platform portable Python source code (tested on
3.7 with the lxml package) or as a compiled executable for 64-bit Windows.

The control script:

  * This tool works by executing a user supplied python script specifying any
    system paths, settings, and desired transforms to run.

  * The key control script sections are:
    - "from X4_Customizer import *" to make all transform functions available.
    - Call Settings() to change paths and set non-default options.
    - Call a series of transforms.
    
  * The quickest way to set up the control script is to copy and edit
    the "input_scripts/User_Transforms_template.py" file, renaming
    it to "User_Transforms.py" for recognition by Launch_X4_Customizer.bat.

Usage for compiled releases:

  * "Launch_X4_Customizer.bat <optional path to control script>"
    - Call from the command line for full options (-h for help), or run
      directly to execute the default script at
      "input_scripts/User_Transforms.py".
  * "Clean_X4_Customizer.bat <optional path to control script>"
    - Removes files generated in a prior run of the given or default3
      control script.

Usage for Python source code:

  * "python X4_Customizer\Main.py <optional path to control script>"
    - This is the primary entry function for the python source code.
    - Add the "-default_script" option to behave like the bat launcher.
    - Control scripts may freely use any python packages, instead of being
      limited to those included with the release.
  * "python X4_Customizer\Make_Documentation.py"
    - Generates updated documentation for this project, as markdown
      formatted files README.md and Documentation.md.
  * "python X4_Customizer\Make_Executable.py"
    - Generates a standalone executable and support files, placed
      in the bin folder. Requires the PyInstaller package be available.
      The executable will be created for the system it was generated on.
  * "python X4_Customizer\Make_Release.py"
    - Generates a zip file with all necessary binaries, source files,
      and example scripts for general release.


'''
# Note: the above comment gets printed to the markdown file, so avoid
#  having a 4-space indent because text will get code blocked.
# -Need to also avoid this 4-space group across newlines, annoyingly.
# -Spaces in text being put into a list seems okay.
# -In general, check changes in markdown (can use Visual Studio plugin)
#  to verify they look okay.

# Note:
# For convenient user use, this will import the transforms and some
#  select items flatly.
# For general good form, this will also import subpackages and top
#  level modules
# The Main and various Make_* modules will be left off; those are
#  desired to be called directly from a command line.

# Subpackages/modules.
from . import Common
from . import Transforms
from . import File_Manager
from . import Change_Log

# Convenience items for input scripts to import.
from .Transforms import *
#from .Common.Settings import Set_Path
from .Common.Settings import Settings
from .File_Manager import Load_File


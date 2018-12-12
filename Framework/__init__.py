'''
X4 Customizer
-----------------

Current status: functional, framework being refined.

This tool offers a framework for modding the X4 and extension game files
programatically, guided by user selected plugins (analyses, transforms,
utilities). Features include:

  * Integrated catalog read/write support.
  * XML diff patch read/write support.
  * Automatic detection and loading of enabled extensions.
  * Three layer design: framework, plugins, and control script.
  * Framework handles the file system, plugin management, etc.
  * Plugins include analysis, transforms, and utilities.
  * Plugins operate on a user's unique mixture of mods, and can
    easily be rerun after game patches or mod updates.
  * Transforms can dynamically read and alter game files, instead of being
    limited to static changes like standard extensions.
  * Transforms are parameterized, to adjust their behavior.
  * Analyses can generate customized documentation.
  * Transformed files are written to a new or specified X4 extension.

This tool is available as platform portable Python source code (tested on
3.7 with the lxml package) or as a compiled executable for 64-bit Windows.

The control script:

  * This tool works by executing a user supplied python script specifying any
    system paths, settings, and desired plugins to run.

  * The key control script sections are:
    - "from Plugins import *" to make all major functions available.
    - Call Settings() to change paths and set non-default options.
    - Call a series of plugins with desired input parameters.
    - Call to Write_Extension() to write any modified files
      if transforms were used.
    
  * The quickest way to set up the control script is to copy and edit
    the "Scripts/User_Transforms_template.py" file, renaming
    it to "User_Transforms.py" for recognition by Launch_X4_Customizer.bat.

Usage for compiled releases:

  * "Launch_X4_Customizer.bat <optional path to control script>"
    - Call from the command line for full options (-h for help), or run
      directly to execute the default script at
      "Scripts/User_Transforms.py".
  * "Clean_X4_Customizer.bat <optional path to control script>"
    - Removes files generated in a prior run of the given or default3
      control script.

Usage for Python source code:

  * "python Framework\Main.py <optional path to control script>"
    - This is the primary entry function for the python source code.
    - Add the "-default_script" option to behave like the bat launcher.
    - Control scripts may freely use any python packages, instead of being
      limited to those included with the release.
  * "python Framework\Make_Documentation.py"
    - Generates updated documentation for this project, as markdown
      formatted files README.md and Documentation.md.
  * "python Framework\Make_Executable.py"
    - Generates a standalone executable and support files, placed
      in the bin folder. Requires the PyInstaller package be available.
      The executable will be created for the system it was generated on.
  * "python Framework\Make_Release.py"
    - Generates a zip file with all necessary binaries, source files,
      and example scripts for general release.
'''
# TODO: maybe add in examples of usage (perhaps tagged to put them
#  in the full documenation and not the readme).

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


# Convenience items for input scripts to import.

#from .Common.Settings import Set_Path
from . import Common
from .Common import Change_Log
from .Common import Settings
from .Common import Analysis_Wrapper
from .Common import Transform_Wrapper
from .Common import Utility_Wrapper

from . import File_Manager
from .File_Manager import Load_File, File_System


def _Init():
    '''
    One-time setup, not to be part of * imports.
    '''
    # Set the import path so the Imports is findable.
    from pathlib import Path
    import sys
    parent_dir = str(Path(__file__).resolve().parent.parent)
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
_Init()
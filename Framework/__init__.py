'''
X4 Customizer
-----------------

This tool offers a framework for modding the X4 and extension game files
programmatically, guided by user selected plugins (analyses, transforms,
utilities). Features include:

  * GUI to improve accessibility, designed using Qt.
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
  * Utilities offer extension error checking and cat pack/unpack support.

This tool is available as runnable Python source code (tested on 3.7 with the
lxml and PyQt5 packages) or as a compiled executable for 64-bit Windows.


Running the compiled release:

  * "Start_Gui.bat"
    - This starts up the Customizer GUI.
    - Equivelent to running "bin/X4_Customizer.exe"
  * "Run_Script.bat [script_name] [args]"
    - This runs a script directly without loading the GUI.
    - Call from the command line for full options (-h for help), or run
      directly to execute the default script at "Scripts/Default_Script.py".
    - Script name may be given without a .py extension, and without
      a path if it is in the Scripts folder.
  * "Clean_Script.bat [script_name] [args]"
    - Removes files generated in a prior run of the given or default
      control script.
  * "Check_Extensions.bat [args]"
    - Runs a command line script which will test extensions for errors,
      focusing on diff patching and dependency checks.
  * "Cat_Unpack.bat [args]"
    - Runs a command line script which unpacks catalog files.
  * "Cat_Pack.bat [args]"
    - Runs a command line script which packs catalog files.

Running the Python source code:

  * "python Framework\Main.py [script_name] [args]"
    - This is the primary entry function for the python source code,
      and equivalent to X4_Customizer.exe.
    - When no script is given, this launches the GUI.


GUI sections:

  * "Script" displays the current control script, alongside documentation
    on available plugins.  Drag plugins to the script window for a fast
    templated copy.  Scripts can be opened or saved, and default to
    the Scripts folder.  Syntax is highlighted as Python code.
    Press "Run Script" to run the current script; other tabs displaying
    game information will be updated automatically with the script changes.

  * "Config" allows customization of settings. These are saved to a
    json file in the main tool directory when the window closes.

  * The "Edit" menu opens up tabs with editable tables of game object
    information. Objects may be displayed individually or in a table.
    See further below for details. All edits made are saved in
    a json file in the main tool directory when a script is run
    or the window closes.

  * The "Utilities" menu currently has one option, the Virtual File
    System. This shows which game files the Customizer has loaded,
    patched from other extensions (blue), or modified itself (red).
    Right click a file for the option to view its contents.

  * The File Viewer tabs display individual file contents, in their
    pre-diff patch, post-diff patch, and post-customizer versions.
    Select two versions and press "Compare" to get a summary on
    lines changed. Press "Reload" to force the file to be reloaded
    from disk, including any diff patches; this may be used to 
    test customize diff patch files in another extension.

The control script:

  * This tool is primarily controlled by a user supplied python script which
    will specify the desired plugins to run. Generally this acts as a build
    script to create a custom extension.

  * The key control script sections are:
    - "from Plugins import *" to make all major functions available.
    - Optionally call Settings() to change paths and set non-default options;
      this can also be done through a setttings.json file or through the GUI.
    - Call a series of plugins with desired input parameters; see plugin
      documentation for available options.
    - Call Write_Extension() to write out any modified files, formatted
      as diff patches.
    
  * Scripts of varying complexity are available in the Scripts folder,
    and may act as examples.
    

GUI based object editing:

  * In addition to script selected transforms, game information can
    be directly edited for select objects on the appropriate edit tabs.
    Tabs include "weapons", "wares", and others as time goes on.

  * Press "Refresh" on the tab to load the game information.
  * The "vanilla" column shows the object field values for the base
    version of the game files loaded.
  * The "patched" column shows field values after other extensions
    have had their diff patches applied.
  * The "edited" column is where you may change values manually.
  * Running a script that includes the Apply_Live_Editor_Patches plugin
    will apply edits to the game files.
  * The "current" column will show the post-script field values,
    and mainly exists for verification of hand edits as well as
    other transform changes.


Writing custom edit code:

  * This framework may be used to write custom file editing routines.
  * The general steps are: use Load_File() to obtain the patched
    file contents, use Get_Root() to obtain the current file root xml
    (which includes any prior transform changes), make any custom edits
    with the help of the lxml package, and to put the changes back using
    Update_Root().
  * Existing plugins offer examples of this approach.
  * Edits made using the framework will automatically support
    diff patch generation.
  * Non-xml file support is more rudimentary, operating on file
    binary data pending further support for specific formats.
  * Routines may be written as plugin functions and put up for
    inclusion in later Customizer releases to share with other users.

'''
'''
todo:
- Support user files in the output extension.
  This needs a lot of thought into how to join files together, eg. user
  diffs need to be included with generated diffs, but this can get
  complicated if another extension run after the user diffs.
  Perhaps make a rule that such custom files cannot have external
  dependencies? Though that isn't preferably.
  Well, think about it.
- Fix bug: changing output extension requires gui restart to work.
- Fix xml formatting of quotation marks in attributes, which show
  up as &quot;
- Suppress some gui exceptions when paths are not set up correctly,
  tabs shouldn't try to update with bad Settings.
- Set the output extension to be included for general gui displays,
  and only disabled during a script run (along with its VFS reset).
  Would this be in parallel with the Settings option, or just
  reuse the Settings flag?
- Change tray icon to something more visible on black backgrounds.
- Save out versions of xml in vanilla/diff patched/edited state for
  external viewing (maybe export from the VFS).
- Dark theme, maybe https://stackoverflow.com/questions/15035767/is-the-qt-5-dark-fusion-theme-available-for-windows
  For cutstom colors, maybe do a custom light/dark flip operation,
  that takes the average rgb, and scales by (1 - avg/255).
- Set MD/AI script loading to not support patching/merging; apparently
  these just look for the first file found (or last subst).
- Button on edit tabs to export csv/html directly.
- When packing cats, add select top level files that are also present in
  the main game cats, so that unpack-repack of main files captures everything.
- When packing cats, support sig files (otherwise ignored by the source
  reader).
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

# For use by the doc generator.
description = __doc__

# Convenience items for input scripts to import.

#from .Common.Settings import Set_Path
from . import Common
from .Common import home_path
# Make some logs available.
from .Common import Change_Log, Plugin_Log, Print
from .Common import Get_Version
from .Common import Settings
from .Common import Analysis_Wrapper
from .Common import Transform_Wrapper
from .Common import Utility_Wrapper
from .Common import XML_Misc
# Allow convenient catching of all special exception types.
from .Common.Exceptions import *

from . import File_Manager
from .File_Manager import *

from . import Live_Editor_Components
from .Live_Editor_Components import Live_Editor

# The Gui wants a few more imports to work when compiled.
from . import Main
from . import Make_Documentation

def _Init():
    '''
    One-time setup, not to be part of * imports.
    '''
    import sys
    # Set the home_path to be a search path for other packages.
    if str(home_path) not in sys.path:
        sys.path.append(str(home_path))
_Init()
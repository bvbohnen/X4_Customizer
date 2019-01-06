'''
Change Log:
 * 0.9
   - Initial version, quick adaption of X3_Customizer for X4.
   - Added first transform, Adjust_Job_Count.
 * 0.9.1
   - Major framework development.
   - Settings overhauled for X4.
   - Source_Reader overhauled, now finds and pulls from extensions.
   - Xml diff patch support added for common operations, merging extensions
     and base files prior to transforms. Pending further debug.
 * 0.9.2
   - Fix for when the user content.xml isn't present.
 * 0.9.3
   - Major development of diff patch generation, now using close to
     minimal patch size instead of full tree replacement, plus
     related debug of the patch application code.
   - Framework largely feature complete, except for further debug.
 * 0.9.4
   - Applied various polish: documentation touchup, gathered misc
     file_manager functions into a class, etc.
   - Added dependency nodes to the output extension.
 * 0.10
   - Major reorganization, moving transforms into a separate Plugins
     package that holds runtime script imports.
   - Added utilities for simple cat operations.
   - Added Print_Weapon_Stats.
 * 0.10.1
   - Added workaround for a bug in x4 catalogs that sometimes use
     an incorrect empty file hash; also added an optional setting to
     allow hash mismatches to support otherwise problematic catalogs.
 * 0.10.2
   - Bug fix in cat unpacker.
 * 0.11
   - Added plugins Check_Extension, Check_All_Extensions.
   - Added passthrough argparse support, along with command line callable
     scripts for extension check and cat pack/unpack.
   - Swapped the default script from User_Transforms to Default_Script.
 * 0.11.1
   - Added support for case insensitive path matching, instead of
     requiring a match to the catalogs.
 * 1.0
   - Scattered framework refinements.
   - Added Adjust_Weapon_Damage.
   - Added Adjust_Weapon_Fire_Rate.
   - Added Adjust_Weapon_Range.
   - Added Adjust_Weapon_Shot_Speed.
   - Refined Print_Weapon_Stats further.
   - Refined matching rule format for Adjust_Job_Count.
 * 1.1
   - Worked around lxml performance issue with index based xpaths, to
     speed up diff patch verification.
   - Added Print_Ware_Stats.
   - Added Adjust_Ware_Prices.
   - Added Adjust_Ware_Price_Spread.
   - Added Adjust_Mission_Rewards.
 * 1.1.1
   - Bugfix for ambiguous xpaths that still require indexes, and cleaned
     up quotes to avoid nesting double quotes.
 * 1.2
   - Added the initial Gui, featuring: python syntax and plugin highlighter,
     documentation viewer, settings editor, script launcher, preliminary
     weapon info viewer; plus niceties like changing font, remembering
     layout, and processing on a background thread.
   - Some unfortunate file size bloat in the compiled version.
 * 1.3
   - Added the Live_Editor, an extension for supporting gui based hand
     editing of game files.
   - Gui refined further, and live editor support added.
   - Weapon tables updated for the live editor.
   - Swapped the release exe to run without a console, and fixed
     a bug when running from outside the main directory.
 * 1.3.1
   - Fix a couple small bugs that crept in.
 * 1.4
   - Added wares to the GUI live editor.
   - Support added in the GUI for changing a laser's bullet.
   - Used several tricks to accelerate wares.xml parsing (multithreading,
     xpath bypassing, etc.) to accelerate Print_Ware_Stats and GUI display.
   - Background work to reorganize gui code for easy tab expansion,
     and tab thread requests will now queue up for service.
   - Further development of the Live_Editor, supporting object tree
     views and dynamically updating inter-object references.
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
   - Added file viewing tabs to the gui, with xml syntax highlighting
     and diff comparison output.
 * 1.6.1
   - Bug fixes for hidden tabs and a threading conflicts.
 * 1.6.2
   - Added coloring to the VFS tree view.
   - Added more fields for missile editing.
   - Bug fix for tabs forgetting order between sessions.
   - Swapped around inter-tab signalling and added more threading safety.
 * 1.7
   - Added multi-object table views to the gui object editor tabs.
 * 1.7.1
   - Fixed an issue with lxml find/findall not properly handling xpaths
     using indexes after predicates.
'''
# Note: changes moved here for organization, and to make them easier to
# break out during documentation generation.

def Get_Version():
    '''
    Returns the highest version number in the change log,
    as a string, eg. '3.4.1'.
    '''
    # Traverse the docstring, looking for ' *' lines, and keep recording
    #  strings as they are seen.
    version = ''
    for line in __doc__.splitlines():
        if not line.startswith(' *'):
            continue
        version = line.split('*')[1].strip()
    return version

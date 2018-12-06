'''
Generate patch files from select modified game files.

Patches allow for distributing edits to some complex (generally compiled)
files in an easier manner, and without having to copy those
code files, plus potentially supporting applying multiple
patches to the same file.

TODO: add a transform file to rebuild the modified source scripts from
 patches, if needed, so that distributions can recreate those modded
 scripts in the patches folder for further editing and regeneration
 of new patches.

Note: currently only supports a single patch per file.
'''

import os
import sys
from pathlib import Path
import argparse

# To support packages cross-referencing each other, set up this
#  top level as a package, findable on the sys path.
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

import X4_Customizer
Make_Patch = X4_Customizer.File_Manager.File_Patcher.Make_Patch

def Make(*args):

    X4_Customizer.Set_Path(
        # This can point to any x3 installation which will have the
        #  unmodified base files to be patched.
        # Modified versions of these files should exist in patches.
        path_to_addon_folder = r'D:\Steam\SteamApps\common\x3 terran conflict\addon',
        source_folder = 'patch_source'
    )

    # Lay out the modified files here.
    # These should all be in the patches folder.
    # Verify the reverse direction patch application generates the
    # modified file properly.

    Make_Patch('scripts/!fight.war.protectsector.xml', verify = True)
    Make_Patch('scripts/plugin.com.agent.main.xml', verify = True)
    Make_Patch('scripts/!move.follow.template.xml', verify = True)
    Make_Patch('scripts/!plugin.acp.fight.attack.object.xml', verify = True)
    Make_Patch('scripts/!lib.fleet.shipsfortarget.xml', verify = True)

    # Note: these patches are on original xml files, not pck.
    # Also, they lack the sourcecodetext section and have line numbers,
    # so reformatting should help reduce patch size.
    Make_Patch('scripts/plugin.gz.CmpClean.crunch.xml', verify = True, reformat_xml = True)
    Make_Patch('scripts/plugin.gz.CmpClean.Main.xml', verify = True, reformat_xml = True)


    # Can leave the attack command mod as a standalone script, since it
    # is fairly simple.
    #Make_Patch('!ship.cmd.attack.std.xml', verify = True)
    

if __name__ == '__main__':
    # Feed all args except the first (which is the file name).
    Make(*sys.argv[1:])

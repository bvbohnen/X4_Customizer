'''
Creates a zip file with all necessary contents for a release.
Included should be documentation, binaries, and necessary game
files.
'''
import os
from pathlib import Path # TODO: switch over from os.
import sys
import zipfile
import argparse

import Make_Documentation
import Make_Executable
#import Make_Patches

parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))
import X4_Customizer

This_dir = os.path.join(os.path.dirname(__file__))
Top_dir = os.path.normpath(os.path.join(This_dir, '..'))

def Make(*args):    
    # Set up command line arguments.
    argparser = argparse.ArgumentParser(
        description='Prepare a release of this project, zipping the'
                    ' necessary files.',
        )
            
    argparser.add_argument(
        '-refresh', 
        action='store_true',
        help = 'Default refresh will apply -doc_refresh and -exe_refresh.')
    
    argparser.add_argument(
        '-doc_refresh', 
        action='store_true',
        help = 'Regenerates documentation files before release.')
    
    argparser.add_argument(
        '-exe_refresh', 
        action='store_true',
        help = 'Regenerates executable and support files before release.')
    
    #argparser.add_argument(
    #    '-patch_refresh', 
    #    action='store_true',
    #    help = 'Regenerates patch files before release. This should be'
    #           ' rarely needed.')
        
    # Run the parser on the input args.
    parsed_args = argparser.parse_args(args)


    # Update the documentation and binary and patches.
    if parsed_args.doc_refresh or parsed_args.refresh:
        print('Refreshing documentation.')
        Make_Documentation.Make()
    if parsed_args.exe_refresh or parsed_args.refresh:
        print('Refreshing executable.')
        Make_Executable.Make()
    #if parsed_args.patch_refresh:
    #    print('Refreshing patches.')
    #    Make_Patches.Make()

    # Get a list of all file paths to add to the release.
    # These will be absolute paths.
    file_paths = []

    # Check the top dir.
    for file_name in os.listdir(Top_dir):
        # Loop over extensions to include.
        # This will be somewhat blind for the moment.
        for extension in ['.md','.txt','.bat']:
            if file_name.endswith(extension):
                file_paths.append(os.path.join(Top_dir, file_name))

    # Grab everything in bin, game_files, and patches.
    # TODO: look into parsing the git index to know which files are
    #  part of the actual repository, and not leftover work files (like
    #  modified scripts).
    # For now, some hand selected filters will be used.
    for folder in ['bin', 'input_scripts']: #,'game_files','patches'
        for dir_path, _, file_names in os.walk(os.path.join(Top_dir, folder)):

            # Check each file name individually.
            for file_name in file_names:

                ## Skip patches that don't end in .patch.
                #if folder == 'patches' and not file_name.endswith('.patch'):
                #    continue
                #
                ## Skip game files that end in .bak, leftovers from
                ##  the script editor.
                #if folder == 'game_files' and file_name.endswith('.bak'):
                #    continue

                # Only include select input scripts.
                if folder == 'input_scripts':
                    if file_name not in ['User_Transforms_template',
                                         'Authors_Transforms']:
                        continue

                file_paths.append(os.path.join(folder, dir_path, file_name))
                
                
    # Create a new zip file.
    # Put this in the top level directory.
    zip_name = 'X4_Customizer_v{}.zip'.format(X4_Customizer.Change_Log.Get_Version())
    zip_path = os.path.normpath(os.path.join(This_dir, '..', zip_name))
    zip_file = zipfile.ZipFile(zip_path, 'w')

    # Add all files to the zip.
    for path in file_paths:
        zip_file.write(
            # Give a full path.
            path,
            # Give an alternate internal path and name.
            # This will be relative to the top dir.
            # Note: relpath seems to bugger up if the directories match,
            #  returning a blank instead of the file name.
            arcname = os.path.relpath(path, Top_dir)
            )

    # Close the zip; this needs to be explicit, according to the
    #  documenation.
    zip_file.close()

    print('Release written to {}'.format(zip_path))

if __name__ == '__main__':
    # Feed all args except the first (which is the file name).
    Make(*sys.argv[1:])

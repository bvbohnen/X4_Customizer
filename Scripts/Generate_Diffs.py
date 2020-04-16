'''
Script for directly diffing pairs of files.
'''

from pathlib import Path
import argparse, sys
from Plugins import Generate_Diffs
from Plugins import Settings
from Framework import Get_Version


# Set up command line arguments.
argparser = argparse.ArgumentParser(
    description = 'XML Diff Patch Generator, part of X4 Customizer v{}'.format(Get_Version()),
    epilog = 'Example: Generate_Diffs.bat original.xml custom.xml diff.xml',
    )


argparser.add_argument(
    'original',
    default = None,
    nargs = 1,
    help =  'Path to the original unmodified file.' )

argparser.add_argument(
    'modified',
    default = None,
    nargs = 1,
    help =  'Path to the modified file.' )

argparser.add_argument(
    'output',
    default = None,
    # Consume 0 or 1 argument.
    # This prevents an error message when an arg not given,
    # and the default is used instead.
    nargs = '?',
    help =  'Path for where to write the output diff file.'
            ' Defaults to modified file name with a .diff.xml extension.' )


args = argparser.parse_args(sys.argv[1:])

# Make the source a Path, and convert to absolute to fill in the parents.
args.original = (Path.cwd() / Path(args.original)).resolve()
args.modified = (Path.cwd() / Path(args.modified)).resolve()

# Fill in the default dest if needed, and convert to a Path.
if args.output == None:
    args.output = args.modified.parent / (args.modified.stem + '.diff.xml')
else:
    args.output = (Path.cwd() / Path(args.output)).resolve()
    
# TODO: maybe verify xml files were given.

# Reprint the args for clarity, in case a bad path was given, to make
# it more obvious.
print()
print('Original  : {}'.format(args.original))
print('Modified  : {}'.format(args.modified))
print('Output    : {}'.format(args.output))
print()

# Call the plugin.
Generate_Diffs(
    original_file_path = args.original,
    modified_file_path = args.modified,
    output_diff_path   = args.output,
    )


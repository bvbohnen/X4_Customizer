'''
Script for directly diffing pairs of files.
'''

from pathlib import Path
import argparse, sys
from Plugins import Generate_Diff, Generate_Diffs
from Plugins import Settings
from Framework import Get_Version

# To avoid errors that print to the Plugin_Log trying to then load Settings
# which may not be set (eg. where to write the plugin_log to), monkey
# patch the log to do a pass through.
from Framework import Plugin_Log
Plugin_Log.logging_function = lambda line: print(str(line))


# Set up command line arguments.
argparser = argparse.ArgumentParser(
    description = ('XML Diff Patch Generator, part of X4 Customizer v{}.'
                   ' Generates xml diff patch files by comparing an original'
                   ' to a modified full xml file. Works on a single pair of'
                   ' files, or on a pair of directories.'
                   ).format(Get_Version()),
    epilog = ('Example (files)  : Generate_Diffs.bat original.xml modded.xml diff.xml\n'
              'Example (folders): Generate_Diffs.bat originals modded diffs' ),
    )


argparser.add_argument(
    'base',
    help =  'Path to the original unmodified base file, or directory of files.' )

argparser.add_argument(
    'mod',
    help =  'Path to the modified file, or directory of files where all'
            ' have name matches in the -base directory.' )

argparser.add_argument(
    'out',
    help =  'Path name of the output diff file, or directory to write files.')

argparser.add_argument(
    '-s', '--skip-unchanged',
    action='store_true',
    help =  'Produce nothing for files are unchanged (removing any prior diff);'
            ' default is to create an empty diff file.' )

argparser.add_argument(
    '-v', '--verbose',
    action='store_true',
    help =  'Print extra messages on each diff file generation.' )

# TODO: pattern matching rules for the files to include or exclude.


args = argparser.parse_args(sys.argv[1:])

# Make the source a Path, and convert to absolute to fill in the parents.
base = (Path.cwd() / Path(args.base)).resolve()
mod  = (Path.cwd() / Path(args.mod)).resolve()
out  = (Path.cwd() / Path(args.out)).resolve()
    

# Reprint the args for clarity, in case a bad path was given, to make
# it more obvious.
print()
print('Base : {}'.format(base))
print('Mod  : {}'.format(mod))
print('Out  : {}'.format(out))
print()

# Determine if this is file or directory mode.
mode = 'file' if base.is_file() else 'dir'

if mode == 'file':

    # TODO: maybe verify xml files were given, though perhaps someone
    # might use this for other xml-style types (xsd, etc), so skip for now.

    # All args should be files.
    if not base.is_file() or not mod.is_file() or not out.is_file():
        print('Error: mixed files and directories.')
    else:                      
        # Create a single diff.
        Generate_Diff(
            original_file_path = base,
            modified_file_path = mod,
            output_file_path   = out,
            skip_unchanged     = args.skip_unchanged,
            verbose            = args.verbose,
            )

else:

    # All args should be dirs.
    if not base.is_dir() or not mod.is_dir() or not out.is_dir():
        print('Error: mixed files and directories.')
    else:                      
        # Hand off to the mult-diff generator, which will handle
        # globbing and such.
        Generate_Diffs(
            original_dir_path = base,
            modified_dir_path = mod,
            output_dir_path   = out,
            skip_unchanged     = args.skip_unchanged,
            verbose            = args.verbose,
            )
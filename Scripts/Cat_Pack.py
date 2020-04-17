'''
Script for packing loose files into a catalog file.
Supports argument parsing for direct calls from a bat file.
'''
from pathlib import Path
import argparse, sys
from Plugins import Cat_Pack
from Plugins import Settings
from Framework import Get_Version

# To avoid errors that print to the Plugin_Log trying to then load Settings
# which may not be set (eg. where to write the plugin_log to), monkey
# patch the log to do a pass through.
from Framework import Plugin_Log
Plugin_Log.logging_function = lambda line: print(str(line))

# Set up command line arguments.
argparser = argparse.ArgumentParser(
    description = 'X4 Catalog Packer, part of X4 Customizer v{}'.format(Get_Version()),
    epilog = 'Example: Cat_Pack.bat "C:\Steam\SteamApps\common\X4 Foundations\extensions\mymod" -include *.xml',
    )


argparser.add_argument(
    'source',
    default = '.',
    # Consume 0 or 1 argument.
    # This prevents an error message when an arg not given,
    # and the default is used instead.
    nargs = '?',
    help =  'Path to the folder holding files to pack.'
            ' Defaults to call location.'
            ' Only packs files in subfolders matching expected X4 names.'
            )

argparser.add_argument(
    'dest',
    default = None,
    # Consume 0 or 1 argument.
    # This prevents an error message when an arg not given,
    # and the default is used instead.
    nargs = '?',
    help =  'Path and name of the cat file to write.'
            ' Defaults to <source folder>/ext_01.cat')


argparser.add_argument(
    '-include',
    default = None,
    # Consume all following plain args.
    nargs = '*',
    help =  'Wildcard patterns for files to be included, space separated.'
            ' Default includes everything.')

argparser.add_argument(
    '-exclude',
    default = None,
    # Consume all following plain args.
    nargs = '*',
    help =  'Wildcard patterns for files to be excluded, space separated.')

args = argparser.parse_args(sys.argv[1:])


# Make the source a Path, and convert to absolute to fill in the parents.
args.source = Path(args.source).resolve()

# Fill in the default dest if needed, and convert to a Path.
if args.dest == None:
    args.dest = args.source / 'ext_01.cat'
else:
    args.dest = Path(args.dest).resolve()
    

# Reprint the args for clarity, in case a bad path was given, to make
# it more obvious.
print()
print('Source  : {}'.format(args.source))
print('Dest    : {}'.format(args.dest))
print('Include : {}'.format(args.include))
print('Exclude : {}'.format(args.exclude))
print()

    
# Call the packer.
Cat_Pack(
    source_dir_path = args.source,
    dest_cat_path   = args.dest,
    include_pattern = args.include,
    exclude_pattern = args.exclude,
    )

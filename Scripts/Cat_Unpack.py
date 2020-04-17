'''
Script for unpacking catalog files.
Supports argument parsing for direct calls from a bat file.
'''

from pathlib import Path
import argparse, sys
from Plugins import Cat_Unpack
from Plugins import Settings
from Framework import Get_Version

# To avoid errors that print to the Plugin_Log trying to then load Settings
# which may not be set (eg. where to write the plugin_log to), monkey
# patch the log to do a pass through.
from Framework import Plugin_Log
Plugin_Log.logging_function = lambda line: print(str(line))

# Set up command line arguments.
argparser = argparse.ArgumentParser(
    description = 'X4 Catalog Unpacker, part of X4 Customizer v{}'.format(Get_Version()),
    epilog = 'Example: Cat_Unpack.bat "C:\Steam\SteamApps\common\X4 Foundations" -include *.xml *.xsd',
    )


argparser.add_argument(
    'source',
    #default = r'C:\Steam\SteamApps\common\X4 Foundations',
    default = '.',
    # Consume 0 or 1 argument.
    # This prevents an error message when an arg not given,
    # and the default is used instead.
    nargs = '?',
    help =  'Path to a catalog file or folder.'
            ' Defaults to call location.'
            ' When a folder given, catalogs are read in X4 priority order'
            ' according to expected naming (eg. 01.cat, ext_01.cat, etc.).'
            )

argparser.add_argument(
    'dest',
    default = None,
    # Consume 0 or 1 argument.
    # This prevents an error message when an arg not given,
    # and the default is used instead.
    nargs = '?',
    help =  'Path to the folder where unpacked files will be written.'
            ' Defaults to <source folder>/extracted')


argparser.add_argument(
    '-include',
    # Common use will likely just want xml and a couple other file types;
    # make that the default, and require explicit * to get everything.
    default = ['*.xml','*.xsd','*.lua','*.html','*.css','*.js','*.xsl'],
    # Consume all following plain args.
    nargs = '*',
    help =  'Wildcard patterns for files to be included, space separated.'
            ' Defaults include "*.xml" and a few other human readable file types.'
            ' Use "*" to unpack everything.')

argparser.add_argument(
    '-exclude',
    default = None,
    # Consume all following plain args.
    nargs = '*',
    help =  'Wildcard patterns for files to be excluded, space separated.')

argparser.add_argument(
    '-allow_md5_errors',
    action='store_true',
    help  = 'Allows unpacking of files that fail an md5 hash check.'
            ' This may occur in badly formed catalog files.')

args = argparser.parse_args(sys.argv[1:])

# Make the source a Path, and convert to absolute to fill in the parents.
args.source = Path(args.source).resolve()

# Fill in the default dest if needed, and convert to a Path.
if args.dest == None:
    if args.source.is_dir():
        args.dest = args.source / 'extracted'
    else:
        args.dest = args.source.parent / 'extracted'
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

# Call the unpacker.
Cat_Unpack(
    source_cat_path  = args.source,
    dest_dir_path    = args.dest,
    include_pattern  = args.include,
    exclude_pattern  = args.exclude,
    allow_md5_errors = args.allow_md5_errors
    )

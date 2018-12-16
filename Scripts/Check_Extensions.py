'''
Check extensions for errors.
Supports argument parsing for direct calls from a bat file.
'''
import argparse, sys
from Plugins import Check_Extension, Check_All_Extensions
from Plugins import Settings
from Framework import Get_Version, File_System


# Set up command line arguments.
argparser = argparse.ArgumentParser(
    description = 'X4 Extension Checker, part of X4 Customizer v{}'.format(Get_Version()),
    epilog = 'Example: Check_Extensions.bat mymod -x4 "C:\Steam\SteamApps\common\X4 Foundations"',
    )


argparser.add_argument(
    'extensions',
    default = None,
    nargs = '*',
    help =  'Optional names of an extensions to check, space separated.'
            ' If none given, all enabled extensions are checked.'
            )

argparser.add_argument(
    '-x4',
    default = None,
    metavar = 'Path',
    nargs = 1,
    help =  'Path to the X4 installation folder.'
            ' If not given, uses the default in Settings.')

argparser.add_argument(
    '-user',
    default = None,
    metavar = 'Path',
    nargs = 1,
    help =  'Path to the user x4 documents folder.'
            ' If not given, uses the default in Settings.')

args = argparser.parse_args(sys.argv[1:])


# Copy over a couple paths to Settings; let it deal with validation
# and defaults.
if args.x4 != None:
    Settings.path_to_x4_folder = args.x4
if args.user != None:
    Settings.path_to_user_folder = args.user


# If no extension names given, grab all of them.
if not args.extensions:
    args.extensions = File_System.Get_Extension_Names()

passed = []
failed = []
for extension in args.extensions:
    if Check_Extension(extension):
        passed.append(extension)
    else:
        failed.append(extension)

# Print out a nice summary.
summary = []
for result, ext_list in [
        ('Passed', passed),
        ('Failed', failed)
        ]:
    print()
    print(result + ':')
    for ext_name in ext_list:
        print('  ' + ext_name)
    if not ext_list:
        print('  None')
        
    # Add a little bit for a final line.
    summary.append('{} {}'.format(len(ext_list), result))
        
print()
print('Overall: ' + ', '.join(summary))


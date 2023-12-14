'''
Check extensions for errors.
Supports argument parsing for direct calls from a bat file.

Note: not for running from the GUI.
'''
import argparse, sys
from Plugins import Check_Extension, Check_All_Extensions
from Plugins import Settings
from Framework import Get_Version, File_System, Print

def Run():
    
    # Test if the gui window is open; error message if so.
    from Plugins.GUI import Main_Window
    if Main_Window.qt_application != None:
        Print('Error: Check_Extensions standalone script is only supported by'
              ' command line calls, not from the GUI.')
        return

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

    argparser.add_argument(
        '-more_orders',
        action = 'store_true',
        help =  'Performs additional loading order tests, loading extensions'
                ' at the earliest or latest opportunity; otherwise only'
                ' alphabetical ordering by folder name is used.'
                )

    args = argparser.parse_args(sys.argv[1:])

    # Copy over a couple paths to Settings; let it deal with validation
    # and defaults.
    if args.x4 != None:
        Settings.path_to_x4_folder = args.x4
    if args.user != None:
        Settings.path_to_user_folder = args.user

    # Include the current output extension in the check.
    Settings.ignore_output_extension = False
    
    # If no extension names given, grab all of them.
    # This will also initialize the file system.
    if not args.extensions:
        args.extensions = File_System.Get_Extension_Names()
    
    passed = []
    failed = []
    for extension in args.extensions:
        if Check_Extension(extension, check_other_orderings = args.more_orders):
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

Run()

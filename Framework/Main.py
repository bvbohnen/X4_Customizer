'''
Main function for the X4_Customizer.
'''
import os
import sys
from pathlib import Path
import argparse
import traceback

# Special code needs to be run for multiprocessing to
# work in the compiled version on windows.
from multiprocessing import Process, freeze_support

# To support packages cross-referencing each other, set up this
# top level as a package, findable on the sys path.
# TODO: this is a little redundant with Home_Path, but it is unclear
# on how to import home_path before this is done, so just repeat
# the effort for now.
if getattr(sys, 'frozen', False):
    home_path = Path(sys._MEIPASS).parent
else:
    home_path = Path(__file__).resolve().parents[1]
if str(home_path) not in sys.path:
    sys.path.append(str(home_path))

# To support easy control script naming, add the Scripts folder to
# the search path, but put it at the end (to reduce interference
# if the user wants to import from their call location).
scripts_dir = home_path / 'Scripts'
if str(scripts_dir) not in sys.path:
    sys.path.append(str(scripts_dir))

import Framework
import Plugins
from Framework import Print


def Run(*args):
    '''
    Run the customizer.
    This expect a single argument: the name of the .py file to load
    which specifies file paths and the transforms to run. Some other
    command line args supported.  Excess args will be placed in
    sys.args for called script to argparse if desired.
    '''    
    # Rename the settings for convenience.
    Settings = Framework.Settings
    
    # Set up command line arguments.
    argparser = argparse.ArgumentParser(
        description='Main function for running X4 Customizer version {}.'.format(
            Framework.Change_Log.Get_Version()
            ),
        # Special setting to add default values to help messages.
        # -Removed; doesn't work on positional args.
        #formatter_class = argparse.ArgumentDefault_ScriptsHelpFormatter,

        # To better support nested scripts doing their own argparsing,
        #  prevent abbreviation support at this level.
        allow_abbrev = False,
        )

    # Set this to default to None, which will be caught manually.
    argparser.add_argument(
        'control_script',
        # Consume 0 or 1 argument.
        # This prevents an error message when an arg not given,
        # and the default is used instead.
        nargs = '?',
        help =  'Python control script which will run directly instead of'
                ' launching the gui; path may be given relative to the'
                ' Scripts folder; .py extension is optional; '
               )
    
    # Flag to clean out old files.
    argparser.add_argument(
        '-clean', 
        action='store_true',
        help = 'Cleans out any files created on the prior run,'
               ' and reverts any file renamings back to their original names.'
               ' Files in the user source folder will be moved to the game'
               ' folders without modifications.'
               ' Still requires a user_transform file which specifies'
               ' the necessary paths, but transforms will not be run.')
    
    argparser.add_argument(
        '-dev', 
        action='store_true',
        help =  'Enables developer mode, which makes some changes to'
                ' exception handling.')
    
    argparser.add_argument(
        '-quiet', 
        action='store_true',
        help =  'Hides some status messages.')
    
    argparser.add_argument(
        '-test', 
        action='store_true',
        help =  'Performs a test run of the transforms, behaving like'
                ' a normal run but not writing out modified files.')
    
    argparser.add_argument(
        '-argpass', 
        action='store_true',
        help =  'Indicates the control script has its own arg parsing;'
                ' extra args and "-h" are passed through sys.argv.')
    
    argparser.add_argument(
        '-nogui', 
        action='store_true',
        help =  'Suppresses the gui from launching; a default script'
                ' will attempt to run if no script was given.')
    
    # Capture leftover args.
    # Note: when tested, this appears to be buggy, and was grabbing
    # "-dev" even though that has no ambiguity; parse_known_args
    # works better.
    #argparser.add_argument('args', nargs=argparse.REMAINDER)
    
    # Parsing behavior will change depending on if args are being
    # passed downward.
    if not '-argpass' in args:
        # Do a normal arg parsing.
        args = argparser.parse_args(args)

    else:
        # Pick out the -h flag, so help can be printed in the
        # control script instead of here. Also catch --help.
        pass_help_arg = None
        for help_str in ['-h','--help']:
            if help_str in args:
                pass_help_arg = help_str
                # Need to swap from tuple to list to remove an item.
                args = list(args)
                args.remove(help_str)

        # Do a partial parsing.
        args, remainder = argparser.parse_known_args(args)

        # Put the remainder in sys.argv so called scripts can use it;
        # these should go after the first argv (always the called script name,
        # eg. Main.py).
        sys.argv = [sys.argv[0]] + remainder
        # Add back in the -h flag.
        if pass_help_arg:
            sys.argv.append(pass_help_arg)


    # Check for a gui launch.
    # This has been changed to act as the default when no script is given.
    if not args.nogui and not args.control_script:
        # In this case, the gui takes over and no script is expected.
        # TODO: maybe pass an input script path to the gui, but it
        # isn't important.
        Plugins.GUI.Start_GUI()
        # Return when the gui closes.
        return

    # Set the input script to default if one wasn't given.
    if not args.control_script:
        args.control_script = 'Default_Script'
    # Convenience flag for when the default script is in use.
    using_default_script = args.control_script == 'Default_Script'

    # Convert the script to a Path, for convenience.
    args.control_script = Path(args.control_script)
    
    # Add the .py extension if needed.
    if args.control_script.suffix != '.py':
        args.control_script = args.control_script.with_suffix('.py')

    # If the given script isn't found, try finding it in the scripts folder
    # or its subdirectories.
    # Only support this switch for relative paths.
    if not args.control_script.exists() and not args.control_script.is_absolute():
        # Recursive search for a matching script name.
        for path in scripts_dir.glob(f'**/{args.control_script.name}'):
            # Use the first one found.
            args.control_script = path
            break
        #alt_path = scripts_dir / args.control_script
        #if alt_path.exists():
        #    args.control_script = alt_path


    # Handle if the script isn't found.
    if not args.control_script.exists():
        # If the default script is in use, Main may have been called with
        # no args, which case print the argparse help.
        if using_default_script:
            argparser.print_help()

        # Follow up with an error on the control script name.
        Print('Error: {} not found.'.format(args.control_script))

        # Print some extra help text if the user tried to run the default
        #  script from the bat file.
        if using_default_script:
            # Avoid word wrap in the middle of a word by using an explicit
            #  newline.
            Print('For new users, please open Scripts/'
                  'Default_Script_template.py\n'
                  'for first time setup instructions.')
        return


    # Add the script location to the search path, so it can include
    # other scripts at that location.
    # This will often just by the Scripts folder, which is already in
    # the sys.path, but for cases when it is not, put this path
    # early in the search order.
    # TODO: remove this path when done, for use in gui when it might
    # switch between multiple scripts.
    control_script_dir = args.control_script.parent
    if str(control_script_dir) not in sys.path:
        sys.path.insert(0, str(control_script_dir))
    
        
    # Handle other args.
    if args.quiet:
        Settings.verbose = False

    if args.clean:
        Print('Enabling cleanup mode; plugins will be skipped.')
        Settings.skip_all_plugins = True

    if args.dev:
        Print('Enabling developer mode.')
        Settings.developer = True

    if args.test:
        Print('Performing test run.')
        # This uses the disable_cleanup flag.
        Settings.disable_cleanup_and_writeback = True
                

    Print('Calling {}'.format(args.control_script))
    try:
        # Attempt to load/run the module.
        # TODO: some way to detect if this is not a valid script, other
        # than whatever possible error occurring, eg. if the user tried
        # to run one of the plugin files.

        import importlib        
        module = importlib.machinery.SourceFileLoader(
            # Provide the name sys will use for this module.
            # Use the basename to get rid of any path, and prefix
            #  to ensure the name is unique (don't want to collide
            #  with other loaded modules).
            'control_script_' + args.control_script.name.replace(' ','_'),
            # Just grab the name; it should be found on included paths.
            str(args.control_script)
            ).load_module()
        
        #Print('Run complete')
        
        # Since a plugin normally handles file cleanup and writeback,
        #  cleanup needs to be done manually here when needed.
        if args.clean:
            Framework.File_System.Cleanup()

    except Exception as ex:
        # Make a nice message, to prevent a full stack trace being
        #  dropped on the user.
        Print('Exception of type "{}" encountered.\n'.format(
            type(ex).__name__))
        ex_text = str(ex)
        if ex_text:
            Print(ex_text)

        # Close the plugin log safely (in case of raising another
        #  exception).
        Framework.Common.Logs.Plugin_Log.Close()

        # In dev mode, print the exception traceback.
        if Settings.developer:
            Print(traceback.format_exc())
            # Raise it again, just in case vs can helpfully break
            # at the problem point. (This won't help with the gui up.)
            raise ex
        #else:
        #    Print('Enable developer mode for exception stack trace.')
        
    return

if __name__ == '__main__':
    # assert False
    # Multiprocessing requires these functions be run right after entry.
    # Note: this breaks the normal VS debugging, so only do it when frozen.
    if getattr(sys, 'frozen', False):
        freeze_support()
        Process(target = Run, args = sys.argv[1:]).start()
    else:
        Run(*sys.argv[1:])
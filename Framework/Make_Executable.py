'''
Use PyInstaller to bundle the python code into a standalone executable.

While it is unclear on how to use PyInstaller directly as a python
package, a specifications file can be generated here, and pyinstaller
called as a subprocess to run the compilation, and then the
expected output folders checked for files and manipulated as needed.

Note:
Pyinstaller has two main modes for generated code:

1)  Multiple files in a single folder, with dlls, python bytecode, etc.
    broken out, and the exe acting as a booststrap.
    This creates an ugly folder with a bunch of files lumped in
    with the exe.

2)  Single exe which contains the above files in a packed form, and
    unpacks them to a temp directory when executed, then acting similar
    to (1).
    This is stated as being slower to start, and not cleaning up after
    itself if the program terminates early, which could be bad since
    this customizer is expected to crash when users provide unsupported
    arguments and such (plus it has its own potential bugs to worry
    about).


Option (1) should be a lot safer, and its ugliness has a couple possible
workarounds:

1)  Create a shortcut in a higher level folder which links to the exe,
    so the user can just use the shortcut.
    This is going to be windows-specific, but most or all expected
    users are likely on windows, so this should be okay.
    In testing, this seems to have problems with handling command
    line args properly.

2)  Put misc files into a subfolder, and add that subfolder to the
    system search path using a runtime hook, essentially python code
    that runs at startup before other modules are loaded.
    See https://stackoverflow.com/questions/19579979/pyinstaller-changing-dll-and-pyd-output-location
    for an example.
    In practice, any subfolder seems to work without needing the hook,
    though a couple files still need to be kept with the exe to
    the basic bootstrapping. Update: a newer pyinstaller verions no
    longer detects dlls in the subfolder.

3)  Make a bat file to launch the app, which can more easily pass
    command line args.


Note on multiple exes:
    Pyinstaller can either make the exe for console or window mode.
    This tool has console style support (run a script), and gui support.

    If compiled in console mode, the gui will be launched with an
    idling console window in the background catching random prints
    and exceptions.

    If compiled in windowed mode, the command line will still work
    except that it doesn't catch any prints or exception messages.

    A possible workaround is suggested here:
    https://stackoverflow.com/questions/38981547/making-a-pyinstaller-exe-do-both-command-line-and-windowed

    Basically, compile in window mode, then for the command line
    launch with the "|more" suffix to cause the console to capture
    printouts.
    Update: cannot capture responses in |more without console=True,
    but that causes the console to appear behind the gui...
    so this might be a dead end.


    Overall decision: just compile two versions, one windowed and one not.


Note: pyinstaller had trouble finding pyqt5 source files ("plugins"),
but this was solved with a pip update.
'''

import argparse
import sys
import os
import shutil
from pathlib import Path # TODO: complete switchover to pathlib.

# Conditional import of pyinstaller, checking if it is available.
try:
    import PyInstaller
except ImportError:
    print('PyInstaller not found; customizer->executable generation disabled')
    PyInstaller = None

import subprocess

This_dir = Path(__file__).parent

def Clear_Dir(dir_path):
    '''
    Clears contents of the given directory.
    '''
    # Note: rmtree is pretty flaky, so put it in a loop to keep
    # trying the removal.
    if os.path.exists(dir_path):
        for _ in range(10):
            try:
                shutil.rmtree(dir_path)
            except Exception:
                continue
            break
    return


def Make(*args):

    # Scrap the first arg if it is a .py file; this is mostly because
    #  visual studio is set to insert it for normal customizer
    #  calls, and it is bothersome to remove that when testing
    #  this script.
    try:
        if args[0].endswith('.py'):
            args = args[1:]
    except Exception:
        pass
    
    # Set up command line arguments.
    argparser = argparse.ArgumentParser(
        description='Generate an executable from the X4 Customizer source'
                    ' python code, using pyinstaller.',
        )
    
    #-Removed; single file support is maybe a bad idea, as noted
    # in comments above.
    #argparser.add_argument(
    #    '-single_file', 
    #    action='store_true',
    #    help = 'Tells pyinstaller to create a single exe file, instead'
    #           ' of bundling multiple files in a folder.')
        
    argparser.add_argument(
        '-preclean', 
        action='store_true',
        help = 'Force pyinstaller to do a fresh compile, ignoring any'
               ' work from a prior build.')
    
    argparser.add_argument(
        '-postclean', 
        action='store_true',
        help = 'Delete the pyinstaller work folder when done, though this'
               ' will slow down rebuilds.')
    
    argparser.add_argument(
        '-bats_only', 
        action='store_true',
        help = 'Only update the .bat files, otherwise skipping the compile.')

    #argparser.add_argument(
    #    '-o', '-O', 
    #    action='store_true',
    #    help = 'Compile with basic python optimization, removing assertions'
    #           ' and perhaps some debug checks.')
    
    #argparser.add_argument(
    #    '-window', 
    #    action='store_true',
    #    help = 'Compiles for windowed output instead of console output.')
    
    # -Removed, keep docstrings.
    #argparser.add_argument(
    #    '-oo', '-OO', 
    #    action='store_true',
    #    help = 'Compile with more python optimization, similar to -O'
    #           ' but also trimming docstrings to reduce code size.')
    
    # Run the parser on the input args.
    # Split off the remainder, mostly to make it easy to run this
    # in VS when its default args are still set for Main.
    parsed_args, remainder = argparser.parse_known_args(args)

    # Check for pyinstaller.
    if PyInstaller is None:
        raise RuntimeError(f'PyInstaller not found')

    # Set the output folder names.
    # Note: changing the pyinstaller build and dist folder names is
    #  possible, but not through the spec file (at least not easily),
    #  so do it through the command line call.
    build_folder = (This_dir / '..' / 'pyinstaller_build_files').resolve()

    # Pick the final location to place the exe and support files.
    # This should have the same relative path to reach any common
    #  files in the source and patches folders, which can be
    #  moved up under the main level (so the x4_customizer exe
    #  can be down one folder, and the python down another folder).
    dist_folder = (This_dir / '..' / 'bin').resolve()
        
    # Note: it would be nice to put the spec file in a subfolder, but
    #  pyinstaller messes up (seems to change its directory to wherever
    #  the spec file is) and can't find the source python, so the spec
    #  file needs to be kept in the main dir and cleaned up at the end.
    spec_file_path = This_dir / 'X4_Customizer.spec'
    # Hook file probably works like the spec file.
    hook_file_path = This_dir / 'pyinstaller_x4c_hook.py'

    # Change the working directory to here.
    # May not be necessary, but pyinstaller not tested for running
    #  from other directories, and this just makes things easier
    #  in general.
    original_cwd = os.getcwd()
    os.chdir(This_dir)
    
    # Set two program names, based on mode.
    program_name_gui     = 'X4_Customizer'
    program_name_console = 'X4_Customizer_console'

    # Delete the existing dist directory; pyinstaller has trouble with
    #  this for some reason (maybe using os.remove, which also seemed
    #  to have the same permission error pyinstaller gets).
    if not parsed_args.bats_only and dist_folder.exists():
        Clear_Dir(dist_folder)


    # To be able to support direct command line calls (with responses)
    #  as well as gui launching, the only workable solution appears
    #  to be to compile twice.
    # Warning: gui version puts another copy of Qt an extra folder deeper,
    #  so aim to have the console version not include qt. This will also
    #  duplicate lxml (which is also packed into its own folder). Deal with
    #  that after compilation.
    for mode in ['console','gui']:
        # Skip when only making bat files.
        if parsed_args.bats_only:
            continue
    
        # Set unique names based on mode.
        if mode == 'console':
            program_name = program_name_console
        else:
            program_name = program_name_gui
            
    
        # Generate lines for a hook file.
        # With the packaging of X4_Customizer, this doesn't appears to
        #  be needed anymore.
        # TODO: maybe remove entirely.
        # TODO: maybe set a gui/console mode here, eg. so that the
        # console version of the compile will not launch a gui
        # by default without args.
        hook_lines = []

        # Prepare the specification file expected by pyinstaller.
        spec_lines = []

        # Note: most places where paths may be used should be set as
        #  raw strings, so the os.path forward slashes will get treated
        #  as escapes when python parses them again otherwise.

        # Analysis block specifies details of the source files to process.
        spec_lines += [
            'a = Analysis(',
            '    [',
            # Files to include.
            # It seems like only the main x4_customizer is needed, everything
            #  else getting recognized correctly.
            '        "Main.py",',
            '    ],',

            # Relative path to work in; just use here.
            '    pathex = [r"{}"],'.format(str(This_dir)),
            # Misc external binaries; unnecessary.
            '    binaries = [],',
            # Misc data files. While the source/patches folders could be
            #  included, it makes more sense to somehow launch the generated
            #  exe from the expected location so those folders are
            #  seen as normal.
            '    datas = [],',

            # Misc imports pyinstaller didn't see.
            '    hiddenimports = [',
            # Add in regex, since it can be handy for runtime imported packages.
            #-Removed, heavyweight.
            #'        r"re",',
            # Add fnmatch instead (wildcard style string matching).
            # -This might be removable if it is in the framework.
            '        r"fnmatch",',
            # Inspect is used in the Live_Editor to ease some code writing.
            '        r"inspect",',
            # Multiprocessing can be used by plugins for speedups.
            '        r"multiprocessing",',
            # Add pyqt for the gui plugin.
            # Pyinstaller needs a lot of help on this one when not being
            # given the original source files (which are in plugins).
            '        r"PyQt5",'          ,#if mode == 'gui' else '',
            '        r"PyQt5.QtWidgets",',#if mode == 'gui' else '',
            '        r"PyQt5.QtCore",'   ,#if mode == 'gui' else '',
            '        r"PyQt5.QtGui",'    ,#if mode == 'gui' else '',
            '        r"PyQt5.uic",'      ,#if mode == 'gui' else '',
            # Not needed directly: profiling script uses configparser.
            '        r"configparser",',
            '    ],',

            '    hookspath = [],',
            # Extra python files to run when the exe starts up.
            '    runtime_hooks = [',
            '        r"{}",'.format(str(hook_file_path)),
            '    ],',

            # Exclude scipy, since it adds 500 MB to the 12 MB compile.
            # Code which uses scipy should have an appropriate backup.
            # Also skip numpy and matplotlib, which are only present for
            #  some optional scaling equation verification.
            '    excludes = [',
            '        r"scipy",',
            '        r"numpy",',
            '        r"matplotlib",',
            '        r"Plugins",', # Make sure the plugins aren't compiled.
            '    ],',

            '    win_no_prefer_redirects = False,',
            '    win_private_assemblies = False,',
            '    cipher = None,',
            ')',
            '',
            ]
    
        spec_lines += [
            'pyz = PYZ(a.pure, a.zipped_data,',
            '     cipher = None,',
            ')',
            '',
        ]
    
        spec_lines += [
            'exe = EXE(pyz,',
            '    a.scripts,',
            '    exclude_binaries = True,',
            '    name = "{}",'.format(program_name),
            '    debug = False,',
            '    strip = False,',
            '    upx = True,',
            # Need console=True to capture responses with |more, but this
            # causes a console to stay open behind the window, so...
            # make this mode based.
            '    console = {},'.format('True' if mode == 'console' else 'False'),
            # To avoid having to use "|more" for the console version,
            # disable windowed mode for it.
            '    windowed = {},'.format('True' if mode == 'gui' else 'False'),
            ')',
            '',
        ]
    
        spec_lines += [
            'coll = COLLECT(exe,',
            '    a.binaries,',
            '    a.zipfiles,',
            '    a.datas,',
            '    strip = False,',
            '    upx = True,',
            '    name = "{}",'.format(program_name),
            ')',
            '',
        ]
    
    
        # Write the spec and hook files to the build folder, creating it
        #  if needed.
        if not build_folder.exists():
            build_folder.mkdir()
        
        with open(spec_file_path, 'w') as file:
            file.write('\n'.join(spec_lines))
        with open(hook_file_path, 'w') as file:
            file.write('\n'.join(hook_lines))


        # Run pyinstaller.
        # This can call "pyinstaller" directly, assuming it is registered
        #  on the command line, but it may be more robust to run python
        #  and target the PyInstaller package.
        # By going through python, it is also possible to set optimization
        #  mode that will be applied to the compiled code.
        # TODO: add optimization flag.
        pyinstaller_call_args = [
            'python', 
            '-m', 'PyInstaller', 
            str(spec_file_path),
            '--distpath', str(dist_folder),
            '--workpath', str(build_folder),
            ]

        # Set a clean flag if requested, making pyinstaller do a fresh
        #  run. Alternatively, could just delete the work folder.
        # Update: pyinstaller cannot deal with nested folders (needs to be
        #  called once for each folder, so deletion should probably be done
        #  manually here.
        if parsed_args.preclean:
            #pyinstaller_call_args.append('--clean')
            if build_folder.exists():
                Clear_Dir(build_folder)

        #-Removed entirely; this isn't useful, and the assetions are
        # used in some places to signal errors.
        # Add the optimization flag, OO taking precedence.
        # Put this flag before the -m and script name, else it gets fed
        #  to the script.
        # (In practice, these seem to make little to no difference, but are
        #  kinda neat to have anyway.)
        # -Removed; some places now reference docstrings, so need to keep them.
        #if parsed_args.oo:
        #    pyinstaller_call_args.insert(1, '-OO')
        #elif parsed_args.o:
        #    pyinstaller_call_args.insert(1, '-O')

        # Run pyinstaller.
        subprocess.run(pyinstaller_call_args)


        # Check if the exe was created.
        exe_path = dist_folder / program_name / (program_name + '.exe')
        if not exe_path.exists():
            # It wasn't found; quit early.
            print('Executable not created.')
            return


        # Traverse the folder with the files; this was collected under
        #  another folder with the name of the program.
        path_to_exe_files = dist_folder / program_name
        for path in path_to_exe_files.iterdir():

            # Move the file up one level, and down to the support folder.
            # Note: after some digging, it appears shutil deals with folders
            #  by passing to 'copytree', which doesn't work well if the
            #  dest already has a folder of the same name (apparently
            #  copying over to underneath that folder, eg. copying /PyQt
            #  to someplace with /PyQt will end up copying to /PyQt/PyQt).
            # Only do this move if the destination doesn't already have
            #  a copy of the file/dir.
            dest_path = dist_folder / path.name
            if not dest_path.exists():
                shutil.move(path, dest_path)
            
        # Clean out the now empty folder in the dist directory.
        Clear_Dir(path_to_exe_files)
        # Clean up the spec and hook files.
        spec_file_path.unlink()
        hook_file_path.unlink()


    # When here, the console and gui versions should be ready
    # and collected into the same bin folder.

    # Delete the pyinstaller work folder, if requested.
    if parsed_args.postclean:
        # Note: rmtree is pretty flaky, so put it in a loop to keep
        # trying the removal.
        if build_folder.exists():
            Clear_Dir(build_folder)


    # Set up bat files for easier launching.
    # To support calling the bat from elsewhere, need to prefix
    #  the exe with %~dp0\ (which fills the bat file folder path).
    # The path needs to be quoted to support spaces.
    exe_command = os.path.join(r'"%~dp0\bin', program_name_console + '.exe"')
    bat_file_details_list = [
        {
            'name' : 'Run_Script',
            # Use '%*' to pass all command line args.
            # The " | MORE" tag supposedly will capture stdout of
            #  the tool even though it was compiled for a window,
            #  but that isn't useful anymore with separate compiles.
            'cmd'  : exe_command + ' -nogui %*',
            # Pause the window when done, so messages can be read.
            'pause': True,
            },
        {
            'name' : 'Clean_Script',
            'cmd'  : exe_command + ' -nogui %* -clean',
            'pause': True,
            },
        {
            'name' : 'Cat_Unpack',
            'cmd'  : exe_command + ' -nogui Cat_Unpack -argpass %*',
            'pause': True,
            },
        {
            'name' : 'Cat_Pack',
            'cmd'  : exe_command + ' -nogui Cat_Pack -argpass %*',
            'pause': True,
            },
        {
            'name' : 'Check_Extensions',
            'cmd'  : exe_command + ' -nogui Check_Extensions -argpass %*',
            'pause': True,
            },
        {
            'name' : 'Start_Gui',
            # Use 'start' to launch the gui and close the bat window
            # right away.
            # Because of oddities with 'start', which treats the first arg
            #  as a label if quoted, give it a dummy set of quotes first.
            # "" "%~dp0\
            'cmd'  : 'start "" ' + exe_command.replace(program_name_console, program_name_gui) + ' %*',
            # No pausing for now; probably just annoying if the gui
            # doesn't crash.
            'pause': False,
            },
        ]

    # Create the bat files.
    for bat_file_details in bat_file_details_list:
        file_name = This_dir / '..' / (bat_file_details['name'] + '.bat')
        lines = [
            # Disable the echo of the command.
            '@echo off',
            bat_file_details['cmd'],
            ]
        if bat_file_details['pause']:
            # Wait for user input, so they can read messages.
            lines.append('pause')
        with open(file_name, 'w') as file:
            file.write('\n'.join(lines))

    # Restory any original workind directory, in case this function
    #  was called from somewhere else.
    os.chdir(original_cwd)


if __name__ == '__main__':
    # Feed all args except the first (which is the file name).
    Make(*sys.argv[1:])

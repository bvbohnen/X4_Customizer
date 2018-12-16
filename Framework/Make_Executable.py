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
    the basic bootstrapping.

3)  Make a bat file to launch the app, which can more easily pass
    command line args.



TODO:
Consider bundling with documentation into a zip file automatically,
include all misc files from the source and patches folders.
'''

import argparse
import sys
import os
import shutil

# Conditional import of pyinstaller, checking if it is available.
try:
    import PyInstaller
except:
    print('Error: PyInstaller not found.')
    sys.exit()

import subprocess

This_dir = os.path.normpath(os.path.join(os.path.dirname(__file__)))

def Make(*args):

    # Scrap the first arg if it is a .py file; this is mostly because
    #  visual studio is set to insert it for normal customizer
    #  calls, and it is bothersome to remove that when testing
    #  this script.
    try:
        if args[0].endswith('.py'):
            args = args[1:]
    except:
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
        '-o', '-O', 
        action='store_true',
        help = 'Compile with basic python optimization, removing assertions'
               ' and perhaps some debug checks.')
    
    argparser.add_argument(
        '-oo', '-OO', 
        action='store_true',
        help = 'Compile with more python optimization, similar to -O'
               ' but also trimming docstrings to reduce code size.')
    
    # Run the parser on the input args.
    parsed_args = argparser.parse_args(args)


    # Set the output folder names.
    # Note: changing the pyinstaller build and dist folder names is
    #  possible, but not through the spec file (at least not easily),
    #  so do it through the command line call.
    build_folder = os.path.join('..','pyinstaller_build_files')
    
    # Pick the final location to place the exe and support files.
    # This should have the same relative path to reach any common
    #  files in the source and patches folders, which can be
    #  moved up under the main level (so the x4_customizer exe
    #  can be down one folder, and the python down another folder).
    dist_folder = os.path.normpath(os.path.join(This_dir, '..', 'bin'))
    # Subfolder to shove misc exe support files into.
    # Update: the new pyinstaller with python 3.7 doesn't like moving
    # these files away from the exe.
    exe_support_folder = os.path.join(dist_folder)#, 'support')
    
    program_name = 'X4_Customizer'
    # Note: it would be nice to put the spec file in a subfolder, but
    #  pyinstaller messes up (seems to change its directory to wherever
    #  the spec file is) and can't find the source python, so the spec
    #  file needs to be kept in the main dir and cleaned up at the end.
    spec_file_path = 'X4_Customizer.spec'
    # Hook file probably works like the spec file.
    hook_file_path = 'pyinstaller_x4c_hook.py'


    # Change the working directory to here.
    # May not be necessary, but pyinstaller not tested for running
    #  from other directories, and this just makes things easier
    #  in general.
    original_cwd = os.getcwd()
    os.chdir(This_dir)

    
    # Generate lines for a hook file.
    # With the packaging of X4_Customizer, this doesn't appears to
    #  be needed anymore.
    # TODO: maybe remove entirely.
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
        '    pathex = [r"{}"],'.format(This_dir),
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
        '        r"fnmatch",',
        '    ],',

        '    hookspath = [],',
        # Extra python files to run when the exe starts up.
        '    runtime_hooks = [',
        '        "{}",'.format(hook_file_path),
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
        '    console = True,',
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
    if not os.path.exists(build_folder):
        os.mkdir(build_folder)
        
    with open(spec_file_path, 'w') as file:
        file.write('\n'.join(spec_lines))
    with open(hook_file_path, 'w') as file:
        file.write('\n'.join(hook_lines))


    # Delete the existing dist directory; pyinstaller has trouble with
    #  this for some reason (maybe using os.remove, which also seemed
    #  to have the same permission error pyinstaller gets).
    if os.path.exists(dist_folder):
        # Use shutil for this; os.remove is for a file, os.rmdir is
        #  for an empty directory, but shutil rmtree will handle
        #  the whole thing.
        shutil.rmtree(dist_folder)


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
        spec_file_path,
        '--distpath', dist_folder,
        '--workpath', build_folder,
        ]

    # Set a clean flag if requested, making pyinstaller do a fresh
    #  run. Alternatively, could just delete the work folder.
    if parsed_args.preclean:
        pyinstaller_call_args.append('--clean')

    # Add the optimization flag, OO taking precedence.
    # Put this flag before the -m and script name, else it gets fed
    #  to the script.
    # (In practice, these seem to make little to no difference, but are
    #  kinda neat to have anyway.)
    if parsed_args.oo:
        pyinstaller_call_args.insert(1, '-OO')
    elif parsed_args.o:
        pyinstaller_call_args.insert(1, '-O')

    subprocess.run(pyinstaller_call_args)


    # Check if the exe was created.
    exe_path = os.path.join(dist_folder, program_name, program_name + '.exe')
    if not os.path.exists(exe_path):
        # It wasn't found; quit early.
        print('Executable not created.')
        return


    # Move most files to a folder under the exe.
    # Create the folder to move to first.
    if not os.path.exists(exe_support_folder):
        os.mkdir(exe_support_folder)
    # Traverse the folder with the files; this was collected under
    #  another folder with the name of the program.
    path_to_exe_files = os.path.join(dist_folder, program_name)
    for file_name in os.listdir(path_to_exe_files):

        # These select names will be kept together and moved to the
        #  bin folder.
        if file_name in [
            program_name + '.exe',
            'base_library.zip',
            'pyexpat.pyd',
            'python36.dll',
            ]:
            # Move the file up one level to the dist folder.
            shutil.move(
                os.path.join(path_to_exe_files, file_name),
                os.path.join(dist_folder, file_name),
                )
        else:
            # Move the file up one level, and down to the support folder.
            shutil.move(
                os.path.join(path_to_exe_files, file_name),
                os.path.join(exe_support_folder, file_name),
                )
            
    # Clean out the now empty folder in the dist directory.
    os.rmdir(path_to_exe_files)
    # Clean up the spec and hook files.
    os.remove(spec_file_path)
    os.remove(hook_file_path)

    # Delete the pyinstaller work folder, if requested.
    if parsed_args.postclean:
        if os.path.exists(build_folder):
            shutil.rmtree(build_folder)


    # Set up bat files for easier launching.
    bat_file_details_list = [
        {
            'name' : 'Launch_X4_Customizer',
            # Use '%*' to pass all command line args.
            'cmd'  : os.path.join('bin', program_name + '.exe') + ' %*',
            },
        {
            'name' : 'Clean_X4_Customizer',
            'cmd'  : os.path.join('bin', program_name + '.exe') + ' %* -clean',
            },
        {
            'name' : 'Cat_Unpack',
            # Set to pass extra command line args.
            'cmd'  : os.path.join('bin', program_name + '.exe') + ' Cat_Unpack -argpass %*',
            },
        {
            'name' : 'Cat_Pack',
            # Set to pass extra command line args.
            'cmd'  : os.path.join('bin', program_name + '.exe') + ' Cat_Pack -argpass %*',
            },
        {
            'name' : 'Check_Extensions',
            # Set to pass extra command line args.
            'cmd'  : os.path.join('bin', program_name + '.exe') + ' Check_Extensions -argpass %*',
            },
        ]

    # Create a bat file for launching the exe from the top level directory.
    for bat_file_details in bat_file_details_list:
        file_name = os.path.join(This_dir, '..', bat_file_details['name'] + '.bat')
        lines = [
            # Disable the echo of the command.
            '@echo off',
            bat_file_details['cmd'],
            # Wait for user input, so they can read messages.
            'pause',
            ]
        with open(file_name, 'w') as file:
            file.write('\n'.join(lines))

    # Restory any original workind directory, in case this function
    #  was called from somewhere else.
    os.chdir(original_cwd)


if __name__ == '__main__':
    # Feed all args except the first (which is the file name).
    Make(*sys.argv[1:])

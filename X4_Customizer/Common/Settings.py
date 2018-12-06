'''
Container for general customize settings.
Import as:
    from Settings import Settings

'''
import os
from pathlib import Path

class Settings_class:
    '''
    Container for general settings, including system paths.
    Primarily used for organization convenience.
    Paths tend to be filled in by a call to Set_Paths; some other
    flags are initialized from command line arguments.

    Attributes:
    * path_to_x4_folder
      - String, the path to the main x4 folder.
      - Converted to a full path if a relative path was given.
    * path_to_output_folder
      - String, the path to where files should be written.
      - If None, defaults to the path_to_x4_folder, so that files can
        be immediately recognized by the game.
      - Primary for use when testing generated outputs without risk
        of overwriting game files.
    * path_to_source_folder
      - String, the path to the source folder, either a full path or relative
        to the calling location.
      - Constructed from path_to_addon_folder and source_folder.
      - None if no source folder specified.
    * message_file_name
      - String, name a file to write detailed output messages to.
    * log_file_name
      - String, name a file to write json log output to.
    * disable_cleanup_and_writeback
      - Bool, if True then cleanup from a prior run as well as any final
        writes will be skipped.
    * write_file_source_paths_to_message_log
      - Bool, if True then the path for any source files read will be
        printed in the message log.
    * skip_all_transforms
      - Bool, if True all transforms will be skipped.
      - For use during cleaning mode.
    * ignore_loose_files
      - Bool, if True then any files loose in the game folders (outside
        the user source folder or a cat/dat pair) will be ignored, as
        if they were produced by the customizer on a prior run.
    * use_scipy_for_scaling_equations
      - Bool, if True then scipy will be used to optimize scaling
        equations, for smoother curves between the boundaries.
      - If False or scipy is not found, then a simple linear scaling
        will be used instead.
    * show_scaling_plots
      - Bool, if True and matplotlib and numpy are available, any
        generated scaling equations will be plotted (and their
        x and y vectors printed for reference). Close the plot window
        manually to continue transform processing.
    * developer
      - Bool, if True then enable some behavior meant just for development,
        such as leaving exceptions uncaught or letting file patchers do
        the best job they can when hitting problems.
    * verbose
      - Bool, if True some extra status messages may be printed.
    * allow_path_error
      - Bool, if True then if the x4 path looks wrong, the customizer
        will still attempt to run.
    * output_to_catalog
      - Bool, if True then the modified files will be written to a single
        cat/dat pair, incrementally numbered above existing catalogs.
      - Scripts will be kept as loose files.
    '''
    # TODO: language selection for modifying t files.
    def __init__(self):
        self.path_to_x4_folder = None
        self.path_to_output_folder = None
        self.path_to_source_folder = None
        self.message_file_name = None
        self.log_file_name = None
        # Temp entry for relative source folder.
        self._relative_source_folder = None
        self.disable_cleanup_and_writeback = False
        self.write_file_source_paths_to_message_log = False
        self.skip_all_transforms = False
        self.ignore_loose_files = False
        self.use_scipy_for_scaling_equations = True
        self.show_scaling_plots = False
        self.developer = False
        self.verbose = True
        self.allow_path_error = False
        self.target_base_tc = False
        self.output_to_catalog = True
        

    def Set_X4_Folder(self, path):
        '''
        Sets the addon folder and x4 folder paths, from the X4 folder
        initial path. Updates the path_to_source_folder if needed.
        '''
        self.path_to_x4_folder = Path(path).resolve()
        # Update the full source path.
        self.Update_Source_Folder_Path()


    def Set_Output_Folder(self, path):
        '''
        Sets the folder to output generated game files to, as if it
        were the x4 folder.
        '''
        # Convert to a Path without resolving.
        path = Path(path)
        # Check if it was an absolute path.
        if path.is_absolute():
            # Record directly; resolve to be extra safe.
            self.path_to_output_folder = path.resolve()
        else:
            # It was relative, so join to the x4 folder.
            # (TODO: or possibly the working directory?)
            self.path_to_output_folder = self.path_to_x4_folder / path


    def Set_Source_Folder(self, path):
        '''
        Sets the source folder path relative to the x4 folder, and
        updates its absolute path if the x4 folder is known and the
        given path is not absolute.
        '''
        # Convert to a Path without resolving.
        path = Path(path)
        # Check if it was an absolute path.
        if path.is_absolute():
            # Record directly; resolve to be extra safe.
            self.path_to_source_folder = path.resolve()
        else:
            # Relative paths get stored, and may be updated to a full
            #  path right away if the addon folder is known.
            self._relative_source_folder = path
            # Update the full source path.
            self.Update_Source_Folder_Path()


    def Update_Source_Folder_Path(self):
        '''
        Update the full source path if x4 and source folders specified
        and source is relative.
        '''
        # If the x4 and relative source folders are available.
        if (self.path_to_x4_folder != None 
        and self._relative_source_folder != None):
            # Add to the x4 path.
            self.path_to_source_folder = (self.path_to_x4_folder 
                                        / self._relative_source_folder)
            

    def Set_Message_File(self, file_name):
        '''
        Sets the file name to use for any transform messages.
        '''
        self.message_file_name = file_name


    def Set_Log_File(self, file_name):
        '''
        Sets the file name to use for the json log.
        '''
        self.log_file_name = file_name


    def Verify_Setup(self):
        '''
        Checks the current paths for errors (not existing, etc.).
        Some situations may just throw warnings.
        Creates the source folder if it does not exist.
        '''
        # Verify the X4 path looks correct.
        if not self.path_to_x4_folder.exists():
            raise Exception(
                'Path to the X4 folder appears to not exist.'
                +'\n (x4 path: {})'.format(self.path_to_x4_folder)
                )

        # Check for 01.cat.
        # Print a warning but continue if anything looks wrong; the user
        #  may wish to have this tool generate files to a separate
        #  directory first.
        if not (self.path_to_x4_folder / '01.cat').exists():
            if self.allow_path_error:
                print(  
                    'Warning: Path to the X4 folder appears wrong.\n'
                    'Generated files may need manual moving to the correct folder.\n'
                    'Automated source file extraction may fail.'
                    +'\n (x4 path: {})'.format(self.path_to_x4_folder)
                    )
            else:
                # Hard error.
                raise Exception(
                    'Path does not appear correct for the X4 folder.'
                    +'\n (x4 path: {})'.format(self.path_to_x4_folder)
                    )

        # Set the output folder to 'extensions/X4_Customizer'
        #  under the x4 folder.
        # TODO: option to place this in user documents instead.
        # Note: an extensions subfolder is added afterward.
        # TODO: should 'extensions' be added here, or even
        #  'extensions/X4_Customizer'?
        if self.path_to_output_folder == None:
            self.path_to_output_folder = self.path_to_x4_folder / 'extensions'/'X4_Customizer'

        # Create the output folder if it does not exist.
        if not self.path_to_output_folder.exists():
            # Add any needed parents as well.
            self.path_to_output_folder.mkdir(parents = True)

        return


    def Get_X4_Folder(self, extra_path = None):
        '''
        Returns the path to the X4 base folder, optionally with some
        extra relative path applied.
        '''
        if extra_path != None:
            return self.path_to_x4_folder / Path(extra_path)
        return self.path_to_x4_folder


    def Get_Output_Folder(self, extra_path = None):
        '''
        Returns the path to the output folder, optionally with some
        extra relative path applied.
        '''
        if extra_path != None:
            return self.path_to_output_folder / Path(extra_path)
        return self.path_to_output_folder


    def Get_Source_Folder(self, extra_path = None):
        '''
        Returns the path to the Source folder, optionally with some
        extra relative path applied.
        '''
        if extra_path != None:
            return self.path_to_source_folder / Path(extra_path)
        return self.path_to_source_folder


    def Get_Message_File_Path(self):
        '''
        Returns the path to the message file, including file name.
        '''
        return self.path_to_output_folder / self.message_file_name


    def Get_Log_File_Path(self):
        '''
        Returns the path to the log file, including file name.
        '''
        return self.path_to_output_folder / self.log_file_name


# General settings object, to be referenced by any place so interested.
Settings = Settings_class()


# This is the main access function input scripts are expected to use.
# This docstring will be included in documentation.
def Set_Path(
        # Force args to be kwargs, since that is safer if args are
        #  added/removed in the future.
        *,
        path_to_x4_folder = None,
        path_to_output_folder = None,
        path_to_source_folder = None,
        # TODO: path to user documents to read content.xml.
        summary_file = 'summary.txt',
        log_file = 'log.json',
    ):
    '''
    Sets the paths to be used for file loading and writing.

    * path_to_x4_folder
      - Path to the X4 base folder, where the executable is located.
    * path_to_output_folder
      - Optional, path to a folder to place output files in.
      - Defaults to match path_to_x4_folder, so that outputs are
        directly readable by the game.
    * path_to_source_folder
      - Optional, alternate folder which contains source files to be modified.
      - Maybe be given as a relative path to the "addon" directory,
        or as an absolute path.
      - Files located here should have the same directory structure
        as standard games files, eg. 'source_folder/types/Jobs.txt'.
    * summary_file
      - Name for where a summary file will be written, with
        any transform results, relative to the output folder.
      - Defaults to 'summary.txt'.
    * log_file
      - Name for where a json log file will be written,
        including a summary of files written.
      - This is also the file which will be read for any log from
        a prior run.
      - Defaults to 'log.json'.
    '''
    # Hide these behind None checks, to be extra safe; the Settings 
    #  verification should catch problems.
    # TODO: maybe trim Nones from here if checked in the Settings methods.
    if path_to_x4_folder != None:
        Settings.Set_X4_Folder(path_to_x4_folder)
    if path_to_source_folder != None:
        Settings.Set_Source_Folder(path_to_source_folder)
    if path_to_output_folder != None:
        Settings.Set_Output_Folder(path_to_output_folder)
    if summary_file != None:
        Settings.Set_Message_File(summary_file)
    if log_file != None:
        Settings.Set_Log_File(log_file)

    # Note: verification is done at the first transform, not here,
    #  so that any settings overwrites can be done after (or without)
    #  the Set_Path call.
    # Note: skipping Init until later isn't entirely safe if no
    #  transforms were run (eg. if a new user runs the template file,
    #  where all transforms are commented out).  Ensure Init gets run
    #  at some late point if needed to complete path checks, since
    #  old transform files may still need to be cleaned out using these
    #  paths.

    return

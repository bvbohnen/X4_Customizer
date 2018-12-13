'''
Container for general customize settings.
Import as:
    from Settings import Settings

'''
import os
from pathlib import Path

class Settings_class:
    '''
    This holds general settings and paths to control the customizer.
    Adjust these settings as needed prior to running the first plugin,
    using direct writes to attributes.

    Settings may be updated individually, or as arguments of
    a call to Settings.
    Examples:
    * Settings.path_to_x4_folder   = 'C:\...'
    * Settings.path_to_user_folder = 'C:\...'
    * Settings(
         path_to_x4_folder = 'C:\...',
         path_to_user_folder = 'C:\...')

    Paths:
    * path_to_x4_folder
      - Path to the main x4 folder.
      - Defaults to HOMEDRIVE/"Steam/steamapps/common/X4 Foundations"
    * path_to_user_folder
      - Path to the folder where user files are located.
      - Should include config.xml, content.xml, etc.
      - Defaults to HOMEPATH/"Documents/Egosoft/X4" or a subfolder
        with an 8-digit name.
    * path_to_source_folder
      - Optional path to a source folder that holds high priority source
        files, which will be used instead of reading the x4 cat/dat files.
      - For use when running plugins on manually edited files.
      - Defaults to None
    * allow_path_error
      - Bool, if True and the x4 or user folder path looks wrong, the
        customizer will still attempt to run (with a warning).
      - Defaults to False
      
    Input:
    * prefer_single_files
      - Bool, if True then loose files will be used before those in cat/dat
        files, otherwise cat/dat takes precedence.
      - Only applies within a single search location, eg. within an
        extension, within the source folder, or within the base X4 folder;
        a loose file in the source folder will still be used over those
        in the X4 folder regardless of setting.
      - Defaults to False
    * ignore_extensions
      - Bool, if True then extensions will be ignored, and files are
        only sourced from the source_folder or x4_folder.
      - Defaults to False
    * allow_cat_md5_errors
      - Bool, if True then when files extracted from cat/dat fail
        to verify their md5 hash, no exception will be thrown.
      - Defaults to False; consider setting True if needing to
        unpack incorrectly assembled catalogs.

    Output:
    * extension_name
      - String, name of the extension being generated.
      - Spaces will be replaced with underscores for the extension id.
      - Defaults to 'X4_Customizer'
    * output_to_user_extensions
      - Bool, if True then the generated extension holding output files
        will be under <path_to_user_folder/extensions>.
      - Defaults to False, writing to <path_to_x4_folder/extensions>
    * output_to_catalog
      - Bool, if True then the modified files will be written to a single
        cat/dat pair, otherwise they are written as loose files.
      - Defaults to False
    * make_maximal_diffs
      - Bool, if True then generated xml diff patches will do the
        maximum full tree replacement instead of using the algorithm
        to find and patch only edited nodes.
      - Turn on to more easily view xml changes.
      - Defaults to False.

    Logging:
    * plugin_log_file_name
      - String, name a text file to write plugin output messages to;
        content depends on plugins run.
      - File is located in the output extension folder.
      - Defaults to 'plugin_log.txt'
    * customizer_log_file_name
      - String, name a json file to write customizer log information to,
        including a list of files written.
      - File is located in the output extension folder.
      - Defaults to 'customizer_log.json'
    * log_source_paths
      - Bool, if True then the path for any source files read will be
        printed in the plugin log.
      - Defaults to False
    * verbose
      - Bool, if True some extra status messages may be printed to the
        console.
      - Defaults to False

    Behavior:
    * disable_cleanup_and_writeback
      - Bool, if True then cleanup from a prior run and any final
        writes will be skipped.
      - For use when testing plugins without modifying files.
      - Defaults to False
    * skip_all_plugins
      - Bool, if True all plugins will be skipped.
      - For use during cleaning mode.
      - Defaults to False
    * developer
      - Bool, if True then enable some behavior meant just for development,
        such as leaving exceptions uncaught.
      - Defaults to False
    * use_scipy_for_scaling_equations
      - Bool, if True then scipy will be used to optimize scaling
        equations, for smoother curves between the boundaries.
      - If False or scipy is not found, then a simple linear scaling
        will be used instead.
      - Defaults to True
    * show_scaling_plots
      - Bool, if True and matplotlib and numpy are available, any
        generated scaling equations will be plotted (and their
        x and y vectors printed for reference). Close the plot window
        manually to continue plugin processing.
      - Primarily for development use.
      - Defaults to False
    '''
    '''
    TODO:
    * generate_content_xml
      - Bool, when True a new content.xml will be generated for the
        extension, overwriting any that already exists.
      - Set False if wishing to reuse a custom content.xml, eg. one with
        custom description. The existing file may be modified to
        fill in dependencies.
      - Defaults True.
    '''
    # TODO: language selection for modifying t files.
    def __init__(self):

        # For the path lookups, use os.environ to look up some windows
        # path terms, but in case they aren't found just use '.' so
        # this doesn't error out here.
        self.path_to_x4_folder   = (Path(os.environ.get('HOMEDRIVE','.')) 
                                    / 'Steam/steamapps/common/X4 Foundations')
        self.path_to_user_folder = (Path(os.environ.get('HOMEPATH','.'))  
                                    / 'Documents/Egosoft/X4')
        
        # If the user folder exists but has no config.xml, check an id folder.
        # Note: while content.xml is wanted, it apparently not always
        # created (maybe only made the first time a mod gets enabled/disabled
        # in the menu?).
        if (self.path_to_user_folder.exists() 
        and not (self.path_to_user_folder / 'config.xml').exists()):
            # Iterate through all files and dirs.
            for dir in self.path_to_user_folder.iterdir():
                # Skip non-dirs.
                if not dir.is_dir():
                    continue
                # Check for the config.xml.
                # Probably don't need to check folder name for digits;
                # common case just has one folder.
                if (dir / 'config.xml').exists():
                    # Record it and stop looping.
                    self.path_to_user_folder = dir
                    break
                

        self.extension_name = 'X4_Customizer'
        self.output_to_user_extensions = False
        self.path_to_source_folder = None
        self.prefer_single_files = False
        self.ignore_extensions = False
        self.allow_cat_md5_errors = False
        self.make_maximal_diffs = False
        self.plugin_log_file_name = 'plugin_log.txt'
        self.customizer_log_file_name = 'customizer_log.json'
        self.disable_cleanup_and_writeback = False
        self.log_source_paths = False
        self.skip_all_plugins = False
        self.use_scipy_for_scaling_equations = True
        self.show_scaling_plots = False
        self.developer = False
        self.verbose = True
        self.allow_path_error = False
        self.output_to_catalog = False

        # Flag to track if delayed init has completed.
        self._init_complete = False
        return
        

    def __call__(self, *args, **kwargs):
        '''
        Convenience function for applying settings by calling
        the settings object with fields to set.
        '''
        # Ignore args; just grab kwargs.
        for name, value in kwargs.items():
            # Warn on unexpected names.
            if not hasattr(self, name):
                print('Warning: setting "{}" not recognized'.format(name))
            else:
                setattr(self, name, value)
        return


    def Delayed_Init(self):
        '''
        Checks the current paths for errors (not existing, etc.), converts
        them to Path objects, creates the output extension folder, etc.
        '''
        # Limit to running just once, though this might get called
        # on every plugin.
        if self._init_complete:
            return
        self._init_complete = True

        # Start with conversions to full Paths, since the user
        # may have written these with strings.
        self.path_to_x4_folder     = Path(self.path_to_x4_folder).resolve()
        self.path_to_user_folder   = Path(self.path_to_user_folder).resolve()
        if self.path_to_source_folder != None:
            self.path_to_source_folder = Path(self.path_to_source_folder).resolve()

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
            message = ('Warning: Path to the X4 folder appears incorrect.'
                    '\n (x4 path: {})').format(self.path_to_x4_folder)
            if self.allow_path_error:
                print(message)
            else:
                # Hard error.
                raise Exception(message)
            
        # Check the user folder for config.xml.
        if not (self.path_to_user_folder / 'config.xml').exists():
            message = ('Path to the user folder appears incorrect, lacking'
                    ' config.xml.\n (path: {})').format(self.path_to_user_folder)
            if self.allow_path_error:
                print(message)
            else:
                # Hard error.
                raise Exception(message)

        # Create the output folder if it does not exist,
        #  so that runtime logging can go here.
        if not self.Get_Output_Folder().exists():
            # Add any needed parents as well.
            self.Get_Output_Folder().mkdir(parents = True)

        return


    def Get_X4_Folder(self):
        'Returns the path to the X4 base folder.'
        return self.path_to_x4_folder
    
    def Get_User_Folder(self):
        'Returns the path to the user folder.'
        return self.path_to_user_folder

    def Get_Output_Folder(self):
        'Returns the path to the output extension folder.'
        # Pick the user or x4 folder.
        if self.output_to_user_extensions:
            path = self.path_to_user_folder
        else:
            path = self.path_to_x4_folder
        # Offset to the extension.
        return path / 'extensions' / self.extension_name

    def Get_Source_Folder(self):
        'Returns the path to the Source folder.'
        return self.path_to_source_folder

    def Get_Plugin_Log_Path(self):
        'Returns the path to the plugin log file.'
        return self.Get_Output_Folder() / self.plugin_log_file_name

    def Get_Customizer_Log_Path(self):
        'Returns the path to the customizer log file.'
        return self.Get_Output_Folder() / self.customizer_log_file_name
    
    def Get_User_Content_XML_Path(self):
        'Returns the path to the user content.xml file.'
        return self.path_to_user_folder / 'content.xml'


# General settings object, to be referenced by any place so interested.
Settings = Settings_class()


'''
Container for general customize settings.
Import as:
    from Settings import Settings

'''
import os
from pathlib import Path
import json
from collections import OrderedDict
from functools import wraps
from .Home_Path import home_path
from .Print import Print

class Settings_class:
    '''
    This holds general settings and paths to control the customizer.
    Adjust these settings as needed prior to running the first plugin,
    using direct writes to attributes.

    Settings may be updated individually, or as arguments of
    a call to Settings, or through a "settings.json" file in the
    top X4 Customizer folder (eg. where documentation resides).
    Any json settings will overwrite defaults, and be overwritten by
    settings in the control script. Changes made using the GUI
    will be applied to the json settings.

    Examples:
    * In the control script (prefix paths with 'r' to support backslashes):
      <code>
          Settings.path_to_x4_folder   = r'C:\...'
          Settings.path_to_user_folder = r'C:\...'
          Settings(
               path_to_x4_folder   = r'C:\...',
               path_to_user_folder = r'C:\...'
               )
      </code>
    * In settings.json (sets defaults for all scripts):
      <code>
          {
            "path_to_x4_folder"        : "C:\...",
            "path_to_user_folder"      : "C:\...",
            "output_to_user_extensions": "true"
          }
      </code>

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
    * ignore_output_extension
      - Bool, if True, the target extension being generated will have
        its prior content ignored (this run works on the original files,
        and not those changes made last run).
      - Defaults to True; should only be set False if not running
        transforms and wanting to analyse prior output.
    * X4_exe_name
      - String, name of the X4.exe file, to be used when sourcing the file
        for any exe transforms (if used), assumed to be in the x4 folder.
      - Defaults to "X4.exe", but may be useful to change based on the
        source exe file for transforms, eg. "X4_nonsteam.exe",
        "X4_steam.exe", or similar.
      - Note: the modified exe is written to the x4 folder with a ".mod.exe"
        extension, and will not be removed on subsequent runs even
        if they do not select any exe editing transforms. If wanting this
        to work with steam, then the X4.exe may need to be replaced with
        this modified exe manually.

    Output:
    * extension_name
      - String, name of the extension being generated.
      - Spaces will be replaced with underscores for the extension id.
      - A lowercase version of this will be used for the output folder
        name.
      - Defaults to 'X4_Customizer'
    * output_to_user_extensions
      - Bool, if True then the generated extension holding output files
        will be under <path_to_user_folder/extensions>.
      - Warning: any prior output on the original path will still exist,
        and is not cleaned out automatically at the time of this note.
      - Defaults to False, writing to <path_to_x4_folder/extensions>
    * path_to_output_folder
      - Optional, Path to the location to write the extension files to,
        instead of the usual X4 or user documents extensions folders.
      - This is the parent directory to the extension_name folder.
    * output_to_catalog
      - Bool, if True then the modified files will be written to a single
        cat/dat pair, otherwise they are written as loose files.
      - Defaults to False
    * generate_sigs
      - Bool, if True then dummy signature files will be created.
      - Defaults to True.
    * make_maximal_diffs
      - Bool, if True then generated xml diff patches will do the
        maximum full tree replacement instead of using the algorithm
        to find and patch only edited nodes.
      - Turn on to more easily view xml changes.
      - Defaults to False.

    Logging:
    * live_editor_log_file_name
      - String, name a json file which the live editor (tracking hand
        edits in the gui) will save patches to, and reload from.
      - Patches will capture any hand edits made by the user.
      - File is located in the output extension folder.
      - Defaults to 'live_editor_log.json'
    * plugin_log_file_name
      - String, name of a text file to write plugin output messages to;
        content depends on plugins run.
      - File is located in the output extension folder.
      - Defaults to 'plugin_log.txt'
    * customizer_log_file_name
      - String, name a json file to write customizer log information to,
        including a list of files written, information that will be loaded
        on the next run to guide the file handling logic.
      - File is located in the output extension folder.
      - Defaults to 'customizer_log.json'
    * log_source_paths
      - Bool, if True then the path for any source files read will be
        printed in the plugin log.
      - Defaults to False
    * verbose
      - Bool, if True some extra status messages may be printed to the
        console.
      - Defaults to True

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
    * disable_threading
      - Bool, if True then threads will not be used in the gui to
        call scripts and plugins. Will cause the gui to lock up
        during processing.
      - Intended for development use, to enable breakpoints during calls.
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
    - This was moved to an input arg of Write_To_Extension.
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

        # Fill in initial defaults.
        for field, default in self.Get_Defaults().items():
            setattr(self, field, default)
        
        # Very early call to look for a json file to overwrite detaults.
        self.Load_Json()

        # Flag to track if delayed init has completed.
        self._init_complete = False
        return
    

    def _Verify_Init(func):
        '''
        Small wrapper on functions that should verify the init
        check has been done before returning.
        '''
        '''
        Note: this cannot be set as a staticmethod since that
        delays its creation until after it is needed (presumably);
        also, it does not take 'self' on its own, just the
        wrapped func.
        '''
        # Use functools wraps to preserve the docstring and such.
        @wraps(func)
        # All wrapped functions will have self.
        def func_wrapper(self, *args, **kwargs):
            # Run delayed init if needed.
            if not self._init_complete:
                self.Delayed_Init()
            # Run the func as normal.
            return func(self, *args, **kwargs)
        return func_wrapper


    def Reset(self):
        '''
        Resets the settings, such that Delayed_Init will be run
        again. For use when paths may be changed since a prior run.
        '''
        self._init_complete = False
        return


    def Get_Categorized_Fields(self):
        '''
        Returns an OrderedDict, keyed by category, with a list of fields in
        their preferred display order. Parses the docstring to determine
        this ordering.
        '''
        # TODO: maybe cache if this will be called often, but probably
        # doesn't matter.
        category_list_dict = OrderedDict()
        category = None

        # Work through the docstring.
        for line in self.__doc__.splitlines():

            # Category titles are single words with an ending :, no
            #  prefix.
            strip_line = line.strip()
            if strip_line.endswith(':') and strip_line[0] not in ['-','*']:
                category = strip_line.replace(':','')

            # Fields are recognized names after a *.
            elif strip_line.startswith('*'):
                field = strip_line.replace('*','').strip()

                # Check that the doc term maches a local attribute.
                if hasattr(self, field):

                    # A category should have been found at this point.
                    assert category != None

                    # Record the new category if needed.
                    # Note: cannot use defaultdict for this since already
                    # using an OrderedDict.
                    if category not in category_list_dict:
                        category_list_dict[category] = []
                    category_list_dict[category].append(field)

        return category_list_dict


    def Get_Defaults(self):
        '''
        Returns a dict holding fields and their default values.
        Does some dynamic compute to determine default paths, so
        this could potentially change across calls.
        '''
        defaults = {}
        # For the path lookups, use os.environ to look up some windows
        #  path terms, but in case they aren't found just use '.' so
        #  this doesn't error out here.
        # Add '/' after the drive letter, else it gets ignored and the path
        #  is treated as relative.
        # TODO: some sort of smart but fast folder search.
        # TODO: consider placing default settings overrides in a json file,
        #  that will work on all called scripts.
        defaults['path_to_x4_folder']  = (Path(os.environ.get('HOMEDRIVE','.') + '/') 
                                    / 'Steam/steamapps/common/X4 Foundations')
        defaults['path_to_user_folder'] = (Path(os.environ.get('HOMEPATH','.'))  
                                    / 'Documents/Egosoft/X4')
        
        # If the user folder exists but has no config.xml, check an id folder.
        # Note: while content.xml is wanted, it apparently not always
        # created (maybe only made the first time a mod gets enabled/disabled
        # in the menu?).
        if (defaults['path_to_user_folder'].exists() 
        and not (defaults['path_to_user_folder'] / 'config.xml').exists()):
            # Iterate through all files and dirs.
            for dir in defaults['path_to_user_folder'].iterdir():
                # Skip non-dirs.
                if not dir.is_dir():
                    continue
                # Check for the config.xml.
                # Probably don't need to check folder name for digits;
                # common case just has one folder.
                if (dir / 'config.xml').exists():
                    # Record it and stop looping.
                    defaults['path_to_user_folder'] = dir
                    break                

        defaults['extension_name'] = 'X4_Customizer'
        defaults['output_to_user_extensions'] = False
        defaults['path_to_output_folder'] = None        
        defaults['path_to_source_folder'] = None
        defaults['prefer_single_files'] = False
        defaults['ignore_extensions'] = False
        defaults['allow_cat_md5_errors'] = False
        defaults['ignore_output_extension'] = True
        defaults['X4_exe_name'] = 'X4.exe'        
        defaults['make_maximal_diffs'] = False
        defaults['plugin_log_file_name'] = 'plugin_log.txt'
        defaults['live_editor_log_file_name'] = 'live_editor_log.json'        
        defaults['customizer_log_file_name'] = 'customizer_log.json'
        defaults['disable_cleanup_and_writeback'] = False
        defaults['log_source_paths'] = False
        defaults['skip_all_plugins'] = False
        defaults['use_scipy_for_scaling_equations'] = True
        defaults['show_scaling_plots'] = False
        defaults['developer'] = False
        defaults['disable_threading'] = False        
        defaults['verbose'] = True
        defaults['allow_path_error'] = False
        defaults['output_to_catalog'] = False
        defaults['generate_sigs'] = False
        return defaults


    def Load_Json(self):
        '''
        Look for a "settings.json" file in the main x4 customizer directory,
        and load defaults from it.
        Returns a list of field names updated.
        '''
        fields_updated = []

        # Try the home_path and the call directory to find this.
        for json_path in [Path('settings.json'), home_path / 'settings.json']:
            if not json_path.exists():
                continue

            # If the json is malformed, json.load with toss an exception.
            # In that case, just ignore it.
            try:
                with open(json_path, 'r') as file:
                    json_dict = json.load(file)
            except Exception as ex:
                Print(('Skipping load of "settings.json" due to {}.'
                        ).format(type(ex).__name__))
                # Don't continue; just return. Avoids repeating errors
                # if the cwd is the home_path.
                return fields_updated

            # Do some replacements of strings for normal types;
            #  unfortunately json.load doesn't do this automatically.
            replacements_dict = {
                'true' : True,
                'True' : True,
                '1'    : True,
                'false': False,
                'False': False,
                '0'    : False,
                }
            
            # Note: this is unsafe if a path is given that matches one
            #  of these strings, so only apply these replacements for
            #  select fields. This will be based on the defaults, and
            #  which are bools.
            defaults = self.Get_Defaults()

            for key, value in json_dict.items():

                if isinstance(defaults[key], bool):
                    # Convert to python bools.
                    value = replacements_dict.get(value, value)
                elif defaults[key] == None:
                    # Convert none to None for paths.
                    if value == 'none':
                        value = None
                # Paths and string names will be left alone.

                if hasattr(self, key):
                    # This should always be a bool or a string.
                    setattr(self, key, value)
                    fields_updated.append(key)
                else:
                    Print(('Entry "{}" in settings.json not recognized; skipping.'
                           ).format(key))

            # Don't want to check other json files.
            break
        return fields_updated


    def Save_Json(self, fields_to_save):
        '''
        Save the given settings fields to settings.json.
        This should preferably only save non-default settings.
        '''
        json_dict = OrderedDict()
        
        # Field replacements going to json.
        replacements_dict = {
            True : 'true',
            False : 'false',
            None : 'none',
            }
        # Can follow the preferred field order, for readability.
        for category, field_list in self.Get_Categorized_Fields().items():
            for field in field_list:
                # Skip if unwanted.
                if field not in fields_to_save:
                    continue

                value = getattr(self, field)
                # Get any json suitable replacements.
                if value in replacements_dict:
                    value = replacements_dict[value]

                # Stringify, in case it is a Path.
                json_dict[field] = str(value)

        # Always save to the home_path for now.
        with open(home_path / 'settings.json', 'w') as file:
            json.dump(json_dict, file, indent = 2)
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
                Print('Warning: setting "{}" not recognized'.format(name))
            else:
                setattr(self, name, value)
        # Reset to pre-init state, so the new paths and such
        # will get cleaned up and checked.
        self.Reset()
        return


    # TODO: with _Verify_Init in place, wherever this was called
    # originally may no longer need to call it.
    def Delayed_Init(self):
        '''
        Checks the current paths for errors (not existing, etc.), converts
        them to Path objects, creates the output extension folder, etc.
        Raises AssertionError on any critical problem, and may raise
        other exceptions on misc problems.
        Sets _init_complete if no errors are found.
        '''
        # Limit to running just once, though this might get called
        # on every plugin. Note: this flag will only get set after
        # all error checks are passed.
        if self._init_complete:
            return

        # Note: some problems can occur if the user input paths are
        # weird (one guy tried a newline). This code may trigger
        # other exceptions than those listed.

        # Start with conversions to full Paths, since the user
        # may have written these with strings.
        self.path_to_x4_folder     = Path(self.path_to_x4_folder).resolve()
        self.path_to_user_folder   = Path(self.path_to_user_folder).resolve()
        if self.path_to_source_folder != None:
            self.path_to_source_folder = Path(self.path_to_source_folder).resolve()
        if self.path_to_output_folder != None:
            self.path_to_output_folder = Path(self.path_to_output_folder).resolve()

        # Verify the X4 path looks correct.
        if not self.path_to_x4_folder.exists():
            raise AssertionError(
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
                Print(message)
            else:
                # Hard error.
                raise AssertionError(message)
            
        # Check the user folder for config.xml.
        if not (self.path_to_user_folder / 'config.xml').exists():
            message = ('Path to the user folder appears incorrect, lacking'
                    ' config.xml.\n (path: {})').format(self.path_to_user_folder)
            if self.allow_path_error:
                Print(message)
            else:
                # Hard error.
                raise AssertionError(message)

        # Check that file names are given, and not blank.
        # TODO
            
        # If here, can continue with source file processing.
        self._init_complete = True
        return
    

    def Paths_Are_Valid(self):
        '''
        Returns True if all paths appear to be valid and ready
        for game file reading and output writing, else False.
        '''
        # If this makes it through Delayed_Init, either on the first
        # time or because _init_complete is set, then thing should
        # be good to go.
        try:
            self.Delayed_Init()
        except Exception:
            # A problem was encountered.
            return False
        return True


    # The following functions return paths that might be unsafe
    # if delayed init wasn't run yet.
    @_Verify_Init
    def Get_X4_Folder(self):
        'Returns the path to the X4 base folder.'
        return self.path_to_x4_folder
    
    @_Verify_Init
    def Get_User_Folder(self):
        'Returns the path to the user folder.'
        return self.path_to_user_folder
    
    @_Verify_Init
    def Get_Output_Folder(self):
        '''
        Returns the path to the output extension folder.
        Creates it if it does not exist.
        '''
        # Check for an override.
        if self.path_to_output_folder:
            path = self.path_to_output_folder
        else:
            # Pick the user or x4 folder, extensions subfolder.
            if self.output_to_user_extensions:
                path = self.path_to_user_folder
            else:
                path = self.path_to_x4_folder
            # Offset to the extension.
            path = path / 'extensions'

        # Use a lowercase name to improve portability, as it may
        # be required for reliable operation on linux.
        path = path /  (self.extension_name.lower())

        # Create the output folder if it does not exist.
        if not path.exists():
            # Add any needed parents as well.
            path.mkdir(parents = True)
        return path

    
    @_Verify_Init
    def Get_Source_Folder(self):
        'Returns the path to the Source folder.'
        return self.path_to_source_folder
    
    @_Verify_Init
    def Get_Plugin_Log_Path(self):
        'Returns the path to the plugin log file.'
        return self.Get_Output_Folder() / self.plugin_log_file_name
    
    @_Verify_Init
    def Get_Customizer_Log_Path(self):
        'Returns the path to the customizer log file.'
        return self.Get_Output_Folder() / self.customizer_log_file_name
    
    @_Verify_Init
    def Get_User_Content_XML_Path(self):
        'Returns the path to the user content.xml file.'
        return self.path_to_user_folder / 'content.xml'
    
    @_Verify_Init
    def Get_Live_Editor_Log_Path(self):
        'Returns the path to the live editor log file.'
        return self.Get_Output_Folder() / self.live_editor_log_file_name



# General settings object, to be referenced by any place so interested.
Settings = Settings_class()


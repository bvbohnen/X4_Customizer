'''
Container for general customize settings.
Import as:
    from Settings import Settings

'''
import os
from pathlib import Path
import json
from collections import OrderedDict
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
    settings in the control script.

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
        its prior content ignored.
      - Defaults to True; should only be set False if not running
        transforms and wanting to analyse prior output.

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
        for line in self.__doc__.splitlines():
            # Category titles are single words with an ending :, no
            #  prefix.
            strip_line = line.strip()
            if strip_line.endswith(':') and strip_line[0] not in ['-','*']:
                category = strip_line.replace(':','')
            # Fields are recognized names after a *.
            elif strip_line.startswith('*'):
                field = strip_line.replace('*','').strip()
                if hasattr(self, field):
                    assert category != None
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
        defaults['path_to_source_folder'] = None
        defaults['prefer_single_files'] = False
        defaults['ignore_extensions'] = False
        defaults['allow_cat_md5_errors'] = False
        defaults['ignore_output_extension'] = True
        defaults['make_maximal_diffs'] = False
        defaults['plugin_log_file_name'] = 'plugin_log.txt'
        defaults['customizer_log_file_name'] = 'customizer_log.json'
        defaults['disable_cleanup_and_writeback'] = False
        defaults['log_source_paths'] = False
        defaults['skip_all_plugins'] = False
        defaults['use_scipy_for_scaling_equations'] = True
        defaults['show_scaling_plots'] = False
        defaults['developer'] = False
        defaults['verbose'] = True
        defaults['allow_path_error'] = False
        defaults['output_to_catalog'] = False
        return defaults


    def Load_Json(self):
        '''
        Look for a "settings.json" file in the main x4 customizer directory,
        and load defaults from it.
        Returns a list of field names updated.
        '''
        fields_update = []

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
                return fields_update

            # Do some replacements of strings for normal types;
            # unfortunately json.load doesn't do this automatically.
            replacements_dict = {
                'true' : True,
                'True' : True,
                '1'    : True,
                'false': False,
                'False': False,
                '0'    : False,
                'none' : None,
                }

            for key, value in json_dict.items():
                # Convert to python bools.
                value = replacements_dict.get(value, value)
                if hasattr(self, key):
                    # This should always be a bool or a string.
                    setattr(self, key, value)
                    fields_update.append(key)
                else:
                    Print(('Entry "{}" in settings.json not recognized; skipping.'
                           ).format(key))

            # Don't want to check other json files.
            break
        return fields_update


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


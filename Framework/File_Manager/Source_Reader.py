'''
Support for reading source files, including unpacking from cat/dat files.
Includes File_Missing_Exception for when a file is not found.
Import as:
    from .Source_Reader import Source_Reader
'''
import os
from pathlib import Path
from lxml import etree as ET
from collections import namedtuple, OrderedDict
from fnmatch import fnmatch
from itertools import chain

from . import File_Types
from .Cat_Reader import Cat_Reader
from .. import Common
from ..Common import Settings
from ..Common import File_Missing_Exception
from ..Common import Plugin_Log

# Set a list of subfolders that are standard for x4 files.
# Other folders can generally be ignored.
valid_virtual_path_prefixes =  (
    'aiscripts/','assets/','index/','libraries/',
    'maps/','md/','t/','ui/' )
    

class Location_Source_Reader:
    '''
    Class used to look up source files from a single location, such as the
    base X4 folder, the loose source folder, or an extension folder.
    
    Attributes:
    * location
      - Path to the location being sourced from.
      - If not given, auto detection of cat files will be skipped.
    * extension_name
      - String, name of the extension, if an extension, else None.
    * catalog_file_dict
      - OrderedDict of Cat_Reader objects, keyed by file path, organized
        by priority, where the first entry is the highest priority cat.
      - Dict entries are initially None, and get replaced with Catalog_Files
        as the cats are searched.
    * source_file_path_dict
      - Dict, keyed by virtual_path, holding the system path
        for where the file is located, for files in the source folder
        specified in the Settings.
    '''
    def __init__(self, location = None, extension_name = None):
        self.location = location
        self.catalog_file_dict = OrderedDict()
        self.extension_name = extension_name        
        # Search for cats if location given.
        if location != None:
            self.Find_Catalogs(location)
        return
    

    def Find_Catalogs(self, location):
        '''
        Find and record all catalog files at the given location,
        according to the X4 naming convention.
        '''
        # Search for cat files the game will recognize.
        # These start at 01.cat, and count up as 2-digit values until
        #  the count is broken.
        # Extensions observed to use prefixes 'ext_' and 'subst_' on
        #  their cat/dat files. Some details:
        #  'subst_' get loaded first, and overwrite lower game files
        #  instead of patching them (eg. 'substitute').
        #  'ext_' get loaded next, and are treated as patches.
        prefixes = ['']
        if self.extension_name:
            prefixes = ['subst_','ext_']

        # For convenience, the first pass will fill in a list with low
        #  to high priority, then the list can be reversed at the end.
        cat_dir_list_low_to_high = []

        for prefix in prefixes:
            # Loop until a cat index not found.
            cat_index = 1
            while 1:
                # Error if hit 100.
                assert cat_index < 100
                cat_name = '{}{:02d}.cat'.format(prefix, cat_index)
                cat_path = self.location / cat_name
                # Stop if the cat file is not found.
                if not cat_path.exists():
                    break
                # Record it.
                cat_dir_list_low_to_high.append(cat_path)
                # Increment for the next cat.
                cat_index += 1
                               
        # Fill in dict entries with the cat paths, in reverse order.
        for path in reversed(cat_dir_list_low_to_high):
            # Start with None; these get opened as needed.
            self.catalog_file_dict[path] = None
        return


    def Add_Catalog(self, path):
        '''
        Adds a catalog entry for the cat file on the given path.
        The new catalog is given low priority.
        '''
        assert path.exists()
        # Easy to give low priority by sticking at the end.
        # Don't worry about a high priority option unless it ever
        # is needed.
        self.catalog_file_dict[path] = None
        return


    def Get_All_Loose_Files(self):
        '''
        Returns a dict of absolute paths to all loose files at this location,
        keyed by virtual path, skipping those at the top directory level
        (eg. other cat files, the content file, etc.).
        Files in subfolders not used by x4 are ignored.
        '''
        source_file_path_dict = {}

        # Dynamically find all files in the source folder.
        # The glob pattern means: 
        #  '**' (recursive search) 
        #  '/*' (one folder down) 
        #  '/*' (anything in that folder, including subfolders)
        for file_path in self.location.glob('**/*/*'):
            # Skip folders.
            if not file_path.is_file():
                continue

            # Isolate the relative part of the path.
            # This will be the same as a virtual path.
            # Convert from Path to a posix style string (forward slashes).
            virtual_path = file_path.relative_to(self.location).as_posix()

            # Skip if this doesn't start in an x4 subfolder.
            if not any(virtual_path.startswith(x) 
                       for x in valid_virtual_path_prefixes):
                continue

            # Can now record it.
            source_file_path_dict[virtual_path] = file_path

        return source_file_path_dict


    def Get_Catalog_Reader(self, cat_path):
        '''
        Returns the Cat_Reader object for the given cat_path,
        creating it if necessary.
        '''
        if self.catalog_file_dict[cat_path] == None:
            self.catalog_file_dict[cat_path] = Cat_Reader(cat_path)
        return self.catalog_file_dict[cat_path]


    def Get_All_Catalog_Readers(self):
        '''
        Returns a list of all Cat_Reader objects, opening them
        as necessary.
        '''
        # Loop over the cat_path names and return readers.
        return [self.Get_Catalog_Reader(cat_path) 
                for cat_path in self.catalog_file_dict]


    def Get_Cat_Entries(self):
        '''
        Returns a dict of Cat_Entry objects, keyed by virtual_path,
        taken from all catalog readers, using the highest priority one when
        a file is repeated.
        '''
        path_entry_dict = {}
        # Loop over the cats in priority order.
        for cat_path in self.catalog_file_dict:
            cat_reader = self.Get_Catalog_Reader(cat_path)

            # Get all the entries for this cat.
            for virtual_path, cat_entry in cat_reader.Get_Cat_Entries().items():

                # If the path wasn't seen before, record it.
                # If it was seen, then the prior one has higher priority.
                if not virtual_path in path_entry_dict:
                    path_entry_dict[virtual_path] = cat_entry
        return path_entry_dict


    def Read_Loose_File(self, virtual_path):
        '''
        Returns a tuple of (file_path, file_binary) for a loose file
        matching the given virtual_path.
        If no file found, returns (attempted_file_path, None).
        '''
        file_binary = None
        file_path = self.location / virtual_path
        if file_path.exists():
            # Load from the selected file.
            with open(file_path, 'rb') as file:
                file_binary = file.read()
        return (file_path, file_binary)


    def Read_Catalog_File(self, virtual_path):
        '''
        Returns a tuple of (cat_path, file_binary) for a cat/dat entry
        matching the given virtual_path.
        If no file found, returns (attempted_cat_path, None).
        '''
        cat_path = None
        file_binary = None
        # Loop over the cats in priority order.
        for cat_path in self.catalog_file_dict:
            # Get the reader.
            cat_reader = self.Get_Catalog_Reader(cat_path)
            # Check the cat for the file.
            file_binary = cat_reader.Read(virtual_path)
            # Stop looping over cats once a match found.
            if file_binary != None:
                break
        return (cat_path, file_binary)


    def Read(self, 
             virtual_path,
             error_if_not_found = False,
             ):
        '''
        Returns a Game_File intialized with the contents read from
        a loose file or unpacked from a cat file.
        If the file contents are empty, this returns None.
         
        * virtual_path
          - String, virtual path of the file to look up.
          - For files which may be gzipped into a pck file, give the
            expected non-zipped extension (.xml, .txt, etc.).
        * error_if_not_found
          - Bool, if True an exception will be thrown if the file cannot
            be found, otherwise None is returned.
        '''
        # Can pick from either loose files or cat/dat files.
        # Preference is taken from Settings.
        if Settings.prefer_single_files:
            method_order = [self.Read_Loose_File, self.Read_Catalog_File]
        else:
            method_order = [self.Read_Catalog_File, self.Read_Loose_File]

        # Call the search methods in order, looking for the first to
        #  fill in file_binary. This will also record where the data
        #  was read from, for debug printout and identifying patches
        #  vs overwrites (by cat name).
        source_path = None
        file_binary = None
        for method in method_order:
            source_path, file_binary = method(virtual_path)
            if file_binary != None:
                break
            
        # If no binary was found, error.
        if file_binary == None:
            if error_if_not_found:
                raise File_Missing_Exception(
                    'Could not find a match for file {}'.format(virtual_path))
            return None
        
        # Construct the game file.
        game_file = File_Types.New_Game_File(
            binary = file_binary,
            virtual_path = virtual_path,
            file_source_path = source_path,
            from_source = True,
            extension_name = self.extension_name,
            )
        
        # Debug print the read location.
        if Settings.log_source_paths:
            Plugin_Log.Print('Loaded file {} from {}'.format(
                virtual_path, source_path))
        
        return game_file

    
# Small support namedtuple for extension details.
_Extension_Summary = namedtuple(
    '_Extension_Summary', 
    ['name', 'path', 'dependencies'])


class Source_Reader_class:
    '''
    Class used to find and read the highest priority source files,
    and handle merging of extension xml with base xml.
    Create this only after Settings have been filled in.

    Attributes:
    * base_x4_source_reader
      - Location_Source_Reader for the base X4 folder.
    * loose_source_reader
      - Location_Source_Reader for the optional user source folder.
      - Takes priority over the base X4 folder.
    * extension_source_readers
      - List of Location_Source_Reader objects pointing at enabled
        extensions.
      - Earlier extensions in the list satisfy dependencies from later
        extensions in the list, so xml patching should be done from
        first entry to last entry.
    '''
    def __init__(self):
        self.base_x4_source_reader    = None
        self.loose_source_reader      = None
        self.extension_source_readers = []
        return


    # TODO: maybe merge this in with __init__, changing when the first
    # reader is created (eg. after Settings are set up).
    def Init_From_Settings(self):
        '''
        Initializes the source reader by creating Location_Source_Reader
        children for all locations being sourced from.
        This should be run after paths have been set up in Settings.
        '''
        # Set up the base X4 folder.
        self.base_x4_source_reader = Location_Source_Reader(
            location = Settings.Get_X4_Folder())

        # Check if a loose source folder was requested.
        source_folder = Settings.Get_Source_Folder()
        if source_folder != None:
            self.loose_source_reader = Location_Source_Reader(
                location = source_folder)


        # Extension lookup will be somewhat more complicated.
        # Need to figure out which extensions the user has enabled.
        # The user content.xml, if it exists (which it may not), will
        #  hold details on custom extension enable/disable settings.
        # Note: by observation, the content.xml appears to not be a complete
        #  list, and may only record cases where the enable/disable selection
        #  differs from the extension default.
        user_extensions_enabled  = {}
        content_xml_path = Settings.Get_User_Content_XML_Path()
        if content_xml_path.exists():
            # (lxml parser needs a string path.)
            content_root = ET.parse(str(content_xml_path)).getroot()
            for extension_node in content_root.findall('extension'):
                name = extension_node.get('id')
                if extension_node.get('enabled') == 'true':
                    user_extensions_enabled[name] = True
                else:
                    user_extensions_enabled[name] = False
                

        # Find where these extensions are located, and record details.
        # Use a list of _Extension_Details objects for detail tracking.
        ext_summary_dict = OrderedDict()

        # Could be in documents or x4 directory.
        for base_path in [Settings.Get_X4_Folder(), Settings.Get_User_Folder()]:
            extensions_path = base_path / 'extensions'

            # Skip if there is no extensions folder.
            if not extensions_path.exists():
                continue

            # Skip if ignoring extensions.
            # (Can also take care of this elsewhere, but this spot is easy.)
            if Settings.ignore_extensions:
                continue

            # Note the path to the target output extension content.xml,
            #  so it can be skipped.
            output_content_path = Settings.Get_Output_Folder() / 'content.xml'

            # Use glob to pick out all of the extension content.xml files.
            for content_xml_path in extensions_path.glob('*/content.xml'):

                # Skip the current output extension target, since its contents
                #  are the ones being updated this run.
                if content_xml_path == output_content_path:
                    continue

                # Load it and pick out the id.
                content_root = ET.parse(str(content_xml_path)).getroot()
                name = content_root.get('id')
                
                # Determine if this is enabled or disabled.
                # If it is in user content.xml, use that flag, else use the
                #  flag in the extension.
                # Skip if this extension is in content.xml and disabled.
                if name in user_extensions_enabled:
                    enabled = user_extensions_enabled[name]
                else:
                    enabled = content_root.get('enabled', 'true') == 'true'
                if not enabled:
                    continue

                # Collect all the names of dependencies.
                # Don't worry if dependencies are optional or not; that would
                #  only matter if wanting to police missing dependencies.
                dependencies = [x.get('id') 
                                for x in content_root.findall('dependency')]

                # Record the details.
                ext_summary_dict[name] = _Extension_Summary(
                    name, content_xml_path.parent, dependencies)

        # TODO: maybe sort the ext_summary_dict so that extensions are
        # always loaded in the same order, which might be a better match
        # to X4 loading.

        # Need to sort the extensions according to dependencies.
        # A brute force appoach will be used, scheduling extensions
        #  that have dependencies filled first, iterating until done.
        # Each loop will move some number of summaries from ext_summary_dict
        #  to sorted_ext_summary_dict.
        sorted_ext_summary_dict = OrderedDict()

        # To satisfy optional dependencies, start by filling in dummy
        #  entries for all missing extensions.
        # This loop will modify the dict, so loop over a copy of its entries.
        for ext_summary in list(ext_summary_dict.values()):
            for dependency in ext_summary.dependencies:

                # If the dependency is missing, fill it in.
                if dependency not in ext_summary_dict:

                    # These go in the sorted list, to satisfy checks.
                    sorted_ext_summary_dict[dependency] = None

                    # Report a warning as well.
                    Plugin_Log.Print(
                        'Warning: extension "{}" dependency "{}" not found'.format(
                        ext_summary.name, dependency))
                

        # Start the sorting process. Add a safety limit.
        limit = 10000
        while ext_summary_dict:
            limit -= 1
            if limit <= 0:
                raise Exception('Something went wrong with extension sorting.')

            # Loop over a copy of the ext_summary_dict again, since it
            # will get entries removed.
            for ext_summary in list(ext_summary_dict.values()):

                # Check if all dependencies are satisfied.
                # (Note: all() will be True if it ends up checking nothing
                # due to no dependencies.)
                if all(x in sorted_ext_summary_dict 
                       for x in ext_summary.dependencies):

                    # Move the extension between dicts.
                    sorted_ext_summary_dict[ext_summary.name] = ext_summary
                    ext_summary_dict.pop(ext_summary.name)


        # With extensions now sorted, set up the readers.
        for ext_name, ext_summary in sorted_ext_summary_dict.items():
            # Skip dependency dummies.
            if ext_summary == None:
                continue
            self.extension_source_readers.append( Location_Source_Reader(
                location = ext_summary.path,
                extension_name = ext_name ))
            
        return


    def Get_All_Virtual_Paths(self, pattern = None):
        '''
        Return a set of virtual_path names of all discovered files,
        optionally filtered by a wildcard pattern.

        * pattern
          - String, optional, wildcard pattern to use for matching names.
        '''
        virtual_paths_set = set()

        # Loop over readers.
        for source_location_reader in ([
                self.base_x4_source_reader, 
                self.loose_source_reader] 
                + self.extension_source_readers
            ):
            # Skip if no reader, eg. when the loose source folder
            # wasn't given.
            if source_location_reader == None:
                continue

            # Pick out the cat and loose file virtual_paths.
            for virtual_path in chain(source_location_reader.Get_All_Loose_Files(),
                                      source_location_reader.Get_Cat_Entries()):
                # If a pattern given, filter based on it.
                if pattern != None and not fnmatch(virtual_path, pattern):
                    continue
                virtual_paths_set.add(virtual_path)

        return virtual_paths_set
    

    def Read(self, 
             virtual_path,
             error_if_not_found = True
             ):
        '''
        Returns a Game_File intialized with the contents read from
        a loose file or unpacked from a cat file.
        Extension xml files will be automatically merged with any
        base files.
        If the file contents are empty, this returns None.
         
        * virtual_path
          - String, virtual path of the file to look up.
          - For files which may be gzipped into a pck file, give the
            expected non-zipped extension (.xml, .txt, etc.).
        * error_if_not_found
          - Bool, if True an exception will be thrown if the file cannot
            be found, otherwise None is returned.
        '''
        # Non-xml files will just use the latest extension's
        # version. TODO: check if this is consistent with x4 behavior.
        # Xml files will handle the more complicated merging.
        # Since behavior diverges pretty heavily, fork the code here.
        file_extension = virtual_path.rsplit('.',1)[1]

        if file_extension != 'xml':
            game_file = None
            # Look for it in extensions in reverse order, since the
            # latest ones are the last to load.
            for extension_source_reader in reversed(self.extension_source_readers):
                game_file = extension_source_reader.Read(virtual_path)
                if game_file != None:
                    break
            # Now check the loose source folder.
            if game_file == None:
                game_file = self.loose_source_reader.Read(virtual_path)
            # Finally, the base x4 folder.
            if game_file == None:
                game_file = self.base_x4_source_reader.Read(virtual_path)


        else:
            # Get a list of all extension versions of the file.
            extension_game_files = []
            for extension_source_reader in self.extension_source_readers:
                extension_game_file = extension_source_reader.Read(virtual_path)
                if extension_game_file != None:
                    extension_game_files.append(extension_game_file)


            # Get a base file from either the loose source folder or the
            # x4 folder. Note: it may not be found if the file was added
            # purely by an extension (which could come up for custom
            # transforms aimed at a particular mod, or generic transforms
            # that loop over files of a given name pattern).
            game_file = None
            if self.loose_source_reader != None:
                game_file = self.loose_source_reader.Read(virtual_path)
            if game_file == None:
                game_file = self.base_x4_source_reader.Read(virtual_path)
            
            # If no base game_file was found, try to treat the first extension
            # file as the base file.
            if game_file == None and extension_game_files:
                game_file = extension_game_files.pop(0)

                # This could go awry if the first extension file is a diff
                #  patch, which has nothing to patch.
                if base_game_file.Get_Tree().tag == 'diff':
                    raise Exception(('No base file found for {}, and the'
                        ' first extension file is a diff patch').format(
                            virtual_path))

            # Merge all other extension xml into the base_file, or
            # possibly overwrite the base_file.
            if game_file:
                for extension_game_file in extension_game_files:

                    if extension_game_file.Is_Patch():
                        # Add a nice printout.
                        Plugin_Log.Print(
                            'XML patching {}: to {}, from {}'.format(
                                virtual_path,
                                game_file.file_source_path,
                                extension_game_file.file_source_path))
                        # Call the patcher.
                        game_file.Patch(extension_game_file)
                    else:
                        # Non-patch, so overwrite.
                        game_file = extension_game_file
            

        # If the file wasn't found anywhere, raise any error needed.
        if game_file == None:
            if error_if_not_found:
                raise File_Missing_Exception(
                    'Could not find a match for file {}'.format(virtual_path))
            return None

        return game_file


    def Get_All_Loose_Source_Files(self):
        '''
        Returns a dict of absolute paths to all loose files in the loose
        source folder, keyed by virtual path.
        '''
        if self.loose_source_reader == None:
            return {}
        return self.loose_source_reader.Get_All_Loose_Files()

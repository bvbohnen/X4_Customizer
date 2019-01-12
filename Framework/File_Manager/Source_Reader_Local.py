
from pathlib import Path
from collections import OrderedDict, defaultdict
from itertools import chain

from . import File_Types
from .Cat_Reader import Cat_Reader
from .. import Common
from ..Common import Settings
from ..Common import File_Missing_Exception
from ..Common import Plugin_Log, Print


# Set a list of subfolders that are standard for x4 files.
# Other folders can generally be ignored.
# TODO: maybe expand on this and look at everything.
valid_virtual_path_prefixes =  (
        'aiscripts/','assets/',
        'cutscenes/','extensions/'
        'index/',
        'libraries/','maps/',
        'md/','music/',
        'particles/','sfx/',
        'shadergl/','t/',
        'textures/',
        'ui/','voice-L044/',
        'voice-L049/','vulkan/',
        )    

class Location_Source_Reader:
    '''
    Class used to look up source files from a single location, such as the
    base X4 folder, the loose source folder, or an extension folder.
    Note: all virtual_paths stored here are relative to the location
    being read, and may not match up with the full game virtual paths
    after extension prefixing.
    
    Attributes:
    * location
      - Path to the location being sourced from.
      - If not given, auto detection of cat files will be skipped.
    * folder_name_lower
      - Name of the final folder of the location, lower cased.
      - To be used in ordering extensions.
    * extension_name
      - String, name of the extension, if an extension, else None.
      - Taken from the original content.xml format.
    * extension_path_name
      - As above, but lower cased.
      - This should be used for matching virtual_paths or dependencies.
    * soft_dependencies
      - List of strings, path_names of other extensions this one should
        load after; other extension might not exist.
    * hard_dependencies
      - List of strings, path_names of other extensions this one should
        load after; other extension should exist.
    * catalog_file_dict
      - OrderedDict of Cat_Reader objects, keyed by virtual_path relative
        to the location, ordered by priority, where the first entry is 
        the highest priority cat.
      - Inner dict entries are initially None, and get replaced with
        Catalog_Files as the cats are searched.
      - This collects all catalogs together, of any prefix.
    * source_file_path_dict
      - Dict, keyed by virtual_path, holding the system path
        for where the file is located, for loose files at the location
        folder.
      - The key will always be lowercased, though the path may not be.
    '''
    def __init__(
            self, 
            location = None, 
            extension_name = None,
            soft_dependencies = None,
            hard_dependencies = None,
        ):
        self.location = location
        self.folder_name_lower = None
        if location:
            # Use the .stem property for the containing folder.
            self.folder_name_lower = location.stem.lower()
        self.catalog_file_dict = OrderedDict()

        self.extension_name = extension_name
        # Grab a lower cased extension name, if a name was given.
        self.extension_path_name = None
        if extension_name:
            self.extension_path_name = extension_name.lower()

        self.soft_dependencies = soft_dependencies
        self.hard_dependencies = hard_dependencies
        self.source_file_path_dict = None

        # Search for cats and loose files if location given.
        if location != None:
            self.Find_Catalogs(location)
            self.Find_Loose_Files(location)
        return
    

    def Find_Catalogs(self, location):
        '''
        Find and record all catalog files at the given location,
        according to the X4 naming convention.
        '''
        # Search for cat files the game will recognize.
        '''
        These start at 01.cat, and count up as 2-digit values until
        the count is broken.

        Extensions observed to use prefixes 'ext_' and 'subst_' on
        their cat/dat files.
        
        Some details:
        -  'subst_' get loaded first, and overwrite lower game files
            instead of patching them (eg. 'substitute').
        -  'ext_' get loaded next, and are treated as patches.
            (This was verified in an accidental test, where a subst file
            that changed nodes caused an ext file in the same extension
            to fail its diff patching.)

        Since the base folder names (01.cat etc) are never expected
        to be mixed with extension names (ext_01.cat etc), and to
        simplify Location_Source_Reader setup so that it doesn't
        need to be told if it is pointed at an extension, all
        prefixes could be searched here.
        '''
        
        # For convenience, the first pass will fill in a list with low
        #  to high priority, then the list can be reversed at the end.
        cat_dir_list_low_to_high = []

        # Put the prefixes in reverse priority, so subst will get
        # found first in general searches.
        if self.extension_name:
            prefixes = ['ext_','subst_']
        else:
            prefixes = ['']

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
                ## Temp warning.
                #if prefix == 'subst_':
                #    Print('Warning: subst_ catalogs not fully supported yet')
                               
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


    def Find_Loose_Files(self, location):
        '''
        Finds all loose files at the location folder, recording
        them into self.source_file_path_dict.
        '''
        self.source_file_path_dict = {}

        # Dynamically find all files in the source folder.
        # The glob pattern means: 
        #  '**' (recursive search)
        #  '/*' (anything in that folder, including subfolders)
        # Note: to limit overhead from looking at invalid paths, the
        # outer loop would ideally be limited to the valid path prefixes,
        # though glob is case sensitive so this might not work great.
        # TODO: revisit this.
        for path_prefix in valid_virtual_path_prefixes:
            for file_path in self.location.glob(path_prefix+'**/*'):
                # Skip folders.
                if not file_path.is_file():
                    continue
                # Skip sig files; don't care about those.
                if file_path.suffix == '.sig':
                    continue

                # Isolate the relative part of the path.
                # This will be the same as a virtual path once lowercased.
                # Convert from Path to a posix style string (forward slashes).
                virtual_path = file_path.relative_to(self.location).as_posix().lower()

                # Skip if this doesn't start in an x4 subfolder.
                if not any(virtual_path.startswith(x) 
                           for x in valid_virtual_path_prefixes):
                    continue

                # Can now record it, with lower case virtual_path.
                self.source_file_path_dict[virtual_path.lower()] = file_path
        return


    def Get_All_Loose_Files(self):
        '''
        Returns a dict of absolute paths to all loose files at this location,
        keyed by virtual path, skipping those at the top directory level
        (eg. other cat files, the content file, etc.).
        Files in subfolders not used by x4 are ignored.
        '''
        if self.source_file_path_dict == None:
            self.Find_Loose_Files()
        return self.source_file_path_dict
    

    def Get_Catalog_Reader(self, cat_path):
        '''
        Returns the Cat_Reader object for the given cat_path,
        creating it if necessary.
        '''
        if self.catalog_file_dict[cat_path] == None:
            self.catalog_file_dict[cat_path] = Cat_Reader(cat_path)
        return self.catalog_file_dict[cat_path]


    #def Get_All_Catalog_Readers(self):
    #    '''
    #    Returns a list of all Cat_Reader objects, opening them
    #    as necessary.
    #    '''
    #    # Loop over the cat_path names and return readers.
    #    return [self.Get_Catalog_Reader(cat_path) 
    #            for cat_path in self.catalog_file_dict]


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


    def Get_Virtual_Paths(self):
        '''
        Returns a set of all virtual paths used at this location
        by catalogs or loose files, relative to the location.
        These may need prefixing for extension files that
        are not present at the base x4 location.
        '''
        # Note: for large number of files, using a list for this
        # gives really bad performance; switch to a set().
        # TODO: consider finding a way to make this a generator,
        # though that may be impractical when needing to avoid
        # repeating names.
        virtual_paths = set()
        # Use the keys returned by Get_All_Loose_Files and Get_Cat_Entries.
        for virtual_path in chain(  self.Get_All_Loose_Files().keys(),
                                    self.Get_Cat_Entries().keys() ):
            # Include each path once, if repeated.
            virtual_paths.add(virtual_path)
        return virtual_paths


    def Read_Loose_File(self, virtual_path, **kwargs):
        '''
        Returns a tuple of (file_path, file_binary) for a loose file
        matching the given virtual_path.
        If no file found, returns (None, None).
        Note: pathing is case sensitive.
        '''
        if virtual_path not in self.source_file_path_dict:
            return (None, None)

        # Load from the selected file.
        file_path = self.source_file_path_dict[virtual_path]
        with open(file_path, 'rb') as file:
            file_binary = file.read()
        return (file_path, file_binary)


    def Read_Catalog_File(self, virtual_path, 
                          cat_prefix = None, allow_md5_error = False):
        '''
        Returns a tuple of (cat_path, file_binary) for a cat/dat entry
        matching the given virtual_path.
        If no file found, returns (attempted_cat_path, None).

        * cat_prefix
          - Optional string, prefix of catalog files to search.
        * allow_md5_error
          - Bool, if True then the md5 check will be suppressed.
        '''
        cat_path = None
        file_binary = None

        # Loop over the cats in priority order.
        for cat_path in self.catalog_file_dict:

            # If a prefix was given, skip if this cat doesn't have
            # a matched prefix.
            if cat_prefix and not cat_path.name.startswith(cat_prefix):
                continue

            # Get the reader.
            cat_reader = self.Get_Catalog_Reader(cat_path)

            # Check the cat for the file.
            file_binary = cat_reader.Read(virtual_path, 
                                          allow_md5_error = allow_md5_error)

            # Stop looping over cats once a match found.
            if file_binary != None:
                break

        return (cat_path, file_binary)
    

    def Read(self, 
             virtual_path,
             include_loose_files = True,
             cat_prefix = None,
             error_if_not_found = False,
             allow_md5_error = False,
             ):
        '''
        Returns a Game_File intialized with the contents read from
        a loose file or unpacked from a cat file.
        If the file contents are empty, this returns None.
         
        * virtual_path
          - String, virtual path of the file to look up.
          - For files which may be gzipped into a pck file, give the
            expected non-zipped extension (.xml, .txt, etc.).
        * include_loose_files
          - Bool, if True then loose files are searched.
        * cat_prefix
          - Optional string, prefix of catalog files to search.
          - Eg. 'subst' to look only at 'subst_#.cat' files.
        * error_if_not_found
          - Bool, if True an exception will be thrown if the file cannot
            be found, otherwise None is returned.
        * allow_md5_error
          - Bool, if True then the md5 check will be suppressed and
            errors allowed. May still print a warning message.
        '''
        # Can pick from either loose files or cat/dat files.
        # Preference is taken from Settings.
        if Settings.prefer_single_files:
            method_order = [self.Read_Loose_File, self.Read_Catalog_File]
        else:
            method_order = [self.Read_Catalog_File, self.Read_Loose_File]

        # Maybe skip loose file checks.
        if not include_loose_files:
            method_order.remove(self.Read_Loose_File)


        # Call the search methods in order, looking for the first to
        #  fill in file_binary. This will also record where the data
        #  was read from, for debug printout and identifying patches
        #  vs overwrites (by cat name).
        source_path = None
        file_binary = None
        for method in method_order:
            # Call the function. Pass some args.
            source_path, file_binary = method(
                virtual_path, 
                cat_prefix = cat_prefix,
                allow_md5_error = allow_md5_error,
                )
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

    

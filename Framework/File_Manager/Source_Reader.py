'''
Support for reading source files, including unpacking from cat/dat files.
Includes File_Missing_Exception for when a file is not found.
'''
'''
X4 virtual path determination:

    - Any file in the base x4 catalogs will have a virtual path
      relative to the root x4 folder.
      Eg. '/libraries/parameters.xml'

    - Extension files that have a path relative to the extension folder
      which matches the path of a base file relative to the x4 folder
      will use the x4 folder based path.
      Eg. '/extensions/extA/libraries/wares.xml' will use the path
          'libraries/wares.xml'

    - Extensions files that do not match to a base file will instead
      use a path relative to the x4 base folder.
      Note: this is based on extension folder name, not extension id.
      Eg. '/extensions/extA/libraries/newfile.xml' will use the path
          '/extensions/extA/libraries/newfile.xml'

    - Extensions which target other extensions' new files will have
      a path relative to the extension folder that matches a path
      relative to the base x4 folder, extended out to the other extension.
      Eg. 'extensions/extA/extensions/extB/somefile' will use the path
          'extensions/extB/somefile'.
      This comes up when extensions edit files from other extensions.
      It also comes up when there is no dependency in place, so extA
      can patch extB files without a dependency on extB.


Loading order:

    After various testing, the x4 file loading order appears to be:
        
        a) Search for the base file version (not a patch).
            - This will establish the actual virtual_path of the file.
            - Paths not starting with 'extensions/' will look in the
              base x4 directory and the 'subst_#.cat' files of the
              extensions.
            - Paths starting with 'extensions/' will look only at the
              particular named extension, and will search inside it
              using a truncated path.

        b) Search for patches.
            - All extensions are searched, not the base game folders.
            - If the path starts with 'extensions', the particular
              named extension can be skipped (cannot patch its own file).
            - Path is left unmodified.
            - These can be found in 'ext_#.cat' or as loose files.
            - Does not include 'subst_#.cat' files; those were handled
              during base file loading.

    Priorities for loading will be determined separately per step.

    Eg. is extA has a dependency on extB and introduces file newfile.xml,
    and extB has a patch for newfile.xml, then the newfile.xml will load
    from exta (as part of step (a)), and then get patched by extB, even
    though that seems to be opposite the dependency order.

    For extensions that have no dependencies to order them, they will
    be handled in lowercase alphabetical folder order.


Note on case:
    To simplify path handling, all paths will be lower cased.
    A side effect is that extension names need to be stored in lower
    case, since they can show up in virtual paths.

    This appears to sync up with the game internals, particularly in
    regard to linux support (which requires extensions use lower case
    in general for paths). This can also be observed in the log,
    where listed extension names are sometimes printed in lower case
    (eg. signature checks are lower case, and though extension diff messages
    are original case, extensions are ordered alphabetically based
    on lower case).

'''
from lxml import etree as ET
from collections import OrderedDict
from fnmatch import fnmatch

from . import File_Types
from .. import Common
from ..Common import Settings
from ..Common import File_Missing_Exception
from ..Common import Plugin_Log, Print
from .Source_Reader_Local import Location_Source_Reader
from .Extension_Finder import Find_Extensions

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
      - OrderedDict of Location_Source_Reader objects pointing at enabled
        extensions, keyed by lowercase extension name.
      - Earlier extensions in the list satisfy dependencies from later
        extensions in the list, so xml patching should be done from
        first entry to last entry.
    * ext_currently_patching
      - String, during xml patch application this is the name of the
        extension sourcing the patch.
      - For use by monitoring code.
    '''
    def __init__(self):
        self.base_x4_source_reader    = None
        self.loose_source_reader      = None
        self.extension_source_readers = OrderedDict()
        self.ext_currently_patching = None
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


        # Skip if ignoring extensions.
        # (Can also take care of this elsewhere, but this spot is easy.)
        if not Settings.ignore_extensions:
            # Loop over Extension_Summary objects.
            for ext_summary in Find_Extensions():            

                # Skip those disabled.
                if not ext_summary.enabled:
                    continue

                # Skip the current output extension target, since its contents
                #  are the ones being updated this run.
                # Sometimes this will be included based on settings, eg. when
                #  only creating documentation.
                if (ext_summary.is_current_output 
                and Settings.ignore_output_extension):
                    continue

                # Create the reader object.
                # Don't worry about ordering just yet.
                reader = Location_Source_Reader(
                    location          = ext_summary.content_xml_path.parent,
                    # TODO: maybe track the display name of the extension.
                    extension_name    = ext_summary.ext_id,
                    soft_dependencies = ext_summary.soft_dependencies,
                    hard_dependencies = ext_summary.hard_dependencies,
                    )
                # Record using the path name (lowercase).
                self.extension_source_readers[reader.extension_path_name] = reader
                
        # Now sort the extension order to satisfy dependencies.
        self.Sort_Extensions()
        
        return


    def Sort_Extensions(self, priorities = None):
        '''
        Sort the found extensions so that all dependencies are satisfied.
        Optionally, allow setting of sorting priority.
        When dependencies are otherwise satisfied, extensions are
        sorted by alphabetical lowercase folder name.

        * priorities
          - Dict, keyed by extension name, holding an integer priority.
          - Default priority is 0.
          - Negative priority loads an extension earlier, positive later.
        '''
        # Get a starting dict, keyed by extension path name.
        unsorted_dict = {ext.extension_path_name : ext 
                        for ext in self.extension_source_readers.values()}

        # Fill out the priorities with defaults.
        if not priorities:
            priorities = {}
        for name in unsorted_dict:
            if name not in priorities:
                priorities[name] = 0

        # Need to sort the extensions according to dependencies.
        # A brute force appoach will be used, scheduling extensions
        #  that have dependencies filled first, iterating until done.
        # Each loop will move some number of summaries from unsorted_dict
        #  to sorted_dict.
        sorted_dict = OrderedDict()

        # Do a hard dependency error check.
        for name, source_reader in unsorted_dict.items():
            for hard_dep_name in source_reader.hard_dependencies:
                if hard_dep_name not in unsorted_dict:
                    # Print as an Error but continue processing.
                    Plugin_Log.Print(('Error: extension "{}" has a missing'
                        ' hard dependency on "{}"').format(name, hard_dep_name))
                    
        # To satisfy optional dependencies, start by filling in dummy
        #  entries for all missing extensions.
        for name, source_reader in unsorted_dict.items():
            for dep_name in ( source_reader.hard_dependencies 
                            + source_reader.soft_dependencies):
                if dep_name not in unsorted_dict:
                    sorted_dict[dep_name] = None
                

        # Start the sorting process, with a safety limit.
        limit = 10000
        while unsorted_dict:
            limit -= 1
            if limit <= 0:
                raise AssertionError('Something went wrong with extension sorting.')

            # Gather which extensions can be sorted into the next slot.
            # Start with all that have hard and soft dependencies filled.
            valid_next_exts = [
                ext for ext in unsorted_dict.values()
                if all(dep in sorted_dict for dep in (
                    ext.hard_dependencies + ext.soft_dependencies))]

            # If none were found, try just those with hard dependencies filled.
            # TODO: This may be more lax than X4 about soft dependencies;
            #  maybe look into it.
            if not valid_next_exts:
                valid_next_exts = [
                    ext for ext in unsorted_dict.values()
                    if all(dep in sorted_dict for dep in ext.soft_dependencies)]

            # Now sort them in priority order, with secondary on lowercase
            # folder name order.
            valid_next_exts = sorted(
                valid_next_exts,
                # Priority goes first (low to high), then name (A to Z).
                key = lambda ext: (priorities[ext.extension_path_name], 
                                   ext.folder_name_lower))

            # Pick the first one and schedule it.
            pick = valid_next_exts[0]
            sorted_dict[pick.extension_path_name] = pick
            unsorted_dict.pop(pick.extension_path_name)


        # Prune out dummy entries.
        for name in list(sorted_dict.keys()):
            if sorted_dict[name] == None:
                sorted_dict.pop(name)

        # Store the sorted list.
        self.extension_source_readers = sorted_dict
        return


    def Get_Extension_Names(self):
        '''
        Returns a list of names of all enabled extensions.
        '''
        return [x.extension_name for x in self.extension_source_readers.values()]
    

    def Gen_Extension_Virtual_Paths(self, ext_name):
        '''
        Returns the virtual paths for the given extension.
        Paths will be prefixed with 'extension/name/' for files that
        do not match any at the base x4 location.
        If the name doesn't match a known extension, this returns 
        an empty list.
        '''
        if ext_name not in self.extension_source_readers:
            return []

        # Get the base x4 paths, to check against.
        base_paths = self.base_x4_source_reader.Get_Virtual_Paths()

        # Go through the paths returned by the extension reader.
        for ext_path in self.extension_source_readers[ext_name].Get_Virtual_Paths():
            # If this matches a base_path, return it as-is.
            if ext_path in base_paths:
                yield ext_path
            # Otherwise, prefix it.
            else:
                yield 'extensions/{}/{}'.format(ext_name, ext_path)
        return


    def Gen_All_Virtual_Paths(self, pattern = None):
        '''
        Generator which yields all virtual_path names of all discovered files,
        optionally filtered by a wildcard pattern.

        * pattern
          - String, optional, wildcard pattern to use for matching names.
        '''
        # Results will be cached for quick lookups.
        # TODO: maybe move this into a normal attribute for use by
        # other methods.
        if not hasattr(self, '_virtual_paths_set'):
            self._virtual_paths_set = set()
            
            # Loop over readers.
            # Note: multiple readers may produce the same file, in which
            # case the name should only be returned once.
            for reader in [ self.base_x4_source_reader, 
                            self.loose_source_reader]:
                # Skip if no reader, eg. when the loose source folder
                # wasn't given.
                if reader == None:
                    continue
                # Pick out the cat and loose file virtual_paths.
                for virtual_path in reader.Get_Virtual_Paths():
                    self._virtual_paths_set.add(virtual_path)

            # Work through extensions.
            for ext_reader in self.extension_source_readers.values():
                # Work through the paths with prefixing as needed.
                for path in self.Gen_Extension_Virtual_Paths(ext_reader.extension_path_name):
                    self._virtual_paths_set.add(virtual_path)

        # With the set filled in, can do a pass to yield each path.
        for virtual_path in self._virtual_paths_set:
            # If a pattern given, filter based on it.
            if pattern != None and not fnmatch(virtual_path, pattern):
                continue
            yield virtual_path
        return
    

    def Read(
            self, 
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
        # Always work with lowercase virtual paths.
        # (Note: this may have been done already in the File_System, but
        # do it here as well to support direct source_reader reads
        # for now, in case any plugins use that.)
        virtual_path = virtual_path.lower()
        

        # Step 1: get the base version of the file.
        # If the virtual_path begins with "extentions", read from the
        # selected extension if present, else from the base x4 folder
        # or source folder.
        game_file = None
        if virtual_path.startswith('extensions/'):
            # Can split on all '/' and take the second term for the
            # extension name, 3rd term for virtual path within that
            # extension.
            _, ext_name, ext_path = virtual_path.split('/',2)

            # Check if this ext is found.
            if ext_name in self.extension_source_readers:
                # Get it from this extension, using the extension
                # specific path.
                # TODO: consider instead giving the whole virtual_path
                # and a base_file flag to let the location source reader
                # deal with picking the path apart locally.
                game_file = self.extension_source_readers[ext_name].Read(ext_path)

        else:
            # Read from the source and base x4 locations.
            if self.loose_source_reader != None:
                game_file = self.loose_source_reader.Read(virtual_path)
            if game_file == None:
                game_file = self.base_x4_source_reader.Read(virtual_path)


        # Deal with cases where the file is not found.
        if game_file == None:
            if error_if_not_found:
                raise File_Missing_Exception(
                    'Could not find a match for file {}'.format(virtual_path))
            return None
        

        # This could go awry if the first extension file is a diff
        #  patch, which has nothing to patch.
        # This case can also come up if a substitution is done with
        #  a diff patch, but that will be caught in the merge function.
        # However, don't hard error; want to print the message
        #  and keep going with best effort, similar to x4 (though there
        #  they give no warning).
        if (isinstance(game_file, File_Types.XML_File)
        and game_file.Get_Root_Readonly().tag == 'diff'):
            Plugin_Log.Print(('Error: File found is a diff patch with nothing'
                              ' to patch, on path "{}".').format(virtual_path))
            return None


        # Step 2: collect any patches/substitutions.
        # These can come from any extension, except the one the file
        #  was sourced from (if it came from an ext).
        # Note: substitions should be evaluated separately from
        #  patches; an extension can apply both, and substitutions
        #  from all extensions should preceed patches from all.
        for mode in ['substitution','patch']:

            for ext_reader in self.extension_source_readers.values():

                # Skip if this ext is the original source.
                # This should be harmless to allow, but saves a little time.
                # (A path of 'extensions/name/...' is never expected to
                # show up again as 'extensions/name/extensions/name/...',
                # hence an extension will not patch its own source file.)
                if ext_reader.extension_name == game_file.extension_name:
                    continue

                # Get the file, if any.
                if mode == 'substitution':
                    # For substitutions, want to just search the 'subst_'
                    # catalogs and not any loose files.
                    ext_game_file = ext_reader.Read(
                        virtual_path,
                        include_loose_files = False,
                        cat_prefix = 'subst_')
                else:
                    # For patches, want to search the 'ext_' catalogs and
                    # any loose files.
                    ext_game_file = ext_reader.Read(
                        virtual_path,
                        include_loose_files = True,
                        cat_prefix = 'ext_')

                # Skip if no matching file was found.
                # This is the normal case.
                if ext_game_file == None:
                    continue
            
                # Merge the extension version with the original.
                # Start by recording the extension name for reference
                #  by the extension_checker utility.
                self.ext_currently_patching = ext_game_file.extension_name

                # Call the merger.
                # This may return the ext_game_file if a substitution
                # occurred, so update the game_file link.
                game_file = game_file.Merge(ext_game_file)

                # Clear out the patching note.
                self.ext_currently_patching = None
            

        # Finish initializing the xml file once patching
        # is complete.
        game_file.Delayed_Init()

        return game_file


    def Get_All_Loose_Source_Files(self):
        '''
        Returns a dict of absolute paths to all loose files in the loose
        source folder, keyed by virtual path.
        '''
        if self.loose_source_reader == None:
            return {}
        return self.loose_source_reader.Get_All_Loose_Files()

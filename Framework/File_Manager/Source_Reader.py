'''
Support for reading source files, including unpacking from cat/dat files.
Includes File_Missing_Exception for when a file is not found.
'''
'''
Notes on the X4 file structure (filled out as it is learned):

    It appears that x4 is inconsistent with how it deals with file paths.

    Any file in the base x4 catalogs will have a virtual path
    relative to the root x4 folder.
        Eg. /libraries/parameters.xml

    However, files from extensions can have multiple treatments:
        a) A virtual path relative to the extension folder,
           if such a virtual path matches that of a base game file.
        b) A virtual path relative to the root x4 folder, including
           extensions/ext_name, for when adding a new file not
           part of the x4 base.
        c) A virtual path relative to the extension folder, but
           in turn targetting an extended path to a file added
           by another extension.

    This causes hiccups in the source file reading here.
    Situation (c) comes up when extensions edit files from other extensions.
    Awkwardly, it also comes up when there is no dependency in place,
    so extA can patch extB files without a dependency on extB.

    It is unclear on if a diff patch can be applied to another extension's
    diff patch.  Currently, it seems that patching only works on a base
    version of a file, patches being applied in dependency order.

    
    The loading approach will be to:
        a) Search for the base file version (not a patch).
            - This will establish the actual virtual_path of the file.
            - Paths not starting with 'extensions/' will look in the
              base x4 directory and the override source folder.
            - Paths starting with 'extensions/' will look only at the
              particular named extension, and will search inside it
              using a truncated path.

        b) Search for patches and substitutions.
            - All extensions are searched, not the base game folders.
            - If the path starts with 'extensions', the particular
              named extension can be skipped (cannot patch its own file).
            - Path is left unmodified.

        c) Apply the patches to the base in dependency order.

    For the current understanding, this seems sufficient to match x4 behavior.


Notes on case:
    To simplify path handling, all paths will be lower cased.
    This appears to sync up with the game internals, particularly in
    regard to linux support (which requires extensions use lower case
    in general for paths).
    A side effect is that extension names need to be stored in lower
    case, since they can show up in virtual paths.
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
            for extension_node in content_root.xpath('extension'):
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
                # Sometimes this will be included based on settings, eg. when
                #  only creating documentation.
                if (content_xml_path == output_content_path 
                and Settings.ignore_output_extension):
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
                    # Apparently a mod can use '1' for this instead of
                    # 'true', so try both.
                    enabled = content_root.get('enabled', 'true').lower() in ['true','1']
                if not enabled:
                    continue
                
                # Collect all the names of dependencies.
                # Lowercase these to standardize name checks.
                dependencies = [x.get('id').lower()
                                for x in content_root.xpath('dependency')]
                # Collect optional dependencies.
                soft_dependencies = [x.get('id') 
                                for x in content_root.xpath('dependency[@optional="true"]')]
                # Pick out hard dependencies (those not optional).
                hard_dependencies = [x for x in dependencies
                                     if x not in soft_dependencies ]
                
                # Create the reader object.
                # Don't worry about ordering just yet.
                reader = Location_Source_Reader(
                    location = content_xml_path.parent,
                    extension_name = name,
                    soft_dependencies = soft_dependencies,
                    hard_dependencies = hard_dependencies,
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

        * priorities
          - Dict, keyed by extension name, holding an integer priority.
          - Default priority is 0.
          - Negative priority loads an extension earlier, positive later.
        '''
        # TODO: maybe sort the ext_summary_dict so that extensions are
        # always loaded in the same order, which might be a better match
        # to X4 loading.

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

            # Now sort them in priority order, with secondary on name order.
            valid_next_exts = sorted(
                valid_next_exts,
                # Priority goes first (low to high), then name (A to Z).
                key = lambda ext: (priorities[ext.extension_path_name], 
                                   ext.extension_path_name))

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
        # and source folder.
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
        # was sourced from (if it came from an ext).
        for ext_reader in self.extension_source_readers.values():

            # Skip if this ext is the original source.
            # This should be harmless to allow, but saves a little time.
            if ext_reader.extension_name == game_file.extension_name:
                continue

            # Get the file, if any.
            ext_game_file = ext_reader.Read(virtual_path)
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

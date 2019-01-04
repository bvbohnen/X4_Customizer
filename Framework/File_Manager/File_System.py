
    
from pathlib import Path
import datetime
from collections import defaultdict
from lxml import etree as ET
from functools import wraps

from .Source_Reader import Source_Reader_class
from .Cat_Writer import Cat_Writer
from .File_Types import Misc_File, XML_File
from ..Common import Settings
from ..Common import File_Missing_Exception
from ..Common import Customizer_Log_class
from ..Common import Change_Log, Print
from ..Common import home_path


class File_System_class:
    '''
    Primary handler for all loaded files, including both read
    and write functionality. Also supports some parsing of
    xml content for easier lookups of file groups.

    Attributes:
    * game_file_dict
      - Dict, keyed by virtual path, holding loaded Game_File objects.
    * old_log
      - Customizer_Log_class holding information from the prior
        customizer run.
    * init_complete
      - Bool, set True after the delayed init function has completed.
    * source_reader
      - Source_Reader object.
    * asset_class_dict
      - Dict of dicts of lists holding XML_File objects, organized according
        to asset properties.
      - Outer key is the root node tag for supported tags,
        currently one of ['macros','components'].
      - Inner key is the "class" attribute of the first child node,
        eg. macros/macro/@class or components/component/@class.
      - Example: asset_class_dict['macros']['bullet'] to get all
        loaded bullet macro files.
      - Filled in as files are loaded or created; use Load_Pattern to fill
        in files on paths that hold the classes of  interest.
    * asset_name_dict
      - Dict of XML_File objects keyed by their "name" attribute.
      - Similar to asset_class_dict, except set up to satisfy the
        way x4 files can reference each other by "name" attribute
        without clarifying tag or "class".
    * _patterns_loaded
      - Set of strings, virtual path name patterns that have been
        loaded and, when macros, added to class_macro_dict.
    '''
    def __init__(self):
        self.game_file_dict = {}
        self.old_log = Customizer_Log_class()
        self.init_complete = False
        self.source_reader = Source_Reader_class()
        # Set this up as a defaultdict of defaultdicts of lists,
        # for easy initialization on new tags or classes.
        self.asset_class_dict = defaultdict(lambda: defaultdict(list))
        self.asset_name_dict = {}
        self._patterns_loaded = set()

        return
    

    def _Verify_Init(func):
        '''
        Small wrapper on functions that should verify the init
        check has been done before returning.
        Similar to what is in Settings.
        '''
        # Use functools wraps to preserve the docstring and such.
        @wraps(func)
        # All wrapped functions will have self.
        def func_wrapper(self, *args, **kwargs):
            # Run delayed init if needed.
            if not self.init_complete:
                self.Delayed_Init()
            # Run the func as normal.
            return func(self, *args, **kwargs)
        return func_wrapper


    def Delayed_Init(self):
        '''
        Initialize the file system and finalize Settings paths.
        '''
        # Skip early if already initialized.
        if self.init_complete:
            return
        self.init_complete = True

        # Make sure the settings are fully initialized at this point.
        # They normally are through a transform call, but may not be
        # if a file was loaded from outside a transform.
        Settings.Delayed_Init()

        # Read any old log file.
        self.old_log.Load(Settings.Get_Customizer_Log_Path())

        # Initialize the source reader, now that paths are set in settings.
        self.source_reader.Init_From_Settings()    
        return


    def Reset(self):
        '''
        Resets the file system, clearing out prior loaded files,
        returning to non-initialized state, etc.
        This will also reset the Live_Editor, since it is out of date.
        '''
        self.init_complete = False
        self.game_file_dict.clear()
        self.asset_class_dict.clear()
        self.asset_name_dict.clear()
        self._patterns_loaded.clear()
        # Pending a reset option for these, just recreate the objects.
        self.old_log = Customizer_Log_class()
        self.source_reader = Source_Reader_class()

        #-Removed; the live editor doesn't maintain hard links to
        #  loaded files, so it can keep its state (albeit it might
        #  be missing new objects and such); resets of the live editor
        #  will be handled elsewhere if/when wanted.
        #  (Also, resetting here breaks its automatic cell update
        #  after script runs.
        # Also reset the live editor. It should rebuild itself from
        # whatever new game files are loaded, to catch source changes.
        # Use a delayed import, due to an annoying circular import issue.
        #from ..Live_Editor_Components import Live_Editor
        #Live_Editor.Reset()
        return


    def Add_File(self, game_file):
        '''
        Record a new a Game_File object, keyed by its virtual path.
        '''
        self.game_file_dict[game_file.virtual_path] = game_file
        
        # Check if the game_file is an xml file with a supported
        # asset tag, and updates the asset_class_dict if so.
        if isinstance(game_file, XML_File) and game_file.asset_class_name != None:
            tag        = game_file.root_tag
            class_name = game_file.asset_class_name
            name       = game_file.asset_name
            # Record the file two ways.
            self.asset_class_dict[tag][class_name].append(game_file)
            self.asset_name_dict[name] = game_file
        return


    def Reset_File(self, virtual_path):
        '''
        Reset a single file, if loaded. Any later Load_File calls
        will pull a fresh copy from the known source locations.
        Note: this does not clear out any existing references to
        the file object that may have been recorded elsewhere.
        '''
        if virtual_path not in self.game_file_dict:
            return

        # Look up the game file.
        game_file = self.Load_File(virtual_path)
        # Remove from the main file dict.
        self.game_file_dict.pop(virtual_path)

        # Also remove from anywhere else that might use it.
        # These will use a game_file object search.
        for key, subdict in self.asset_class_dict.items():
            for key2, sublist in subdict.items():
                if game_file in sublist:
                    sublist.remove(game_file)

        for key, value in self.asset_name_dict.items():
            if value is game_file:
                # This should be okay to modify the dict if not continuing
                # the loop further.
                self.asset_name_dict.pop(key)
                break
        return


    def Get_Asset_File(self, name):
        '''
        Returns a loaded asset XML_File object with the corresponding
        "name" (as found in the xml).  Error if not found.
        
        Example: Get_Asset_File('weapon_tel_l_beam_01_mk1')
        '''
        return self.asset_name_dict[name]


    def Get_Asset_Files_By_Class(self, tag, *class_names):
        '''
        Returns the list of loaded asset XML_Files matching the
        given tag and class_names. Accepts multiple class names.
        Returns an empty list if no matching files are loaded yet.

        Example: Get_Asset_Files('macros','bullet','missile')
        '''
        ret_list = []
        # Collect lists together.
        for name in class_names:
            ret_list += self.asset_class_dict[tag][name]
        return ret_list
    
    
    @_Verify_Init
    def Get_Indexed_File(self, index, name):
        '''
        Returns a Game_File found on a path read from the given
        index matching the given name. Loads the file if needed.

        * index
          - String, one of 'macros','components'.
        * name
          - Name to look up, without path or extension.
        '''
        # Bounce over to the pattern based lookup.
        game_files = self.Get_All_Indexed_Files(index, name)
        # Expect 0 or 1 files returned.
        if game_files:
            return game_files[0]
        return None

    
    @_Verify_Init
    def Get_All_Indexed_Files(self, index, pattern):
        '''
        Returns a list of Game_Files found on paths in the given
        index matching the given pattern.
        Loads the files as needed. Broken links are skipped.
        Duplicate links are ignored.

        * index
          - String, one of 'macros','components'.
        * pattern
          - Name pattern to look up, with wildcards, without path
            or extension.
        '''
        assert index in ['macros','components']#,'mousecursors']
        # Start by loading the libraries/macros.xml index.
        index_xml = self.Load_File('index/{}.xml'.format(index))

        # Use its convenient Get function.
        virtual_paths = index_xml.Findall(pattern)
        ret_list = []
        for path in virtual_paths:
            # If there is no file of this name, or it is empty,
            # skip it; there seem to be broken links in the
            # index files.
            game_file = self.Load_File(path, error_if_not_found = False)
            if game_file != None:
                ret_list.append(game_file)
        return ret_list


    def File_Is_Loaded(self, virtual_path):
        '''
        Returns True if a file of the given virtual_path has been
        loaded, else False.
        '''
        if virtual_path in self.game_file_dict:
            return True
        return False

    
    @_Verify_Init
    def Load_File(
            self,
            virtual_path,
            error_if_not_found = True,
            test_load = False,
            ):
        '''
        Returns a Game_File subclass object for the given file, according
        to its extension.
        If the file has not been loaded yet, reads from the expected
        source file. Files which are XML macros or components
        be recorded according to their "class" attribute.

        * virtual_path
          - Name of the file, using the cat_path style (forward slashes,
            relative to X4 base directory).
          - May have mixed case and reverse slashes, but will be
            lowercased and forward slashed internally.
        * error_if_not_found
          - Bool, if True and the file is not found, raises an exception,
            else returns None.
        * test_load
          - Bool, if True then the file will be loaded regardless of
            any currently tracked version of it, and the results will
            not be recorded.
          - When in use, None is returned.
        '''
        # Standardize all virtual paths to lower case, forward slashes.
        # (Back slashes show up in some xml attribute paths, so converting
        # here makes those easier to manage.)
        virtual_path = virtual_path.lower().replace('\\','/')

        # If the file is not loaded, handle loading.
        if virtual_path not in self.game_file_dict or test_load:

            # Get the file using the source_reader, maybe pulling from
            #  a cat/dat pair.
            # Returns a Game_File object, of some subclass, or None
            #  if not found.
            game_file = self.source_reader.Read(virtual_path, error_if_not_found = False)

            # Problem if the file isn't found.
            if game_file == None:
                if error_if_not_found:
                    raise File_Missing_Exception(
                        'Could not find file "{}", or file was empty'.format(virtual_path))
                return None
        
            # Store the contents in the game_file_dict if not in testing.
            if not test_load:
                self.Add_File(game_file)
            else:
                return None

        # Return the file contents.
        return self.game_file_dict[virtual_path]
    

    def Load_Files(self, pattern):
        '''
        Searches for and loads in xml files following the given
        virtual_path wildcard pattern.
        Returns a list of files loaded.
        '''
        # Limit each pattern to running once.
        if pattern in self._patterns_loaded:
            return
        self._patterns_loaded.add(pattern)

        # Load all files matching the pattern.
        files = []
        for virtual_path in self.Gen_All_Virtual_Paths(pattern):
            files.append( self.Load_File(virtual_path) )
        return files

    
    @_Verify_Init
    def Get_Source_Reader(self):
        '''
        Returns the current Source_Reader.
        '''
        return self.source_reader

    
    @_Verify_Init
    def Get_Extension_Names(self):
        '''
        Returns a list of names of all enabled extensions.
        '''
        return self.source_reader.Get_Extension_Names()

          
    @_Verify_Init
    def Cleanup(self):
        '''
        Handles cleanup of old transform files.
        This is done blindly for now, regardless of it this run intends
         to follow up by applying another renaming and writing new files
         in place of the ones removed.
        This should preceed a call to any call to Write_Files, though can
         be run standalone to do a generic cleaning.
        Preferably do this late in a run, so that files from a prior run
         are not removed if the new run had an error during a transform.
        '''
        Print('Cleaning up old files')

        # TODO: maybe just completely delete the extension/customizer contents,
        # though that would mess with logs and messages that have been written
        # to up to this point.
        # It is cleaner other than that, though. Maybe manually skip the logs
        # or somesuch.

        # Find all files generated on a prior run, that still appear to be
        #  from that run (eg. were not changed externally), and remove
        #  them.
        # TODO: clean up empty folders.
        for path in self.old_log.Get_File_Paths_From_Last_Run():
            if path.exists():
                path.unlink()
        return
            
    
    @_Verify_Init
    def Add_Source_Folder_Copies(self):
        '''
        Adds Misc_File objects which copy files from the user source
        folders to the game folders.
        This should only be called after transforms have been completed,
        to avoid adding a copy of a file that was already loaded and
        edited.
        All source folder files, loaded here or earlier, will be flagged
        as modified.
        '''
        # Some loose files may be present in the user source folder which
        #  are intended to be moved into the main folders, whether transformed
        #  or not, in keeping with behavior of older versions of the customizer.
        # These will do direct copies.
        for virtual_path, sys_path in self.source_reader.Get_All_Loose_Source_Files().items():
            # TODO:
            # Skip files which do not match anything in the game cat files,
            #  to avoid copying any misc stuff (backed up files, notes, etc.).
            # This will need a function created to search cat files without
            #  loading from them.

            # Check for files not loaded yet.
            if virtual_path not in self.game_file_dict:
                # Read the binary.
                with open(sys_path, 'rb') as file:
                    binary = file.read()

                # Create the game file.
                self.Add_File(Misc_File(binary = binary, 
                                   virtual_path = virtual_path))

            # Set as modified to force writeout.
            self.game_file_dict['virtual_path'].modified = True
        return

                
    @_Verify_Init
    def Write_Files(self):
        '''
        Write output files for all source file content used or
         created by transforms, either to loose files or to a catalog
         depending on settings.
        Existing files which may conflict with the new writes will be renamed,
         including files of the same name as well as their .pck versions.
        '''
        Print('Writing output files' 
              + (' (diff encoded)' if not Settings.make_maximal_diffs else ''))
        #to {}'.format(Settings.Get_Output_Folder()))

        # Add copies of leftover files from the user source folder.
        # Do this before the proper writeout, so it can reuse functionality.
        self.Add_Source_Folder_Copies()

        # TODO: do a pre-pass on all files to do a test write, then if all
        #  look good, do the actual writes and log updates, to weed out
        #  bugs early.
        # Maybe could do it Clang style with gibberish extensions, then once
        #  all files, written, rename then properly.

        # Record the output folder in the log.
        log = Customizer_Log_class()

        # Pick the path to the catalog folder and file.
        cat_path = Settings.Get_Output_Folder() / 'ext_01.cat'

        # Note: this path may be the same as used in a prior run, but
        #  the prior cat file should have been removed by cleanup.
        assert not cat_path.exists()
        cat_writer = Cat_Writer(cat_path)

        # Set up the content.xml file. -Moved to plugin.
        #self.Make_Extension_Content_XML()

        # Loop over the files that were loaded.
        for file_name, file_object in self.game_file_dict.items():

            # Skip if not modified.
            if not file_object.modified:
                continue

            # In case the target directory doesn't exist, such as on a
            #  first run, make it, but only when not sending to a catalog.
            if not Settings.output_to_catalog:
                # Look up the output path.
                file_path = Settings.Get_Output_Folder() / file_object.virtual_path
        
                folder_path = file_path.parent
                if not folder_path.exists():
                    folder_path.mkdir(parents = True)
                
                # Write out the file, using the object's individual method.
                file_object.Write_File(file_path)

                # Add this to the log, post-write for correct hash.
                log.Record_File_Path_Written(file_path)

                # Refresh the log file, in case a crash happens during file
                #  writes, so this last write was captured.
                log.Store()

            else:
                # Add to the catalog writer.
                cat_writer.Add_File(file_object)


        # If anything was added to the cat_writer, do its write.
        if cat_writer.game_files:
            cat_writer.Write()

            # Log both the cat and dat files as written.
            log.Record_File_Path_Written(cat_writer.cat_path)
            log.Record_File_Path_Written(cat_writer.dat_path)

            # Refresh the log file.
            log.Store()

        return

    
    @_Verify_Init
    def Copy_File(
            self,
            source_virtual_path,
            dest_virtual_path = None
        ):
        '''
        Suport function to copy a file from a source folder under this project, 
        to a dest folder. Typically used for scripts, objects, etc.
        Note: this simply creates a Game_File object, and the file write
        will occur during normal output.

        * source_virtual_path
          - Virtual path for the source file, which matches the folder
            structure in the project source folder.
        * dest_virtual_path
          - Virtual path for the dest location.
          - If None, this defaults to match the source_virtual_path.
        '''
        # Normally, the dest will just match the source.
        if dest_virtual_path == None:
            dest_virtual_path = source_virtual_path

        # Get the path for where to find the source file, and load
        #  its binary.
        # Similar to above, but the folder is located in this project.    
        with open(home_path / 'game_files' / virtual_path, 'rb') as file:
            source_binary = file.read()

        # Create a generic game object for this, using the dest path.
        self.Add_File( Misc_File(
            virtual_path = dest_virtual_path, 
            binary = source_binary))

        return


    def Get_Date(self):
        '''
        Returns the current date, as a string.
        '''
        return str(datetime.date.today())
    
    
    @_Verify_Init
    def Gen_All_Virtual_Paths(self, pattern = None):
        '''
        Generator which yields all virtual_path names of all discovered files,
        optionally filtered by a wildcard pattern.

        * pattern
          - String, optional, wildcard pattern to use for matching names.
        '''
        # Pass the call to the source reader.
        # TODO: swap this around to gathering a set of paths here,
        #  and adding to them new files that get added during runtime.
        yield from self.source_reader.Gen_All_Virtual_Paths(pattern)
        return
    

# Static copy of the file system object.
File_System = File_System_class()
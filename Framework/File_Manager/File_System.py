
    
from pathlib import Path
import datetime
from collections import defaultdict
from lxml import etree as ET
from functools import wraps
import fnmatch
from time import time
import re

from .Source_Reader import Source_Reader_class
from .Cat_Writer import Cat_Writer
from .File_Types import Misc_File, XML_File, Signature_File, Machine_Code_File
from .File_Types import Generate_Signatures
from ..Common import Settings
from ..Common import File_Missing_Exception
from ..Common import Customizer_Log_class
from ..Common import Change_Log, Plugin_Log, Print
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
        
        # To add safety against threading mistakes, where two are
        # trying to init and run at once, clear this flag at
        # the end of init and not earlier (so a second thread has
        # more trouble racing ahead of the first that is still in
        # init). Long term, care should be taken with thread to
        # avoid needing this.
        self.init_complete = False
        return


    def Add_File(self, game_file):
        '''
        Record a new a Game_File object, keyed by its virtual path.
        '''
        self.game_file_dict[game_file.virtual_path] = game_file
        
        # Check if the game_file is an xml file with a supported
        # asset tag, and updates the asset_class_dict if so.
        if isinstance(game_file, XML_File) and game_file.asset_class_name_dict != None:
            tag        = game_file.root_tag
            # There could be multiple assets of different classes, so
            # loop over them.
            for class_name, name_list in game_file.asset_class_name_dict.items():
                for name in name_list:
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
        The returned file may contain other assets.
        
        Example: Get_Asset_File('weapon_tel_l_beam_01_mk1')
        '''
        return self.asset_name_dict[name]


    def Get_Asset_Files_By_Class(self, tag, *class_names):
        '''
        Returns the list of loaded asset XML_Files matching the
        given tag and class_names. Accepts multiple class names.
        Returns an empty list if no matching files are loaded yet.
        Can preceed with Load_Files for expected file names.

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
        Can be followed by Get_Assets_By_Class if extra class checking
        safety is wanted.

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
            else:
                # Warn on broken link.
                # Add some little state to prevent warning multiple times
                # on the same file.
                if not hasattr(self, '_index_file_not_found_paths'):
                    self._index_file_not_found_paths = []
                if path not in self._index_file_not_found_paths:
                    Plugin_Log.Print(f'Warning: no file found on index.xml specified path: {path}')
                    self._index_file_not_found_paths.append(path)

        # On the off-chance there are duplicates (eg. one file provides
        # multiple macros), filter them out here.
        # TODO: maybe think about maintaining ordering.
        return list(set(ret_list))


    def File_Is_Loaded(self, virtual_path):
        '''
        Returns True if a file of the given virtual_path has been
        loaded, else False.
        '''
        if virtual_path in self.game_file_dict:
            return True
        return False


    def Get_Loaded_Files(self, pattern = None):
        '''
        Returns a list of Game_File objects that are currently loaded.
        Optionally, loads only files with virtual_paths matching
        the given pattern.
        '''
        if not pattern:
            return list(self.game_file_dict.values())

        # Start with the pattern processing.
        #ret_list = []
        #for path, game_file in self.game_file_dict.items():
        #    if pattern == None or fnmatch(path, pattern):
        #        ret_list.append(game_file)
        # Speed up with filter().
        paths = fnmatch.filter(self.game_file_dict.keys(), pattern)
        return [self.game_file_dict[x] for x in paths]
    

    @_Verify_Init
    def Load_File(
            self,
            virtual_path,
            error_if_not_found = True,
            error_if_unmatched_diff = False,
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
        * error_if_unmatched_diff
          - Bool, if True a Unmatched_Diff_Exception will be thrown
            if the assumed base file is found to be a diff patch.
          - Default is to log an error and return None.
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
            game_file = self.source_reader.Read(
                virtual_path, 
                error_if_not_found = False,
                error_if_unmatched_diff = error_if_unmatched_diff)

            # Problem if the file isn't found.
            if game_file == None:
                if error_if_not_found:
                    raise File_Missing_Exception(('Error: Could not find file'
                            ' "{}", or file was empty').format(virtual_path))
                return None
        
            # Store the contents in the game_file_dict if not in testing.
            if not test_load:
                assert game_file.virtual_path == virtual_path
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
        # -Removed; skipping like this fails to fill the return list.
        ## Limit each pattern to running once.
        #if pattern in self._patterns_loaded:
        #    return
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
        
        # Find all files generated on a prior run, that still appear to be
        #  from that run (eg. were not changed externally), and remove
        #  them. Note: change check has been removed for now, since it
        #  is not so important for x4 as it was for x3.
        for path in self.old_log.Get_File_Paths_From_Last_Run():
            # Make a special exception for files created outside of
            # the extension (mainly the exe); those tend to be more
            # expensive to create, and could be from other customizer
            # extension runs, so leave it to the user to handle them.
            if Settings.Get_Output_Folder() not in path.parents:
                continue

            if path.exists():
                path.unlink()

                # Clean up empty folders, going upward.
                parent_dir = path.parent
                while 1:
                    try:
                        # This fails if not empty.
                        # Will naturally stop once reaching the old log.
                        parent_dir.rmdir()
                        parent_dir = parent_dir.parent
                    except:
                        break
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
            self.game_file_dict[virtual_path].modified = True
        return

                
    @_Verify_Init
    def Write_Files(self):
        '''
        Write output files for all source file content used or
        created by transforms, either to loose files or to a catalog
        depending on settings.
        '''
        Print('Writing output files' 
              + (' (diff encoded)' if not Settings.make_maximal_diffs else ''))
        #Print('Output dir: {}'.format(Settings.Get_Output_Folder()))

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

        # TODO: second cat for subst files, with some way to flag
        # which game_files are substitutions (eg. anything not xml
        # that path matches some vanilla or other extension file).

        # Note: this path may be the same as used in a prior run, but
        #  the prior cat file should have been removed by cleanup.
        assert not cat_path.exists()
        cat_writer = Cat_Writer(cat_path)

        # Set up the content.xml file. -Moved to plugin.
        #self.Make_Extension_Content_XML()

        # Handle generic sig file creation.
        if Settings.generate_sigs:
            for game_file in Generate_Signatures(self.game_file_dict.values()):
                self.game_file_dict[game_file.virtual_path] = game_file


        # Loop over the files that were loaded.
        for file_name, file_object in self.game_file_dict.items():

            # Skip if not modified and not a sig.
            if not file_object.modified:
                continue

            # In case the target directory doesn't exist, such as on a
            #  first run, make it, but only when not sending to a catalog.
            # Machine_Code_File files will never go in a catalog.
            if (not Settings.output_to_catalog 
            or isinstance(file_object, Machine_Code_File)):

                # Look up the output path.
                file_path = file_object.Get_Output_Path()
        
                # Generate the folder if needed.
                folder_path = file_path.parent
                if not folder_path.exists():
                    folder_path.mkdir(parents = True)

                # If the file already exists, something went wrong, so
                # throw an error. (It should have been deleted already
                # if from last run.) Skip this check for exe files, which
                # use custom naming to get around overwrite dangers.
                if file_path.exists() and not isinstance(file_object, Machine_Code_File):
                    Print(('Error: skipping write due to file existing on path: {}'
                           ).format(file_path))
                    continue

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

    
    @_Verify_Init
    def Read_Text(self, text = None, page = None, id = None):
        '''
        Reads and returns the text at the given {page,id}.
        Recursively expands nested references.
        Removes comments in parentheses.
        Returns None if no text found.

        * text
          - String, including any internal '{page,id}' terms.
        * page, id
          - Int or string, page and id separated; give for direct
            dereference instead of a full text string.
        '''
        # Currently expect all text to be in the 0001 file, but could
        # be split between currently language (eg. 0001-l044.xml) and
        # a generic fallback (eg. 0001.xml).
        # TODO: get a language code from Settings.

        # Kick it off with the language specific lookup.
        t_files = [
            File_System.Load_File('t/0001-L044.xml'),
            # This one may not be present; ego doesn't use it, but mods might.
            # TODO: what happens if two mods use this? are strings joined?
            # TODO: will tend to fail since there is no vanilla version of
            # this file; will need special handling to create a vanilla
            # dummy that extensions can append to.
            File_System.Load_File('t/0001.xml', error_if_not_found = False),
            ]

        
        # If page and id given, pack them in a string to reuse the
        # following code. Probably don't need to worry about performance
        # of this.
        if text == None:
            assert page != None and id != None
            text = '{{{},{}}}'.format(page,id)
                       
        # Remove any comments, in parentheses.
        if '(' in text:
            # .*?     : Non-greed match a series of chars.
            # \( \)   : Match parentheses
            # (?<!\\) : Look behind for no preceeding escape char.
            # Note: put all this in a raw string to avoid python escapes.
            text = ''.join(re.split(r'(?<!\\)\(.*?(?<!\\)\)', text))
        #if text.startswith('(') and ')' in text:
        #    text = text.split(')',1)[1]

        # Remove leftover escape characters, blindly for now (assume
        # they are never escaped themselves).
        text = text.replace('\\','')

        # If lookups are present, deal with them recursively.
        if '{' in text:
            # RE pattern used:
            #  .*    : Match a series of chars.
            #  .*?   : As above, but changes to non-greedy.
            #  {.*?} : Matches between { and }.
            #  ()    : When put around pattern in re.split, returns the
            #          separators (eg. the text lookups).
            new_text = ''
            for term in re.split('({.*?})', text):
                # Skip empty terms (eg. when there is no text before the 
                # first '{').
                if not term:
                    continue

                # Check if it is a nested lookup.
                if term.startswith('{'):

                    # Search each of the t_files in order to see if any
                    # of them have it, taking the first hit.
                    replacement_text = None
                    for file in t_files:
                        replacement_text = file.Read(term)
                        if replacement_text != None:
                            break

                    # If the text wasn't found, just leave the term as-is.
                    if replacement_text == None:
                        replacement_text = term

                    # Otherwise, recursively process it, since it could
                    # have more nested references.
                    else:
                        new_text += self.Read_Text(replacement_text)

                else:
                    # There was no lookup for this term; just append
                    # it back to the text string.
                    new_text += term

            # Overwrite the text with the replacements.
            text = new_text
            
        # Send back the processed text.
        return text

        
        # Search for the text.
        ret_text = None
        for file in t_files:
            if file == None:
                continue
            # If this runs into a nested reference, point it back to this
            # function for the next step lookup.
            # TODO: how to avoid this Read failing to find a term, call
            # back to Read_Text, and Read_Text calling Read on the same
            # t_file again (inf loop). Protection should also avoid bouncing
            # between two t_files each failing their Read.
            ret_text = file.Read(
                text = text, 
                page = page, 
                id = id,
                nested_read_text_func = self.Read_Text)

            # If the above returned something useful, use it.
            if ret_text != None:
                break
            # Otherwise keep looping.

        # If text is still None, something failed to resolve.
        # Could potentially return None, which will cause any higher level
        # calls to this function (this could be the bottom of a reference
        # stack) to fail and return None.
        # Alternatively, use a "read_text" fallback, which will also help
        # references resolve.
        if ret_text == None:
            if text != None:
                ret_text = text
            else:
                ret_text = f'{{{page},{id}}}'
        return ret_text
    

# Static copy of the file system object.
File_System = File_System_class()
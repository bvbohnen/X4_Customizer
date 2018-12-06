'''
Loads and stores source files to be modified, and writes them
out when finished.

TODO: rename this to be different than the package.
'''

import os
from pathlib import Path
from collections import OrderedDict
import inspect
import shutil

from .. import Common
Settings = Common.Settings
from . import Source_Reader
Source_Reader = Source_Reader.Source_Reader
from . import Cat_Writer
from .File_Types import *
from . import Logs
Log_New = Logs.Log_New
Log_Old = Logs.Log_Old
    

# On the first call to Load_File from any transform, do some extra
#  setup.
First_call = True
def Init():
    'Initialize the file manager.'
    # Safety check for First_call already being cleared, return early.
    global First_call
    if not First_call:
        return
    First_call = False

    # The file paths should be defined at this point. Error if not.
    Settings.Verify_Setup()

    # Read any old log file.
    Log_Old.Load()

    # Initialize the file system, now that paths are set in settings.
    Source_Reader.Init()
    
    #-Removed for now.
    ## Generate an initial dummy file for all page text overrides.
    #game_file = Page_Text_File(
    #    virtual_path = Settings.Get_Page_Text_File_Path(),
    #    )
    #Add_File(game_file)

    return


# Dict to hold file contents, as well as specify their full path.
# Keyed by virtual path for the file.
# This gets filled in by transforms as they load the files.
# T files will generally be loaded into lists of dictionaries keyed by field
#  name or index, with each list entry being a separate line.
# XML files will generally be loaded as a XML_File object holding
#  the encoding and raw text.
# These are Game_File objects, and will record their relative path
#  to be used during output.
File_dict = {}

def Add_File(game_file):
    '''
    Add a Game_File object to the File_dict, keyed by its virtual path.
    '''
    File_dict[game_file.virtual_path] = game_file


def Load_File(file_name,
              # TODO: rename this to be more generic.
              return_game_file = False, 
              return_text = False,
              error_if_not_found = True):
    '''
    Returns a Game_File subclass object for the given file, according
    to its extension.
    If the file has not been loaded yet, reads from the expected
    source file.

    * file_name
      - Name of the file, using the cat_path style (forward slashes,
        no 'addon' folder).
      - For the special text override file to go in the addon/t folder,
        use 'text_override', which will be translated to the correct
        name according to Settings.
    * error_if_not_found
      - Bool, if True and the file is not found, raises an exception,
        else returns None.
    '''
    # If the file is not loaded, handle loading.
    if file_name not in File_dict:

        # Get the file using the source_reader, maybe pulling from
        #  a cat/dat pair.
        # Returns a Game_File object, of some subclass, or None
        #  if not found.
        game_file = Source_Reader.Read(file_name, error_if_not_found = False)

        # Problem if the file isn't found.
        if game_file == None:
            if error_if_not_found:
                raise Common.File_Missing_Exception(
                    'Could not find file {}, or file was empty'.format(file_name))
            return None
        
        # Store the contents in the File_dict.
        Add_File(game_file)

    # Return the file contents.
    return File_dict[file_name]

          
def Cleanup():
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
    # It is possible Init was never run if no transforms were provided.
    # Ensure it gets run here in such cases.
    if First_call:
        Init()

    # TODO: maybe just completely delete the extension/customizer contents,
    # though that would mess with logs and messages that have been written
    # to up to this point.
    # It is cleaner other than that, though. Maybe manually skip the logs
    # or somesuch.

    # Find all files generated on a prior run, that still appear to be
    #  from that run (eg. were not changed externally), and remove
    #  them.
    for path in Log_Old.Get_File_Paths_From_Last_Run():
        if os.path.exists(path):
            os.remove(path)            
    return
            

def Add_Source_Folder_Copies():
    '''
    Adds Misc_File objects which copy files from the user source
     folders to the game folders.
    This should only be called after transforms have been completed,
     to avoid adding a copy of a file that was already loaded and
     edited.
    '''
    # Some loose files may be present in the user source folder which
    #  are intended to be moved into the main folders, whether transformed
    #  or not, in keeping with behavior of older versions of the customizer.
    # These will do direct copies.
    for virtual_path, sys_path in Source_Reader.source_file_path_dict.items():
        # Skip files already written.
        if virtual_path in File_dict:
            continue

        # TODO:
        # Skip files which do not match anything in the game cat files,
        #  to avoid copying any misc stuff (backed up files, notes, etc.).
        # This will need a function created to search cat files without
        #  loading from them.

        # Read the binary.
        with open(sys_path, 'rb') as file:
            binary = file.read()

        # Create the game file.
        Add_File(Misc_File(binary = binary, virtual_path = virtual_path))
    return

                
def Write_Files():
    '''
    Write output files for all source file content used or
     created by transforms, either to loose files or to a catalog
     depending on settings.
    Existing files which may conflict with the new writes will be renamed,
     including files of the same name as well as their .pck versions.
    '''
    # Add copies of leftover files from the user source folder.
    # Do this before the proper writeout, so it can reuse functionality.
    Add_Source_Folder_Copies()

    # TODO: do a pre-pass on all files to do a test write, then if all
    #  look good, do the actual writes and log updates, to weed out
    #  bugs early.
    # Maybe could do it Clang style with gibberish extensions, then once
    #  all files, written, rename then properly.

    # Pick the path to the catalog folder and file.
    cat_path = Settings.Get_Output_Folder() / 'ext_01.cat'

    # Note: this path may be the same as used in a prior run, but
    #  the prior cat file should have been removed by cleanup.
    assert not cat_path.exists()
    cat_writer = Cat_Writer.Cat_Writer(cat_path)


    # Loop over the files that were loaded.
    for file_name, file_object in File_dict.items():

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
            Log_New.Record_File_Path_Written(file_path)

            # Refresh the log file, in case a crash happens during file
            #  writes, so this last write was captured.
            Log_New.Store()

        else:
            # Add to the catalog writer.
            cat_writer.Add_File(file_object)


    # If anything was added to the cat_writer, do its write.
    if cat_writer.game_files:
        cat_writer.Write()

        # Log both the cat and dat files as written.
        Log_New.Record_File_Path_Written(cat_writer.cat_path)
        Log_New.Record_File_Path_Written(cat_writer.dat_path)

        # Refresh the log file.
        Log_New.Store()

    return


# Preset the directory where the customizer resides, which
#  is one level up from here.
# Note: pyinstaller can change directories around, and needs special
#  handling here.
# See https://stackoverflow.com/questions/404744/determining-application-path-in-a-python-exe-generated-by-pyinstaller
# In short, a 'frozen' attribute is added to sys by pyinstaller,
#  so can be checked for a post-installer format.
# Further, _MEIPASS will be given the app base folder.
import sys
if getattr(sys, 'frozen', False):
    # This appears to be the launch folder, so no extra pathing needed.
    _customizer_dir = Path(sys._MEIPASS)
else:
    _customizer_dir = Path(__file__).resolve().parent.parent

def Copy_File(
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
    with open(_customizer_dir / '..' / 'game_files' / virtual_path, 'rb') as file:
        source_binary = file.read()

    # Create a generic game object for this, using the dest path.
    Add_File(Misc_File(virtual_path = dest_virtual_path, 
                       binary = source_binary))

    return


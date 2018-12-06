'''
Support for reading source files, including unpacking from cat/dat files.
Includes File_Missing_Exception for when a file is not found.
Import as:
    from Source_Reader import *
'''
import os
from pathlib import Path # TODO: convert all from os to pathlib.
from ..Common.Settings import Settings
from .Logs import *
from collections import OrderedDict
from . import File_Types
from .Cat_Reader import Cat_Reader
from .. import Common


class Source_Reader_class:
    '''
    Class used to find and read the highest priority source files.

    The general search order is:
    * Source folder defined in the settings.
    * Loose folders, including scripts. (May change.)
    * Cat files in the X4 folder numbered 01 through the highest
      contiguous 2-digit number, higher number taking precedence.

    Files which were generated on a prior customizer run (identified
    by matching a hash in the prior run's log) will be skipped.
    
    Cat files will be parsed as they are reached in the search order,
    not before, to avoid excessive startup time when deeper cat files
    may never be needed.

    Attributes:
    * catalog_file_dict
      - OrderedDict of Cat_Reader objects, keyed by file path, organized
        by priority, where the first entry is the highest priority cat.
      - TODO: include mods.
      - Dict entries are initially None, and get replaced with Catalog_Files
        as the cats are searched.
    * source_file_path_dict
      - Dict, keyed by virtual_path, holding the system path
        for where the file is located, for files in the source folder
        specified in the Settings.
    '''
    def __init__(self):
        self.catalog_file_dict = OrderedDict()
        self.source_file_path_dict = {}


    def Init(self):
        '''
        Initializes the file system by finding files in the source folder,
         and finding all cat files in priority order.
        This should be run after paths have been set up in Settings.
        '''
        # Look up the source folder.
        source_folder = Settings.Get_Source_Folder()
        
        # If it is not None, look into it.
        if source_folder != None:

            # Dynamically find all files in the source folder.
            # These will all be copied at final writeout, even if not modified,
            #  eg. if a transform was formerly run on a file but then commented
            #  out, need to overwrite the previous results with a non-transformed
            #  version of the file.
            for file_path in source_folder.glob('**'):

                # Isolate the relative part of the path.
                relative_path = file_path.relative_to(source_folder)
                # Swap out the separators from system default to standardized
                #  forward slashes.
                virtual_path = relative_path.replace(os.path.sep, '/')
                # Can now record it.
                self.source_file_path_dict[virtual_path] = file_path
                

        # Search for cat files the game will recognize.
        # These start at 01.cat, and count up as 2-digit values until
        #  the count is broken.
        # For convenience, the first pass will fill in a list with low
        #  to high priority, then the list can be reversed at the end.
        cat_dir_list_low_to_high = []

        # Loop until a cat index not found.
        cat_index = 1
        while 1:
            # Error if hit 100.
            assert cat_index < 100
            cat_name = '{:02d}.cat'.format(cat_index)
            cat_path = Settings.Get_X4_Folder() / cat_name
            # Stop if the cat file is not found.
            if not cat_path.exists():
                break
            # Record it.
            cat_dir_list_low_to_high.append(cat_path)
            # Increment for the next cat.
            cat_index += 1

        # TODO: visit all enabled extensions (satisfying dependencies).
               
        # Fill in dict entries with the list paths, in reverse order.
        for path in reversed(cat_dir_list_low_to_high):
            self.catalog_file_dict[path] = None
            
        return
    

    def Read(self, 
             virtual_path,
             error_if_not_found = True,
             copy_to_source_folder = False
             ):
        '''
        Returns a Game_File including the contents read from the
         source folder or unpacked from a cat file.
        Contents may be binary or text, depending on the Game_File subclass.
        This will search for packed versions as well, automatically unzipping
         the contents.
        If the file contents are empty, this returns None; this may occur
         for LU dummy files.
         
        * virtual_path
          - String, virtual path of the file to look up.
          - For files which may be gzipped into a pck file, give the
            expected non-zipped extension (.xml, .txt, etc.).
        * error_if_not_found
          - Bool, if True an exception will be thrown if the file cannot
            be found, otherwise None is returned.
        * copy_to_source_folder
          - Bool, if True and the file is read from a cat/dat pair, then
            a copy of the data will be placed into the source folder.
          - The copy is made after any unzipping is applied.
          - Pending development.
        '''
        # Grab the extension.
        file_extension = virtual_path.rsplit('.',1)[1]

        # Binary data read from a file.
        # Once a source is found, this will be filled in, so later
        #  source checks can be skipped once this is not None.
        file_binary = None
        # For debug, the path of the file sourced from, maybe a cat.
        file_source_path = None

        # TODO: check extensions.

        # Check the source folder.
        if Settings.Get_Source_Folder() != None:
            sys_path = Settings.Get_Source_Folder() / virtual_path
            if sys_path.exists():
                # Open the file and grab the binary data.
                # If this needs to be treated as text, it will be
                #  reinterpretted elsewhere.
                file_source_path = sys_path
                with open(file_source_path, 'rb') as file:
                    file_binary = file.read()
                

        # Check for a loose file outside the source folder, unless
        #  this is disabled in the settings.
        if file_binary == None and Settings.ignore_loose_files == False:
            sys_path = Settings.Get_X4_Folder() / virtual_path
            if sys_path.exists():
                # Load from the selected file.
                file_source_path = file_path_to_source
                with open(file_source_path, 'rb') as file:
                    file_binary = file.read()


        # If still no binary found, check the cat/dat pairs.
        if file_binary == None:

            # Loop over the cats in priority order.
            for cat_file, cat_reader in self.catalog_file_dict.items():

                # If the reader hasn't been created, make it.
                if cat_reader == None:
                    cat_reader = Cat_Reader(cat_file)
                    self.catalog_file_dict[cat_file] = cat_reader

                    # Check the cat for the file.
                    file_binary = cat_reader.Read(virtual_path)

                # Stop looping over cats once a match found.
                if file_binary != None:
                    break


        # If no binary was found, error.
        if file_binary == None:
            if error_if_not_found:
                raise Common.File_Missing_Exception(
                    'Could not find a match for file {}'.format(virtual_path))
            return None


        # Convert the binary into a Game_File object.
        # The object constructors will handle parsing of binary data,
        #  so this just checks file extensions and picks the right class.
        # Some special lookups will be done for select files.
        if file_extension == 'xml':
            game_file_class = File_Types.XML_File
        # TODO: lua or other files of interest.
        else:
            raise Exception('File type for {} not understood.'.format(virtual_path))

        # Construct the game file.
        # These will also record the path used, to help know where to place
        #  an edited file in the folder structure.
        game_file = game_file_class(
            file_binary = file_binary,
            virtual_path = virtual_path,
            file_source_path = file_source_path,
            )

        if Settings.write_file_source_paths_to_message_log:
            Write_Summary_Line(
                'Loaded file {} from {}'.format(virtual_path, file_source_path))
        
        return game_file


# Single, global copy of the reader.
# TODO: make a copy part of a File_System or similar object, instead
#  of keeping one here.
Source_Reader = Source_Reader_class()
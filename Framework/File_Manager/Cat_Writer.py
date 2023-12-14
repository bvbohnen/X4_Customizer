'''
Support for packing files to a cat/dat pair.
See Cat_Reader for details on catalog files.

Note on newlines:
    X Tools produced dat files observed to use windows line feeds (\r\n),
    perhaps just being a direct encoding of the input files. This can be dealt
    with in the Game_File Get_Binary methods.
    The cat files themselves use unix newlines (\n), so the code below
    will match such behavior.
    (The above did not seem to matter in testing, but was switched to
    matching ego results as a potentential fix for some users complaining
    about the extension not loading.)
    X Tools does not add newlines between text files.
'''
from ..Documentation import Doc_Category_Default
_doc_category = Doc_Category_Default('File_Manager')

import gzip
import time
import hashlib
from pathlib import Path
from .File_Types import Game_File, Signature_File, Machine_Code_File
from .File_Types import Generate_Signatures
from .Cat_Reader import Get_Hash_String
from ..Common import Print


class Cat_Writer:
    '''
    Support class for collecting modified files into a single catalog.
    Initial functionality will not gzip the files.

    Attributes:
    * cat_path
      - Path, the full path to the cat file.
    * dat_path
      - Path, the full path to corresponding dat file.
      - Set automatically to match the cat_path index.
    * game_files
      - List of Game_File objects to be written.
    '''
    def __init__(self, cat_path):
        # Ensure this is a Path.
        self.cat_path = Path(cat_path)
        self.dat_path = self.cat_path.with_suffix('.dat')
        self.game_files = []
        return


    def Add_File(self, game_file):
        '''
        Add a Game_File to be recorded into the catalog.
        Machine_Code_File will be rejected.
        '''
        assert isinstance(game_file, Game_File)
        if isinstance(game_file, Machine_Code_File):
            Print('Cat_Writer ignoring Machine_Code_File {}'.format(game_file.virtual_path))
            return
        self.game_files.append(game_file)


    def Write(self, generate_sigs = False, separate_sigs = False):
        '''
        Write the contents to a cat/dat file pair.
        Any existing files will be overwritten.

        * generate_sigs
          - Bool, if True then dummy signature files will be created.
        * separate_sigs
          - Bool, if True then any signatures will be moved to a second
            cat/dat pair suffixed with .sig. This may result in an
            empty dat.
        '''
        # Handle signature generation first.
        game_files = self.game_files
        if generate_sigs:
            game_files += Generate_Signatures(self.game_files)


        # Requires up to two passes, if separating sigs.
        if separate_sigs:
            modes = ['std','sig']
        else:
            modes = ['all']

        for mode in modes:

            # Cat contents will be kept as a list of strings.
            # Dat contents will be running binary.
            cat_lines = []
            dat_binary = bytearray()

            # Get the current time since epoch, as an integer, then
            #  swap to a string (normal base 10).
            timestamp = str(int(time.time()))

            # Collect info from the files.
            # Note: this may generate nothing if no game files were added,
            #  eg. when making dummy catalogs.
            for game_file in self.game_files:

                # If just wanting standard or sig files, filter the
                # others out.
                if mode == 'std' and isinstance(game_file, Signature_File):
                    continue
                if mode == 'sig' and not isinstance(game_file, Signature_File):
                    continue

                # Get the binary data; any text should be utf-8.
                this_binary = game_file.Get_Binary(for_cat = True)
                x = bytes(this_binary)

                # Append to the existing dat binary.
                dat_binary += this_binary

                # Get the hash.
                hash_str = Get_Hash_String(this_binary)

                # Add the cat entry line.
                cat_lines.append( ' '.join([
                    game_file.virtual_path,
                    str(len(this_binary)),
                    timestamp,
                    hash_str,
                    ]))


            # The cat needs to end in a newline.
            cat_lines.append('')

            # Convert the cat to utf-8 binary.
            # Note: x4 cats appear to use unix newlines, which this bytes()
            # method will match.
            cat_str = '\n'.join(cat_lines)
            cat_binary = bytes(cat_str, encoding = 'utf-8')
        
            # Append a .sig to the names for signature files.
            if mode == 'sig':
                cat_path = self.cat_path.parent / (self.cat_path.name + '.sig')
                dat_path = self.dat_path.parent / (self.dat_path.name + '.sig')
            else:
                cat_path = self.cat_path
                dat_path = self.dat_path

            # Write the data out.
            with open(cat_path, 'wb') as file:
                file.write(cat_binary)
            with open(dat_path, 'wb') as file:
                file.write(dat_binary)

        return

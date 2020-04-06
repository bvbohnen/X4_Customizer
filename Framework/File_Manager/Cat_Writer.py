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
import gzip
import time
import hashlib
from pathlib import Path
from . import File_Types
from .Cat_Reader import Get_Hash_String


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
        '''
        assert isinstance(game_file, File_Types.Game_File)
        self.game_files.append(game_file)


    def Write(self):
        '''
        Write the contents to a cat/dat file pair.
        Any existing files will be overwritten.
        '''
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
        
        # Write the data out.
        with open(self.cat_path, 'wb') as file:
            file.write(cat_binary)
        with open(self.dat_path, 'wb') as file:
            file.write(dat_binary)

        return

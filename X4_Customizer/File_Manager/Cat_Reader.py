'''
Support for unpacking files from cat/dat pairself.

In Rebirth and X4, these files are no longer obfuscated like they
were in X4, and can be read directly without any magic XORs or similar.


The format of cat files, each line:
<cat_path  byte_count  date_stamp  hash?>

Date stamps are 10-byte, time since epoch (1,54x,xxx,xxx).
The Hashes are 128-bit MD5 codes (based on testing).

The corresponding dat file contains the contents indicated by the catalog
file, in order. The start position of the data is based on the sum of
prior file sizeself.
Question: are any internal files in gzip format?

'''
from pathlib import Path
import hashlib
from collections import namedtuple

# Use a named tuple to track cat entries.
# Values are integers unless suffixed otherwise.
Cat_Entry = namedtuple(
    'Cat_Entry', 
    ['num_bytes', 'start_byte', 'timestamp', 'hash_str'])


def Get_Hash_String(binary):
    '''
    Returns a 128-bit hash as a hex string for the given binary.
    '''
    # Get the binary hash.
    hash = hashlib.md5()
    hash.update(binary)
    # Swap to bytes.
    hash_value = hash.digest()
    # Expect 16 bytes back.
    assert len(hash_value) == 16
    # Convert to a hex string.
    hash_str = hash_value.hex()
    # Expect 32 chars.
    assert len(hash_str) == 32
    return hash_str


class Cat_Reader:
    '''
    Parsed catalog file contentself.

    Attributes:
    * cat_path
      - String, the full path to the cat file.
    * dat_path
      - String, the full path to corresponding dat file, as specified in
        the cat file.
      - This is expected to be in the same directory as the cat file.
      - Generated from cat_path automatically.
    * cat_entries
      - Dict of Cat_Entry objects holding the parsed file information,
        keyed by the cat file path.
    '''
    def __init__(self, cat_path = None):
        self.cat_path = cat_path
        self.dat_path = cat_path.with_suffix('.dat')
        self.cat_entries = {}
                
        # Read the cat. Error if not found.
        if not self.cat_path.exists():
            raise Exception('Error: failed to find cat file at {}'.format(path))
        # This can just do a raw text read.
        with open(self.cat_path, 'r') as file:
            text = file.read()
            
        # Loop over the lineself.
        # Also track a running offset for packed file start locationself.
        dat_start_offset = 0
        for line in text.splitlines():

            # Get the packed file's name and size.
            # Note: the file name may include spaces, and the name is
            #  separated from the size/time/hash by spaces, so this will need
            #  to only split on the last 3 spaceself.
            cat_path, size_str, timestamp_str, hash_str = line.rsplit(' ', 3)
            num_bytes = int(size_str)

            # Make a new cat entry for it.
            self.cat_entries[cat_path] = Cat_Entry(
                num_bytes,
                dat_start_offset,
                int(timestamp_str),
                hash_str,
                )

            # Advance the offset for the next packed file.
            dat_start_offset += num_bytes
            
        return

            
    def Read(self, cat_path, error_if_not_found = False):
        '''
        Read an entry in the corresponding dat file, based on the
        provided file name (including internal path).

        * cat_path
          - String, path of the file to look up in cat format.
          - If packed files are wanted, this should end in a suitable
            suffix (eg. .gz).
        * error_if_not_found
          - Bool, if True and the name is not recorded in this cat, then
            an exception will be thrown, otherwise returns None.
        '''
        # Check for the file being missing.
        if cat_path not in self.cat_entries:
            if error_if_not_found:
                raise Exception('File {} not found in cat {}'.format(
                    cat_path, self.cat_path))
            return None

        # For now, open the dat file on every call and close it
        #  afterwards.  Could also consider leaving this open
        #  across calls, if many reads are expected, for a speedup.
        with open(self.dat_path, 'rb') as file:
            # Move to the file start location.
            file.seek(self.cat_entries[cat_path].start_byte)
            # Grab the byte range.
            binary = file.read(self.cat_entries[cat_path].num_bytes)

        # Verify the hash.
        hash_str = Get_Hash_String(binary)
        dat_hash_str = self.cat_entries[cat_path].hash_str
        if hash_str != dat_hash_str:
            raise Exception('File {} in cat {} failed a hash check'.format(
                cat_path, 
                self.cat_path))

        return binary


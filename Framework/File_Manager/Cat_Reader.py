'''
Support for unpacking files from cat/dat pairself.

In Rebirth and X4, these files are no longer obfuscated like they
were in X2/X3, and can be read directly without any magic XORs or similar.


The format of cat files, each line:
<cat_path  byte_count  date_stamp  hash>

Date stamps are 10-byte, time since epoch (1,54x,xxx,xxx).
The Hashes are 128-bit MD5 codes, mostly.
    Note: egosoft catalogs are buggy regarding empty files, which have
    a hash of 0 in the cat even though md5 should return a hash
    of d41d8cd98f00b204e9800998ecf8427e for empty input.

The corresponding dat file contains the contents indicated by the catalog
file, in order. The start position of the data is based on the sum of
prior file sizes.
Question: are any internal files in gzip format?

Note on case:
    X4 appears to support case-insensitive matching, though the original
    catalogs do sometimes have uppercase characters in paths.
    Mods may use lowercase paths.
    Ideally, original case can be kept for cat unpacking or similar,
    but other tools may force paths into lowercase when
    extracting files that modders worked on.
    However, working in pure lowercase is simpler to maintain.
    Here, paths will be handled in lower case generally, but the original
    case will be preserved for lookup when needed.
'''
from ..Documentation import Doc_Category_Default
_doc_category = Doc_Category_Default('File_Manager')

from pathlib import Path
import hashlib
from collections import namedtuple

from ..Common import Cat_Hash_Exception, Settings, Print

# Use a named tuple to track cat entries.
# Values are integers unless suffixed otherwise.
Cat_Entry = namedtuple(
    'Cat_Entry', 
    ['cat_path','num_bytes', 'start_byte', 'timestamp', 'hash_str'])


def Get_Hash_String(binary):
    '''
    Returns a 128-bit md5 hash as a hex string for the given binary.
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
    Parsed catalog file contents.

    Attributes:
    * cat_path
      - String, the full path to the cat file.
      - TODO: track ext_ vs subst_ cats in a convenient way.
    * dat_path
      - String, the full path to corresponding dat file, as specified in
        the cat file.
      - This is expected to be in the same directory as the cat file.
      - Generated from cat_path automatically.
    * cat_entries
      - Dict of Cat_Entry objects holding the parsed file information,
        keyed by the virtual path (lower case).
      - A Cat_Entry itself will have an original case path.
    '''
    def __init__(self, cat_path = None):
        self.cat_path = cat_path
        self.dat_path = cat_path.with_suffix('.dat')
        self.cat_entries = {}

        # Read the cat. Error if not found.
        if not self.cat_path.exists():
            raise AssertionError('Error: failed to find cat file at {}'.format(path))
        # This can just do a raw text read.
        with open(self.cat_path, 'r') as file:
            text = file.read()
            
        # Loop over the lines.
        # Also track a running offset for packed file start locations.
        dat_start_offset = 0
        for line in text.splitlines():

            # Get the packed file's name and size.
            # Note: the file name may include spaces, and the name is
            #  separated from the size/time/hash by spaces, so this will need
            #  to only split on the last 3 spaces.
            cat_path, size_str, timestamp_str, hash_str = line.rsplit(' ', 3)
            num_bytes = int(size_str)

            # Make a new cat entry for it.
            self.cat_entries[cat_path.lower()] = Cat_Entry(
                cat_path,
                num_bytes,
                dat_start_offset,
                int(timestamp_str),
                hash_str,
                )

            # Advance the offset for the next packed file.
            dat_start_offset += num_bytes
            
        return


    def Get_File_Names(self):
        '''
        Returns a list of virtual names of files in this catalog,
        in sorted order.
        '''
        return sorted(self.cat_entries.keys())


    def Get_Cat_Entries(self):
        '''
        Returns a dict of Cat_Entry objects, keyed by cat_path
        (expected to be the same as virtual_path).
        '''
        return self.cat_entries

            
    def Read(self, virtual_path, error_if_not_found = False, allow_md5_error = False):
        '''
        Read an entry in the corresponding dat file, based on the
        provided file name (including internal path).

        * virtual_path
          - String, path of the file to look up in cat format.
        * error_if_not_found
          - Bool, if True and the name is not recorded in this cat, then
            an exception will be thrown, otherwise returns None.
        * allow_md5_error
          - Bool, if True then the md5 check will be suppressed and
            errors allowed. May still print a warning message.
        '''
        # Ensure lower case path.
        virtual_path = virtual_path.lower()

        # Check for the file being missing.
        if virtual_path not in self.cat_entries:
            if error_if_not_found:
                raise AssertionError('File {} not found in cat {}'.format(
                    virtual_path, self.cat_path))
            return None

        # For now, open the dat file on every call and close it
        #  afterwards.  Could also consider leaving this open
        #  across calls, if many reads are expected, for a speedup.
        with open(self.dat_path, 'rb') as file:
            # Move to the file start location.
            file.seek(self.cat_entries[virtual_path].start_byte)
            # Grab the byte range.
            binary = file.read(self.cat_entries[virtual_path].num_bytes)


        # Verify the hash.
        binary_hash_str = Get_Hash_String(binary)
        cat_hash_str = self.cat_entries[virtual_path].hash_str

        # Note: egosoft cats are buggy and can have a 0 for the hash
        # of empty files, so also check that, but keep the normal
        # check incase proper empty file hashes show up sometimes.
        if (cat_hash_str == binary_hash_str):
            # Hash match.
            pass
        elif not binary and cat_hash_str == '00000000000000000000000000000000':
            # Alt hash match for empty file.
            pass
        else:
            # Handle the error message.
            message = 'File {} in cat {} failed the md5 hash check'.format(
                    virtual_path, self.cat_path)
            # Prevent the exception based on Settings or the input arg.
            if not Settings.allow_cat_md5_errors and not allow_md5_error:
                raise Cat_Hash_Exception(message)
            elif Settings.verbose:
                Print(message)

        return binary


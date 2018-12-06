'''
Support for log files, including generic messages.
'''
import os
import json
from ..Common.Settings import Settings
import hashlib

# General messages printout by transforms or during runtime.
Message_file = None
def Write_Summary_Line(line, no_newline = False):
    '''
    Write a line to the summary file.
    A newline is inserted automatically if no_newline == False.
    '''
    global Message_file
    # Open the file if needed.
    if Message_file == None:
        Message_file = open(Settings.Get_Message_File_Path(), 'w')
    Message_file.write(line + '\n' if not no_newline else '')
    

class Log:
    '''
    Container for logged information, from a prior run or to be
    saved at the end of the current run. Separate logs should be
    used for each.

    Attributes:
    * version
      - String, version of the customizer.
    * file_paths_written_hash_dict
      - Dict, keyed by path to files written out by the customizer, holding
        the hash of the file data.
      - Paths are absolute, but should be relative when stored and reloaded
        to be consistent if the installation folder is moved.
      - When from an older run, these files should be removed or overwritten
        by the newer run, and should be ignored when looking for sources.
      - May need pruning for files whose existing hash doesn't match
        the stored hash in the prior run (indicating the file was
        overwritten externally).
    * file_paths_renamed_dict
      - Dict of strings, paths to files renamed by the customizer, keyed
        by the original path and holding the new path.
      - Generally, these will be suffixed with '.x4c.bak' or similar,
        to sideline non-customizer files to make room for the
        customized versions.
      - When from an older run, these files should be considered as sources,
        and should be renamed back to their base version by the newer run
        if it is otherwise not writing out a matching customized file.
    '''
    def __init__(self):
        # Always default to the current highest version.
        # When loading an older log, it can overwrite this.
        import Change_Log
        self.version = Change_Log.Get_Version()
        self.file_paths_written_hash_dict = {}
        self.file_paths_renamed_dict = {}
        
    def System_Path_to_Relative_Path(self, path):
        '''
        Convert a full system path to a standardized relative path.
        The standard will be relative to the x4 base folder.
        '''
        # Note: this might have to path upwards, which pathlib can't handle,
        #  so use os relpath.
        return os.path.relpath(path, Settings.Get_X4_Folder())
    

    def Relative_Path_to_System_Path(self, path):
        '''
        Convert a standardized relative path to a full system path.
        The standard will be relative to the x4 base folder.
        '''
        # Error if the path is already absolute.
        assert not os.path.isabs(path)
        return os.path.join(Settings.Get_X4_Folder(), path)

    def Load(self):
        '''
        Load information from an existing log json file.
        If a log file is not found, nothing will be changed.
        '''
        path = Settings.Get_Log_File_Path()
        # If the file doesn't exist, return early.
        if not os.path.exists(path):
            return

        with open(path, 'r') as file:
            log_dict = json.load(file)

        #-Removed; special handling applies instead to deal with
        # relative paths.
        ## Load the fields into this object's attributes.
        #for field, value in log_dict.items():
        #    setattr(self, field, value)

        # For pre-3.4.1 support, cast version to a string from float.
        self.version = str(log_dict['version'])
        # Handle hashes.
        for relative_path, hash in log_dict[
            'file_paths_written_hash_dict'].items():

            # Convert to an absolute path and store.
            self.file_paths_written_hash_dict[
                self.Relative_Path_to_System_Path(relative_path)] = hash

        # Handle renamings.
        for source_relative_path, dest_relative_path in log_dict[
            'file_paths_renamed_dict'].items():
            # Convert both to absolute and store.
            self.file_paths_renamed_dict[
                    self.Relative_Path_to_System_Path(source_relative_path)
                ] = self.Relative_Path_to_System_Path(dest_relative_path)
            

        # Check for hash mismatches in the prior written files.
        hash_mismatched_file_paths = []
        for file_path, hash in self.file_paths_written_hash_dict.items():
            # If the old hash is None, something weird happened and
            #  the file was not found after being written; this may
            #  come from test code that disabled writeouts, and this
            #  can be ignored.

            # Get an updated hash.
            new_hash = self.Get_File_Hash(file_path)

            # If the file is no longer found, hash will be None and this
            #  should be treated as a mismatch (though it probably
            #  doesn't matter much).
            if new_hash == None or new_hash != hash:
                hash_mismatched_file_paths.append(file_path)

        # Delete these paths from the dict.
        for path in hash_mismatched_file_paths:
            del(self.file_paths_written_hash_dict[path])
            
        # TODO: think about how to detect cases where a generated
        #  file is the same as a user written file, eg. if the source
        #  was not actively changed by a transform that loaded it, and
        #  the user copied from the same source intending to maybe
        #  modify it for their own use; cleanup in this case would end
        #  up deleting the file inadvertently.
        # Maybe something can be done with file attributes, or similar?
        # Otherwise, maybe try to find a standard way to add a benign
        #  comment to all generated files, though format will depend
        #  on file type; opening and checking for this comment could
        #  be sufficient.

        return


    def Store(self):
        '''
        Store the current log information to a log json file.
        Overwrites any prior file.
        '''
        #-Removed; special handling converts to relative paths.
        ## Pack a dict with any class attributes, skipping built-in stuff.
        #log_dict = {}
        #for field in vars(self):
        #    if field.startswith('_'):
        #        continue
        #    log_dict[field] = getattr(self, field)

        log_dict = {}
        log_dict['version'] = self.version
        log_dict['file_paths_written_hash_dict'] = {}
        log_dict['file_paths_renamed_dict'] = {}

        # Handle hashes.
        for abs_path, hash in self.file_paths_written_hash_dict.items():

            # Convert to relative path and store.
            log_dict['file_paths_written_hash_dict'][
                self.System_Path_to_Relative_Path(abs_path)] = hash

        # Handle renamings.
        for source_abs_path, dest_abs_path in self.file_paths_renamed_dict.items():
            # Convert both to relative and store.
            log_dict['file_paths_renamed_dict'][
                    self.System_Path_to_Relative_Path(source_abs_path)
                ] = self.System_Path_to_Relative_Path(dest_abs_path)
            
        # Write the json, with indents for readability.
        with open(Settings.Get_Log_File_Path(), 'w') as file:
            json.dump(log_dict, file, indent = 2)


    def Get_File_Hash(self, path):
        '''
        Return a hash for a file on the given path.
        If the file does not exist, returns None.
        '''
        if not os.path.exists(path):
            return None
        # Can use sha256, which seems to be the current default over
        #  ones like md5.        
        hash = hashlib.sha256()
        # Presumably manually buffering a file will help with hashing
        #  it, but can keep things simple for now and do a full read.
        with open(path, 'rb') as file:
            hash.update(file.read())
        return hash.hexdigest()


    def Record_File_Path_Written(self, path):
        '''
        Record the path of a file written by the customizer, along with
        a hash of the contents. This should be called after the file
        has been written, so the correct hash is computed.
        '''
        self.file_paths_written_hash_dict[path] = self.Get_File_Hash(path)


    def Record_File_Path_Renamed(self, source_path, dest_path):
        '''
        Record the paths of a renamed file, from source to dest.
        '''
        self.file_paths_renamed_dict[source_path] = dest_path


    def Get_File_Paths_From_Last_Run(self):
        '''
        Returns a list of paths to files which were written on the
         last run, and were not overwritten externally in the
         meantime.
        '''
        return self.file_paths_written_hash_dict.keys()


    def File_Is_From_Last_Run(self, path):
        '''
        Checks if the given file was written on the prior run, according to
         the log and hash check.
        Returns a bool.
        '''
        # If the path is not in the dict, return False.
        if path not in self.file_paths_written_hash_dict:
            return False
        return True


    def Get_Renamed_File_Path(self, path):
        '''
        Returns the path to a renamed version of a file, if the given
         path was renamed on a prior run.
        The renamed file should be safe to act as a source, as it did
         not come from the customizer.
        Returns None if the file was not renamed.
        '''
        if path not in self.file_paths_renamed_dict:
            return None
        return self.file_paths_renamed_dict[path]


    def Get_Renamed_File_Paths(self):
        '''
        Returns a list of tuples of (original file path, renamed path),
        for files that were renamed on a prior run.
        '''
        # Reform the dict keys and values into a list of tuples.
        # Original name (key) goes first.
        return [(x,y) for x,y in self.file_paths_renamed_dict.items()]

        
# Log files, from an old run and for the current run.
Log_Old = Log()
Log_New = Log()

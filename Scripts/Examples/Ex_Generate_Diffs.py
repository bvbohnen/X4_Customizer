'''
Example of creating diff files from pairs of matched input files, where
one file is the original, the other the modified.

Note: these examples don't run as-is since example xml files aren't
included. Change paths as needed.
'''
from Plugins import *

# Example assumes xml files are in a "work" folder.
source_folder = r'C:\Steam\SteamApps\common\X4 Foundations\work'

# Single file example.
Generate_Diff(
    original_file_path = source_folder + r'/original.xml',
    modified_file_path = source_folder + r'/modified.xml',
    output_file_path   = source_folder + r'/patch.xml',
    )

# Multi-file example; diffs matching files in the directories.
Generate_Diffs(
    original_dir_path = source_folder + r'/orig_files',
    modified_dir_path = source_folder + r'/mod_files',
    output_dir_path   = source_folder + r'/diff_files',
    )
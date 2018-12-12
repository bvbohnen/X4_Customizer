'''
Script for packing loose files into a catalog file.
'''

from pathlib import Path
from Plugins import Cat_Pack
from Plugins import Settings

# Pick where to grab files from.
# Could also call this script from that directory and use relative
# paths for the cat file names.
dir_path = Path(r'C:\Steam\SteamApps\common\X4 Foundations\extensions\test_mod')

# Optional wildcard pattern to use for matching.
include_pattern = '*.xml'
exclude_pattern = None

# Name of the cat file.
# For extensions, use prefix 'ext_' for patching game files, or
# prefix 'subst_' for overwriting game files.
cat_name = 'ext_01.cat'

Cat_Pack(
    source_dir_path = dir_path,
    dest_cat_path   = dir_path / cat_name,
    include_pattern = include_pattern,
    exclude_pattern = exclude_pattern
    )

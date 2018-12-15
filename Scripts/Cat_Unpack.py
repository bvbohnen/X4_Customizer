'''
Script for unpacking catalog files.
'''

from pathlib import Path
from Plugins import Cat_Unpack
from Plugins import Settings

# Pick where to grab cats from.
# Could also call this script from that directory and use relative
#  paths for the cat file names.
# Append the name of a cat file if wanting to unpack just one.
cat_dir = Path(r'C:\Steam\SteamApps\common\X4 Foundations')

# Pick the output folder. This script places it under the cat_dir.
dest_dir_path = 'extracted'

# Optional wildcard pattern to use for matching.
include_pattern = ['*.xml','*.xsd','*.lua'] #,'*.xpl']
exclude_pattern = None

# Call the unpacker.
Cat_Unpack(
    source_cat_path = cat_dir,
    dest_dir_path   = cat_dir / dest_dir_path,
    is_extension    = False,
    include_pattern = include_pattern,
    exclude_pattern = exclude_pattern
    )

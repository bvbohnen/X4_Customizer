'''
Example of unpacking an arbitrary directory of "ext_" cat/dat files.
This can also be done from the command line using the Cat_Unpack bat file.
'''
from Plugins import *

# Unpack the main game files.
Cat_Unpack(
    # Select location to unpack. This is just the base X4 folder.
    source_cat_path  = r'C:\Steam\SteamApps\common\X4 Foundations',
    # Select where to place the output.
    dest_dir_path    = r'C:\Steam\SteamApps\common\X4 Foundations\extracted',
    # Pick files to include. This default covers the various text files.
    include_pattern  = ['*.xml','*.xsd','*.lua','*.html','*.css','*.js','*.xsl']
    )

# Also unpack the split dlc.
Cat_Unpack(
    source_cat_path  = r'C:\Steam\SteamApps\common\X4 Foundations\extensions\ego_dlc_split',
    dest_dir_path    = r'C:\Steam\SteamApps\common\X4 Foundations\extracted\extensions\ego_dlc_split',
    include_pattern  = ['*.xml','*.xsd','*.lua','*.html','*.css','*.js','*.xsl']
    )
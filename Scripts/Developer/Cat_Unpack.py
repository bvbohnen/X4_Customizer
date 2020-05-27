
from Plugins import *

pattern = [ '*.xml','*.xsd','*.lua','*.html','*.css','*.js','*.xsl',
            # Shader related.
            '*.ogl','*.v','*.vh','*.vf','*.tcs','*.tes','*.f','*.h','*.fh']

# Unpack the main game files.
Cat_Unpack(
    source_cat_path  = r'C:\Steam\SteamApps\common\X4 Foundations',
    dest_dir_path    = r'C:\Steam\SteamApps\common\X4 Foundations\extracted',
    include_pattern  = pattern,
    )

# Also unpack the split dlc.
Cat_Unpack(
    source_cat_path  = r'C:\Steam\SteamApps\common\X4 Foundations\extensions\ego_dlc_split',
    dest_dir_path    = r'C:\Steam\SteamApps\common\X4 Foundations\extracted\extensions\ego_dlc_split',
    include_pattern  = pattern,
    )
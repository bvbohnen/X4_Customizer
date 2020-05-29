'''
Load files using the file system, with automated patch application from
enabled extensions, then save the patched xml for easier viewing.
'''
from Plugins import *
from Framework import Load_Files

# Pick a location to save to.
# This will go to X4root/extracted_patched
folder = Settings.Get_X4_Folder() / 'extracted_patched'

game_files = []

# Pick a set of file name patterns.
# This example includes all library xml files.
for pattern in [
    'libraries/*.xml',
    ]:
    game_files += Load_Files(pattern)

# This code pulls the file binary data (not diff encoded), and writes to
# the target directory.
for game_file in game_files:
    binary = game_file.Get_Binary(no_diff = True)
    file_path = folder / game_file.virtual_path
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents = True)
    with open(file_path, 'wb') as file:
        file.write(binary)


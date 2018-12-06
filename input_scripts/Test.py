'''
Place to test individual transforms.
'''

# Import all transform functions.
import X4_Customizer
from X4_Customizer import *

Set_Path(
    path_to_x4_folder = r'C:\Steam\SteamApps\common\X4 Foundations',
)

Adjust_Job_Count()

## Test: open up a cat file, the one with text pages.
#cat09 = X4_Customizer.File_Manager.Cat_Reader.Cat_Reader(
#    Settings.path_to_x4_folder / '09.cat')
#
## Read the files from it.
#t44 = cat09.Read('t/0001-L044.xml')
#
## Now try out the source reader.
#reader = X4_Customizer.File_Manager.Source_Reader.Source_Reader
#reader.Init()
#t44_game_file = reader.Read('t/0001-L044.xml')
#jobs_game_file = reader.Read('libraries/jobs.xml')
#
## Write to a new cat file.
#binary = t44_game_file.Get_Binary()
#cat_dir = Settings.path_to_x4_folder / 'extensions' / 'X4_Customizer'
#if not cat_dir.exists():
#    cat_dir.mkdir(parents = True)
#
#cat_writer = X4_Customizer.File_Manager.Cat_Writer.Cat_Writer(
#    cat_path = cat_dir / 'ext_01.cat')
#cat_writer.Add_File(t44_game_file)
#cat_writer.Write()


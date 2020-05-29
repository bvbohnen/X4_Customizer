'''
Holds modules with most of the file handling framework.
'''
from .File_Types import *
from .File_System import File_System
from . import XML_Diff
from . import Extension_Finder
# Pull out the most common file system function for transforms to use.
Load_File = File_System.Load_File
Load_Files = File_System.Load_Files
Get_Indexed_File = File_System.Get_Indexed_File
Get_All_Indexed_Files = File_System.Get_All_Indexed_Files
Get_Asset_Files_By_Class = File_System.Get_Asset_Files_By_Class

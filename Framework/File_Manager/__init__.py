'''
Holds modules with most of the file handling framework.
'''
from .File_Types import XML_File, Misc_File
from .File_System import File_System
from . import XML_Diff
from . import Extension_Finder
# Pull out the most common file system function for transforms to use.
Load_File = File_System.Load_File

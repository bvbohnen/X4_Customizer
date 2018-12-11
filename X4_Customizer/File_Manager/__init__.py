'''
Holds modules with most of the file handling framework.
'''
from .File_Types import XML_File, Misc_File
from .File_System import File_System
# Pull out the most common file system function for transforms to use.
Load_File = File_System.Load_File

# Support easy import of some key functions used by transforms.
#from .Misc import Cleanup
#from .Misc import Load_File
#from .Misc import Write_Files
#from .Misc import Copy_File
#from .Misc import Add_File

# Allow access indirectly to some modules.
#from . import Misc
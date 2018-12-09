'''
Holds modules with most of the file handling framework.
'''
# Support easy import of some key functions used by transforms.
from .Misc import Cleanup
from .Misc import Load_File
from .Misc import Write_Files
from .Misc import Copy_File
from .Misc import Add_File
from .File_Types import *

# Allow access indirectly to some modules.
from . import Misc
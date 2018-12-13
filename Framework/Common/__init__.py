'''
Holds modules that will be commonly imported by transforms
and other parts of the framework.
'''
# Import exceptions early, due to some dependency issues.
from .Exceptions import File_Missing_Exception
from .Exceptions import Obj_Patch_Exception
from .Exceptions import Text_Patch_Exception
from .Exceptions import Gzip_Exception
from .Exceptions import XML_Patch_Exception
from .Exceptions import Cat_Hash_Exception

from . import Change_Log
from .Settings import Settings
from .Logs import Plugin_Log
from .Logs import Customizer_Log_class

from .Plugin_Manager import Analysis_Wrapper
from .Plugin_Manager import Transform_Wrapper
from .Plugin_Manager import Utility_Wrapper
from .Plugin_Manager import Plugin_Was_Run_Before


# Set the directory where the package resides, which is one
#  level up from here.
# Note: pyinstaller can change directories around, and needs special
#  handling.
# See https://stackoverflow.com/questions/404744/determining-application-path-in-a-python-exe-generated-by-pyinstaller
# In short, a 'frozen' attribute is added to sys by pyinstaller,
#  which can be checked to know if this is running in post-installer mode,
#  in which case _MEIPASS will hold the app base folder.
# TODO: check if this is still needed in the latest pyinstaller.
import sys as _sys
from pathlib import Path as _Path
if getattr(_sys, 'frozen', False):
    # This appears to be the launch folder, so no extra pathing needed.
    framework_path = _Path(_sys._MEIPASS)
else:
    framework_path = _Path(__file__).resolve().parent.parent


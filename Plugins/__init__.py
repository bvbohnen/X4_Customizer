'''
This package contains modules imported at run time.
Transforms, utilities, and other source code can be edited here without
requiring a recompile, for users who do not have python installed.

Note: import packages are limited to those included in the compilation
when running from the exe instead of python source code.

Custom user transforms and other modules can also be dropped in here.
TODO: think of how this would look.
'''

# Make all plugin functions accessible directly and indirectly.
from . import Analyses
from . import Transforms
from . import Utilities
from .Analyses   import *
from .Transforms import *
from .Utilities  import *

# Make the framework Setting available to anyone importing this,
#  for convenience.
from Framework import Settings

# The gui is not really a plugin, but there isn't a better place
# to put it, since the layout .ui file has somewhat difficult
# to modify import paths that only work well with raw python
# input. Also, this gives a nice folder to put the .ui file in.
from . import GUI


def _Init():
    '''
    One-time setup, not to be part of * imports.
    '''
    # Set the import path so the Framework is findable.
    from pathlib import Path
    import sys
    parent_dir = str(Path(__file__).resolve().parent.parent)
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
_Init()
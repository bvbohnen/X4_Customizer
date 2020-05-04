'''
This package holds documentation generation functions.
These will analyze the game files, after all extensions are processed,
pick out fields of interest, and write them out (in some format, eg. html).
'''

from .Print_Object_Stats import *

# Import of the builder functions to get them set up.
# This isn't really meant to go up to a higher level.
from . import Live_Editor_Builders as _Live_Editor_Builders
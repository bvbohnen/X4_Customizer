'''
Subpackage holding functionality for building live editable tables
of selectd data items.
'''
# TODO: split up/rename the Support module.
# In general, users should only be accessing the Live_Editor static
# object itself, and not the other support code.
from .Support import Live_Editor

# Make sure other modules are imported, so they can register
# their build functions with the editor.
from . import Weapons
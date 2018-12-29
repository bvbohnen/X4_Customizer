'''
Build functions for the Live Editor.
These either set up categorized groups of Edit_Objects, or
the Edit_Tree_Views for displaying them.

Primarily for use in the GUI and printouts.
'''

# Generally, this subpackage shouldn't have its contents imported
# to any user, though it will have a fluff import by Plugins to
# load the build functions.
__all__ = []

# Do all live editor hookups here, to keep them organized somewhat.
from .Wares import _Build_Ware_Objects
from .Wares import _Build_Ware_Object_Tree_View
from .Weapons import _Build_Bullet_Objects
from .Weapons import _Build_Weapon_Objects
from .Weapons import _Build_Weapon_Object_Tree_View
from Framework import Live_Editor

Live_Editor.Record_Category_Objects_Builder('wares', _Build_Ware_Objects)
Live_Editor.Record_Category_Objects_Builder('bullets', _Build_Bullet_Objects)
Live_Editor.Record_Category_Objects_Builder('weapons', _Build_Weapon_Objects)

Live_Editor.Record_Tree_View_Builder('weapons', _Build_Weapon_Object_Tree_View)
Live_Editor.Record_Tree_View_Builder('wares', _Build_Ware_Object_Tree_View)
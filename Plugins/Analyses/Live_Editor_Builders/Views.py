'''
Object tree view builder functions.
These generally map to gui display tabs.
'''

from Framework.Live_Editor_Components import *

def Build_Object_Tree_View(
        name,
        display_name,
        object_categories,
        label_item,
        flat = False,
        subcategory_func = None,
    ):
    '''
    Generic builder for a tree view of select objects, with no
    extra sorting branches beyond object category.

    * name
      - String, name for this tree to use in live editor lookups.
    * display_name
      - String, name to use for this tree in name displays, such as
        gui tabs or when nested under another tree later.
    * object_categories
      - Strings, categories of objects to look up in the live editor.
      - If multiple given, they will be split into branches.
    * flat
      - Bool, if True and multiple object_categories are present,
        they will be collected together and not split into branches.
    * label_item
      - Name of an item in the objects which will provide the tree label.
      - Often 'name', though could be other terms.
    * subcategory_func
      - Optional function which will take the object and return 1 or more
        strings to use as categories.
      - These categories will be placed underneath the object_categories.
    '''
    object_tree_view = Edit_Tree_View(name, display_name)

    # Always flat with one category.
    if len(object_categories) == 1:
        flat = True

    for category in object_categories:
        objects_list = Live_Editor.Get_Category_Objects(category)

        for object in objects_list:
            name = object.Get_Item(label_item).Get_Value('current')

            # Get categorization, if any.
            categories = []
            if not flat:
                categories.append(category)
            if subcategory_func != None:
                 subcats = subcategory_func(object)
                 # If only one subcat was returned, list pack it,
                 # to avoid a string getting every letter treated
                 # as a subcat level.
                 if not isinstance(subcats, (tuple, list)):
                     subcats = [subcats]
                 categories += subcats

            # Apply the object and categories.
            object_tree_view.Add_Object(name, object, *categories)
                
    # Sort the tree in place when done.
    object_tree_view.Sort_Branches()

    # Apply default label filtering.
    object_tree_view.Apply_Filtered_Labels()
    return object_tree_view



@Live_Editor_Tree_View_Builder('bullets')
def _Build_Bullet_Object_Tree_View():
    '''
    Constructs an Edit_Tree_View object for use in displaying
    bullet data.
    '''
    def Subcat_func(object):
        'Set up sub categories.'
        # Weapon class (separates missiles, bombs, bullets, etc.).
        wclass = object.Get_Item_Value('macro_class')
        return wclass

    return Build_Object_Tree_View(
        name              = 'bullets',
        display_name      = 'Bullets',
        object_categories = ['bullets'],
        label_item        = 'bullet_codename',
        subcategory_func  = Subcat_func,    
    )


@Live_Editor_Tree_View_Builder('weapons')
def _Build_Weapon_Object_Tree_View():
    '''
    Constructs an Edit_Tree_View object for use in displaying
    weapon data.
    '''
    def Subcat_func(object):
        'Set up sub categories.'
        # Weapon class (separates missiles, bombs, turrets, etc.).
        wclass = object.Get_Item_Value('macro_class')
        # Weapon size.
        # Size needs to be found in the tags.
        tags = object.Get_Item_Value('connection_tags').split()
        for size in ['small','medium','large','spacesuit']:
            if size in tags:
                break
            size = '?'
        return wclass, size

    return Build_Object_Tree_View(
        name              = 'weapons',
        display_name      = 'Weapons',
        object_categories = ['weapons'],
        label_item        = 'name',
        subcategory_func  = Subcat_func,    
    )



@Live_Editor_Tree_View_Builder('ships')
def _Build_Ship_Object_Tree_View():
    '''
    Constructs an Edit_Tree_View object for use in displaying
    ship data.
    '''
    def Subcat_func(object):
        'Set up sub categories.'
        # Ship class captures size.
        sclass = object.Get_Item_Value('macro_class')
        # Purpose is fight/trade
        purpose = object.Get_Item_Value('purpose_primary', default = 'purposeless')
        # Type is bomber/etc.
        ship_type = object.Get_Item_Value('ship_type', default = 'typeless')
        return purpose, sclass, ship_type

    return Build_Object_Tree_View(
        name              = 'ships',
        display_name      = 'Ships',
        object_categories = ['ships'],
        label_item        = 'name',
        subcategory_func  = Subcat_func,    
    )


@Live_Editor_Tree_View_Builder('wares')
def _Build_Ware_Object_Tree_View():
    '''
    Constructs an Edit_Tree_View object for use in displaying
    ware data.
    '''
    def Subcat_func(object):
        'Set up sub categories.'
        group     = object.Get_Item_Value('group', default = 'ungrouped')
        transport = object.Get_Item_Value('transport', default = 'no transport')
        return group, transport

    return Build_Object_Tree_View(
        name              = 'wares',
        display_name      = 'Wares',
        object_categories = ['wares'],
        label_item        = 'name',
        subcategory_func  = Subcat_func,    
    )



@Live_Editor_Tree_View_Builder('shields')
def _Build_Shield_Object_Tree_View():
    '''
    Constructs an Edit_Tree_View object for use in displaying
    shield data.
    '''
    def Subcat_func(object):
        'Set up sub categories.'
        # Size needs to be found in the tags.
        tags = object.Get_Item_Value('connection_tags').split()
        for size in ['small','medium','large','extralarge']:
            if size in tags:
                break
            size = '?'
        return size

    return Build_Object_Tree_View(
        name              = 'shields',
        display_name      = 'Shields',
        object_categories = ['shields'],
        label_item        = 'name',
        subcategory_func  = Subcat_func,    
    )

# TODO:
# engines (thrusters)
# storage

@Live_Editor_Tree_View_Builder('engines')
def _Build_Engine_Object_Tree_View():
    '''
    Constructs an Edit_Tree_View object for use in displaying
    engine data.
    '''
    def Subcat_func(object):
        'Set up sub categories.'
        # Size needs to be found in the tags.
        tags = object.Get_Item_Value('connection_tags').split()
        for size in ['small','medium','large','extralarge','spacesuit']:
            if size in tags:
                break
            size = 'unsized'
        for type in ['engine','thruster']:
            if type in tags:
                break
            type = '?'
        return type, size

    return Build_Object_Tree_View(
        name              = 'engines',
        display_name      = 'Engines',
        object_categories = ['engines'],
        label_item        = 'name',
        subcategory_func  = Subcat_func,    
    )


@Live_Editor_Tree_View_Builder('components')
def _Build_Components_Object_Tree_View():
    '''
    Constructs an Edit_Tree_View object for use in displaying
    various ship component data.
    '''
    # Set up a new tree.
    object_tree_view = Edit_Tree_View('components', 'Components')

    # Collect from existing trees.
    object_tree_view.Add_Tree(
        Live_Editor.Get_Tree_View('shields'))
    object_tree_view.Add_Tree(
        Live_Editor.Get_Tree_View('engines'))

    # Generic other components as they get added.
    for category in ['scanners','dockingbays','storage']:
        object_tree_view.Add_Tree(
            Build_Object_Tree_View(
                name = category,
                display_name = category,
                object_categories = [category],
                label_item = 'name',
            ))

    # Sort the tree in place when done.
    object_tree_view.Sort_Branches()

    return object_tree_view

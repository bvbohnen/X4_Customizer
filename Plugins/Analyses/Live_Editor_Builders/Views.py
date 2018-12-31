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
      - Strings, categories to look up in the live editor.
      - If multiple given, they will be split into branches.
    * flat
      - Bool, if True and multiple object_categories are present,
        they will be collected together and not split into branches.
    * label_item
      - Name of an item in the objects which will provide the tree label.
      - Often 'name', though could be other terms.
    '''
    object_tree_view = Edit_Tree_View(name, display_name)

    # Always flat with one category.
    if len(object_categories) == 1:
        flat = True

    for category in object_categories:
        objects_list = Live_Editor.Get_Category_Objects(category)

        for object in objects_list:
            name = object.Get_Item(label_item).Get_Value('current')
            if flat:
                object_tree_view.Add_Object(name, object)
            else:
                object_tree_view.Add_Object(name, object, category)
                
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
    # Set up a new table.
    object_tree_view = Edit_Tree_View('bullets')

    # Get all of the objects.
    objects_list = Live_Editor.Get_Category_Objects('bullets')

    # Organize by class, then by size.
    for object in objects_list:
        # Use the bullet_codename to label it.
        name      = object.Get_Item('bullet_codename').Get_Value('current')
        # No categorization for now.
        object_tree_view.Add_Object(name, object)
        
    # Sort the tree in place when done.
    object_tree_view.Sort_Branches()

    # Apply default label filtering.
    object_tree_view.Apply_Filtered_Labels()

    return object_tree_view



@Live_Editor_Tree_View_Builder('weapons')
def _Build_Weapon_Object_Tree_View():
    '''
    Constructs an Edit_Tree_View object for use in displaying
    weapon data.
    '''
    # Set up a new table.
    object_tree_view = Edit_Tree_View('weapons')

    # Get all of the objects.
    objects_list = Live_Editor.Get_Category_Objects('weapons')

    # Organize by class, then by size.
    for object in objects_list:
        # Use the parsed name to label it.
        name      = object.Get_Item('name')     .Get_Value('current')
        wclass     = ('' if object.Get_Item('macro_class') == None 
                    else object.Get_Item('macro_class').Get_Value('current'))

        # Size needs to be found in the tags.
        tags = object.Get_Item('connection_tags').Get_Value('current')
        for size in ['small','medium','large','spacesuit']:
            if size in tags:
                break
            size = '?'

        object_tree_view.Add_Object(name, object, wclass, size)
        
    # Sort the tree in place when done.
    object_tree_view.Sort_Branches()

    # Apply default label filtering.
    object_tree_view.Apply_Filtered_Labels()

    return object_tree_view


@Live_Editor_Tree_View_Builder('wares')
def _Build_Ware_Object_Tree_View():
    '''
    Constructs an Edit_Tree_View object for use in displaying
    ware data.
    '''
    # Set up a new table.
    object_tree_view = Edit_Tree_View('wares')

    # Get all of the objects.
    ware_objects = Live_Editor.Get_Category_Objects('wares')

    # Organize by group, then by transport type.
    for ware_object in ware_objects:
        # Use the parsed name to label it.
        name      = ware_object.Get_Item('name')     .Get_Value('current')
        group     = ('' if ware_object.Get_Item('group') == None 
                    else ware_object.Get_Item('group').Get_Value('current'))
        transport = ('' if ware_object.Get_Item('transport') == None 
                    else ware_object.Get_Item('transport').Get_Value('current'))

        # Categories may have failed due to lack of a node, or an
        # empty attribute. Provide defaults to avoid empty labels.
        if not group:
            group = 'ungrouped'
        if not transport:
            transport = 'no transport'

        object_tree_view.Add_Object(name, ware_object, group, transport)
        
    # Sort the tree in place when done.
    object_tree_view.Sort_Branches()

    # Apply default label filtering.
    object_tree_view.Apply_Filtered_Labels()

    return object_tree_view



@Live_Editor_Tree_View_Builder('shields')
def _Build_Shield_Object_Tree_View():
    '''
    Constructs an Edit_Tree_View object for use in displaying
    shield data.
    '''
    # Set up a new tree.
    object_tree_view = Edit_Tree_View('shields')

    # Get all of the objects.
    objects_list = Live_Editor.Get_Category_Objects('shields')

    # Organize by class, then by size.
    for object in objects_list:
        # Use the parsed name to label it.
        name      = object.Get_Item('name')     .Get_Value('current')

        # Size needs to be found in the tags.
        tags = object.Get_Item('connection_tags').Get_Value('current').split()
        for size in ['small','medium','large','extralarge']:
            if size in tags:
                break
            size = '?'

        object_tree_view.Add_Object(name, object, size)
        
    # Sort the tree in place when done.
    object_tree_view.Sort_Branches()

    # Apply default label filtering.
    object_tree_view.Apply_Filtered_Labels()

    return object_tree_view



@Live_Editor_Tree_View_Builder('components')
def _Build_Components_Object_Tree_View():
    '''
    Constructs an Edit_Tree_View object for use in displaying
    various ship component data.
    '''
    # Set up a new tree.
    object_tree_view = Edit_Tree_View('components', 'Components')

    # Get the shields tree, with some internal sorting.
    object_tree_view.Add_Tree(
        Live_Editor.Get_Tree_View('shields'))

    # Generic other components as they get added.
    for category in ['scanners','dockingbays','engines','storage']:
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


from collections import defaultdict, OrderedDict
from lxml import etree as ET

from Framework import Analysis_Wrapper
from Framework import File_System
from Framework import Settings
from Framework import Live_Editor
from Framework import Print


# TODO: make file_name automated based on category.
@Analysis_Wrapper()
def Print_Object_Stats(
        category, 
        file_name,
        version = None,
    ):
    '''
    Print out statistics for objects of a given category.
    This output will be similar to that viewable in the gui live editor
    pages, except formed into one or more tables.
    Produces csv and html output.
    Will include changes from enabled extensions.

    * category
      - String, category name of the objects, eg. 'weapons'.
    * file_name
      - String, name to use for generated files, without extension.
    * version
      - Optional string, version of the objects to use.
      - One of ['vanilla','patched','current','edited'].
      - Defaults to 'current'.
    '''
    try:
        tree_view = Live_Editor.Get_Tree_View(category)
        assert tree_view != None
    except Exception as ex:
        Print(('Could not print objects, error obtaining tree view for'
               ' category "{}".').format(category))
        if Settings.developer:
            raise ex
        return

    if version == None:
        version = 'current'

    # Convert it to an edit table group.
    table_group = tree_view.Convert_To_Table_Group()
    table_list = []

    for edit_table in table_group.Get_Tables():

        # This returns a 2d list of lists holding edit items, that
        # still need to be converted to strings.
        # These will use the selected version for filling out references.
        item_table = edit_table.Get_Table(version = version)
        
        # Prep a clean table of strings.
        new_table = []
        table_list.append(new_table)

        # Copy over the headers.
        new_table.append(item_table[0])

        for row in item_table[1:]:
            new_row = []
            new_table.append(new_row)
            for item in row:

                # Get its current value, or an empty string if no
                # item was available.
                value = '' if item == None else item.Get_Value(version)
                new_row.append( value )

    # Write results.
    Write_Tables(file_name, *table_list)
    return


@Analysis_Wrapper()
def Print_Weapon_Stats(file_name = 'weapon_stats', version = None):
    '''
    Gather up all weapon statistics, and print them out.
    This is a convenience wrapper around Print_Object_Stats,
    filling in the category and a default file name.

    * file_name
      - String, name to use for generated files, without extension.
      - Defaults to "weapon_stats".
    * version
      - Optional string, version of the objects to use.
    '''
    Print_Object_Stats(
        category = 'weapons',
        file_name = file_name,
        version = version)
    return


@Analysis_Wrapper()
def Print_Ware_Stats(file_name = 'ware_stats', version = None):
    '''
    Gather up all ware statistics, and print them out.
    This is a convenience wrapper around Print_Object_Stats,
    filling in the category and a default file name.

    * file_name
      - String, name to use for generated files, without extension.
      - Defaults to "ware_stats".
    * version
      - Optional string, version of the objects to use.
    '''
    Print_Object_Stats(
        category = 'wares',
        file_name = file_name,
        version = version)
    return




##############################################################################
# Support functions.

def Convert_Weapon_Edit_Tree_View():
    '''
    Uses the Edit_Tree_View for weapons to construct a list of lists,
    to be used for file writing.
    '''
    tree_view = Live_Editor.Get_Tree_View('weapons')
    # Convert it to an edit table group.
    table_group = tree_view.Convert_To_Table_Group()
    table_list = []

    for edit_table in table_group.Get_Tables():

        # This returns a 2d list of lists holding edit items, that
        # still need to be converted to strings.
        item_table = edit_table.Get_Table()
        
        # Prep a clean table of strings.
        new_table = []
        table_list.append(new_table)

        # Copy over the headers.
        new_table.append(item_table[0])

        for row in item_table[1:]:
            new_row = []
            new_table.append(new_row)
            for item in row:

                # Get its current value, or an empty string if no
                # item was available.
                if item != None:
                    # TODO: maybe support other versions (vanilla, patched, etc.).
                    value = item.Get_Value('current')
                else:
                    value = ''
                new_row.append( value )

    return table_list




def Write_Tables(file_name, *tables):
    '''
    Writes one or more tables (list of lists) to output files.
    '''
    # Now pick a format to print to.
    # TODO: move these into a support module.
    # CSV initially.
    with open(Settings.Get_Output_Folder() / (file_name+'.csv'), 'w') as file:
        for table in tables:
            for line in table:
                # Quick fix: replace commas in the line to avoid them
                # getting confused with the csv commas.
                file.write(', '.join([x.replace(',',';') for x in line]) + '\n')
            # Put extra space between tables.
            file.write('\n')

    # HTML style.
    with open(Settings.Get_Output_Folder() / (file_name+'.html'), 'w') as file:
        for table in tables:
            xml_node = Table_To_Html(table)
            file.write(ET.tostring(xml_node, pretty_print = True, encoding='unicode'))
            # Put extra space between tables.
            file.write('\n')

    return

            
def Table_To_Html(table):
    '''
    Returns an xml root node holding html style nodes with the
    contents of the given table (list of lists, first line
    being the columns headers).
    '''
    # Pick the css styles; these will be ';' joined in a 'style' attribute.
    # Using http://www.stylinwithcss.com/resources_css_properties.php
    # to look up options.
    table_styles = {
        # Single line instead of double line borders.
        'border-collapse' : 'collapse',
        # Not too clear on this; was an attempt to stop word wrap.
        #'width'           : '100%', 
        # Stop wordwrap on the names and headers and such.
        'white-space'     : 'nowrap', 
        # Get values to be centered instead of left aligned.
        'text-align'      : 'center',
        # TODO: play with captioning.
        'caption-side'    : 'left',
        # Margin between tables.
        'margin-bottom'   : '20px',
        }
    cell_styles = {
        # Give some room around the text before hitting the cell borders.
        # TODO: not working; if placed on the table, puts a giant
        # margin around the whole table.
        #'margin'          : '10px',
        # Adjust this with padding. Don't set this very high; it is really
        # sensitive.
        'padding'         : '2px',
        }
    root = ET.Element('table', attrib = {
        'border':'1',
        #'cellpadding' : '0', 
        #'cellspacing' : '0',
        # CSS styles, separated by ;
        'style' : ';'.join('{}:{}'.format(k,v) 
                           for k,v in table_styles.items()),
        })
    for index, line in enumerate(table):
        row = ET.Element('tr', attrib = {
                # CSS styles, separated by ;
                'style' : ';'.join('{}:{}'.format(k,v) 
                                   for k,v in cell_styles.items()),
                })
        root.append(row)
        for entry in line:
            if index == 0:
                tag = 'th'
            else:
                tag = 'td'
            col = ET.Element(tag, attrib = {
                # CSS styles, separated by ;
                'style' : ';'.join('{}:{}'.format(k,v) 
                                   for k,v in cell_styles.items()),
                })
            col.text = entry
            row.append(col)
    return root
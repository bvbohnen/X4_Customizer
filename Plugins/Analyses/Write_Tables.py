
from lxml import etree as ET
from Framework import Settings

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
                file.write(', '.join(line) + '\n')
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


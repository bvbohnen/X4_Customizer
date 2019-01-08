

from Framework import Transform_Wrapper, Settings, Load_File, File_System

'''
Copied from x3 customizer; maybe do something with this.
    Race_color_letters = {
            # argon
            '1': 'B',
            # boron
            '2': 'G',
            # split
            '3': 'M',
            # paranid
            '4': 'C',
            # teladi
            '5': 'Y',
            # xenon
            '6': 'R',
            # kha'ak
            '7': 'R',
            # pirates
            '8': 'R',
            # goner
            '9': 'B',
            # unknown; leave uncolored or just use grey. Code is more consistent
            #  for now to just use grey.
            '14': 'A',
            # Terran (ATF)
            '17': 'W',
            # Terran (USC)
            '18': 'W',
            # Yaki
            '19': 'R',
        }
'''

# TODO: develop this further to support text searching, coloring only
# selected words, maybe; that wouldn't be as robust across languages
# though.
@Transform_Wrapper(category = 'Text')
def Color_Text(
        *page_t_colors
    ):
    '''
    Applies coloring to selected text nodes, for all versions
    of the text found in the current X4 files.
    Note: these colors will override any prior color in effect,
    and will return to standard text color at the end of the colored
    text node.

    * page_t_colors
      - One or more groups of (page id, text id, color code) to apply.

    Example:
    <code>
        Color_Text(
            (20005,1001,'B'),
            (20005,3012,'C'),
            (20005,6046,'Y'),
            )
    </code>
    '''
    # TODO: add a list of support colors to the doc.
    # TODO: verify input.

    # Load all text files.
    game_files = File_System.Load_Files('t/*.xml')

    # Loop over them.
    for game_file in game_files:
        xml_root = game_file.Get_Root()

        # Loop over the colorings.
        change_found = False
        for page, text, color in page_t_colors:
            # Look up the node.
            node = xml_root.find('./page[@id="{}"]/t[@id="{}"]'.format(page,text))
            # Skip on missing node.
            if node == None:
                continue
            # Prefix and suffix it with color.
            node.text = r'\033{}{}\033X'.format(color, node.text)
            change_found = True
        
        # TODO: delay this until after all loops complete, in
        # case a later one has an error, to safely cancel the
        # whole transform.
        if change_found:
            game_file.Update_Root(xml_root)

    return
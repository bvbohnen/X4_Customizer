'''
Generate documentation for the customizer.
This will parse the docstrings at the top of X4_Customizer and
for each transform, and write them to a plain text file.

This can generally be called directly as an entry function.


Quick markdown notes, for the readme which will be dispayed on
github, and the main documentation just because:

 -Newlines don't particularly matter. Can break up lines for a text
 file, and they will get joined back together.

 -This is bad for a list of transforms, since they get lumped together,
 so aim to put markdown characters on them to listify them.

 -Adding asterisks at the start of lines will turn them into a list,
 as long as there is a space between the asterisk and the text.

 -Indentation by 4 spaces or 1 tab creates code blocks; try to avoid 
 this level of indent unless code blocking is intentional.

 -Indentation is built into some docstrings, though the only one that
 should matter for the markdown version is x4_customizer. That one needs
 to be carefully adjusted to avoid 4-space chains, including across
 newlines.

 -Triple -,*,_ will place a horizontal thick line. Can be used between
 sections. Avoid dashes, though, since they make whatever is above them
 into a header, unless that is desired.

'''

import os
import sys
from pathlib import Path
from collections import OrderedDict, defaultdict

# To support packages cross-referencing each other, set up this
#  top level as a package, findable on the sys path.
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

import Framework
import Plugins

# TODO: swap to Path.
this_dir = os.path.normpath(os.path.dirname(__file__))

def Make(*args):

    # TODO:
    # Make a variation on the simple doc which has some formatting for
    #  the egosoft forum, including code blocks and removing newlines
    #  when the next line starts with a lowercase character.

    # Make a list of lines or text blocks to print out.
    doc_lines = []

    # Also include a simple version, which will truncate
    #  the transform descriptions, aimed at providing a summary which
    #  is suitable for posting.
    # Git appears to expect a README.md file; this can be used to
    #  generate that, although one directory up.
    doc_short_lines = []

    # Set the indent type. Use double space, since markdown likes
    #  that as a unit.
    # Avoid indenting by 4 spaces (from previous text) unless wanting a 
    #  code block in markdown.
    indent = '  '

    def Make_Horizontal_Line(include_in_simple = True):
        'Adds a horizontal line, with extra newline before and after.'
        # TODO: maybe swap to a bunch of dashes, for a better look
        #  in the raw text format. This requires a newline before
        #  the dashes to avoid upscaling prior text.
        this_line = '\n***\n'
        doc_lines.append(this_line)
        if include_in_simple:
            doc_short_lines.append(this_line)

    def Add_Line(line, indent_level = 0, include_in_simple = True):
        'Add a single line to the files, including any newlines.'
        # Prefix with a number of indents.
        this_line = indent * indent_level + line
        doc_lines.append(this_line)
        if include_in_simple:
            doc_short_lines.append(this_line)

    def Add_Lines(text_block, indent_level = 0, 
                  include_in_simple = True,
                  only_header_in_simple = False,
                  merge_lines = False):
        '''
        Record a set of lines from text_block, with indent, splitting on
        newlines. May not include all starting or ending newlines, depending
        on behavior of splitlines(). Starting newlines are explicitly
        ignored.
        If include_in_simple == True, the simple file will not have any
        lines added.
        If only_header_in_simple == True, the simple file will not have
        any lines added past the first empty line following a text line,
        eg. only the first group of text lines are included.
        If merge_lines == True, this will attempt to merge lines together
        that appear to be part of the same paragraph.
        '''
        # Merge before further processing.
        if merge_lines:
            text_block = Merge_Lines(text_block)

        # Flag for when an empty line is found.
        # This will not count any pruned starting empty lines, eg. when
        #  triple quotes are used they tend to put an initial empty line.
        empty_line_found = False
        non_empty_line_found = False

        # Loop over the lines.
        for line in text_block.splitlines():

            # Note if this line has contents.
            if not non_empty_line_found and line.strip():
                non_empty_line_found = True
            # Skip until a non empty line found.
            if not non_empty_line_found:
                continue

            # Note if this is an empty line.
            if not empty_line_found and not line.strip():
                empty_line_found = True

            # Prefix with a number of indents.
            this_line = indent * indent_level + line
            # Add to the main document.
            doc_lines.append(this_line)
            if include_in_simple:
                # Add to the short document only if including everything or
                #  an empty line not hit yet.
                if not (only_header_in_simple and empty_line_found):
                    doc_short_lines.append(this_line)


    def Record_Text_Block(
            text,
            header_name = None, 
            indent_level = 0, 
            end_with_empty_line = True,
            include_in_simple = False,
            include_name = True):
        '''
        Record a text block, with an optional header name.
        Text is expected to come from docstrings.
        If include_in_simple == False, the simple file is skipped entirely.
        Otherwise, the simple file will get a truncated name with the initial
        part of the docstring, and no requirement list.
        '''
        # Get the name as-is.
        # Put an asterix in front for markdown.
        if header_name:
            name_line = '* ' + header_name      
            Add_Line(name_line, indent_level, 
                      include_in_simple = include_in_simple)

        # Stick another newline, then the text docstring, maybe
        #  truncated for the simple file.
        Add_Line('', include_in_simple = include_in_simple)
        Add_Lines(text, indent_level +1,
                  include_in_simple = include_in_simple,
                  only_header_in_simple = True,
                  # Get rid of excess newlines.
                  merge_lines = True
                  )

        if end_with_empty_line:
            Add_Line('')
        return


    # Grab the main docstring.
    # Add in the version number.
    main_doc = Framework.__doc__.replace(
        'X4 Customizer', 
        'X4 Customizer {}'.format(Framework.Change_Log.Get_Version()),
        # Only change the first spot, the title line.
        1)
    # TODO: figure out how to split off the example tree.
    Add_Lines(main_doc, merge_lines = True)
    
    # Add a note for the simple documentation to point to the full one.
    doc_short_lines.append(
        '\nFull documentation found in Documentation.md,'
        ' describing settings and transform parameters.')

    
    # Print out the example module early, to be less scary.
    # The example will accompany the simple version, since it is a good way
    #  to express what the customizer is doing.
    Make_Horizontal_Line()
    Add_Line('Example input file:')
    # Need a newline before the code, otherwise the code block
    #  isn't made right away (the file header gets lumped with the above).
    Add_Line('')
    with open(os.path.join(this_dir,'..','Scripts',
                           'Example_Transforms.py'), 'r') as file:
        # Put in 4 indents to make a code block.
        Add_Lines(file.read(), indent_level = 2)


    # Grab the Settings documentation.
    # Skip this for the simple summary.
    Make_Horizontal_Line(include_in_simple = False)
    # TODO: maybe leave this header to the Record_Text_Block call.
    Add_Line('* Settings:', include_in_simple = False)
    Add_Line('', include_in_simple = False)
    Record_Text_Block(
        Framework.Settings.__doc__, 
        indent_level = 1,
        include_in_simple = False
        )
    

    # Grab the various plugins.
    for plugin_type, plugin_type_plural in (
            ('Analysis' , 'Analyses'),
            ('Transform', 'Transforms'),
            ('Utility'  , 'Utilities')
        ):

        # Grab the various plugin functions.
        # Collect into a dict keyed by category name.
        category_plugin_dict = defaultdict(list)
        for item_name in dir(Plugins):
            item = getattr(Plugins, item_name)

            # Skip if the wrong type of plugin or not a plugin.
            # Can check for the _plugin_type attribute, attached by the decorator.
            if getattr(item, '_plugin_type', None) != plugin_type:
                continue
        
            # Skip if the file name starts with an underscore, indicating
            #  an experimental function.
            if item.__name__[0] == '_':
                continue

            # Record this function for the category.
            category_plugin_dict[item._category].append(item)
        

        # Can now print out by category, sorted.
        for category, plugin_list in sorted(category_plugin_dict.items()):
    
            # Put a header for the category transform list.
            # Note: if category was left blank, just print the plugin_type
            # (omit any space); helpful for Analyses.
            Make_Horizontal_Line()
            Add_Line('{}{}{}:'.format(
                category, 
                ' ' if category else '',
                plugin_type_plural))
            Add_Line('')


            # Handle shared documentation at the top.
            # Look through the plugins, find shared docstrings, and keep
            # one copy of each.
            shared_docs = []
            for plugin in plugin_list:
                for shared_doc in plugin._shared_docs:
                    if shared_doc not in shared_docs:
                        shared_docs.append(shared_doc)
            # Chain them together, with header.
            if shared_docs:
                shared_docs_text = '\n'.join(shared_docs)
                Record_Text_Block(
                    shared_docs_text, 
                    header_name = 'Common documentation',
                    indent_level = 1, 
                    include_in_simple = False)


            # Loop over the plugin in the category, sorted by reversed
            # priority, then by name. Want high priority to go first,
            # so negate it.
            for plugin in sorted(plugin_list, key = lambda k: (-1 * k._doc_priority, k.__name__)):
                Record_Text_Block(
                    plugin.__doc__, 
                    header_name = plugin.__name__,
                    indent_level = 1, 
                    include_in_simple = True)
            

    # Print out the change log.
    # Only do this for the full documenation now, after it got too
    # long for the egosoft forums.
    Make_Horizontal_Line()
    Add_Lines(Framework.Change_Log.__doc__, merge_lines = True,
                  include_in_simple = False)

    # Print out the license.
    # The simple version will skip this.
    # This probably isn't needed if there is a license file floating around
    #  in the repository; remove for now.
    # Make_Horizontal_Line(include_in_simple = False)
    # with open(os.path.join('..','License.txt'), 'r') as file:
    #     Add_Lines(file.read(), include_in_simple = False)

    # Get a set of lines suitable for the egosoft forum thread,
    #  using BB code.
    doc_bb_lines = Get_BB_Text(doc_short_lines)
    # Prefix with some extra lines for the forum.
    doc_bb_lines = [
        'Download source from github:',
        '[url]https://github.com/bvbohnen/X4_Customizer[/url]',
        'Compiled release (64-bit Windows):',
        '[url]https://github.com/bvbohnen/X4_Customizer/releases[/url]',
        'Full documentation (describing settings and transform parameters):',
        '[url]https://github.com/bvbohnen/X4_Customizer/blob/master/Documentation.md[/url]',
        '',
        '',
        ] + doc_bb_lines
    
    # Write out the full doc.
    # Put these 1 directory up to separate from the code.
    with open(os.path.join(this_dir,'..','Documentation.md'), 'w') as file:
        file.write('\n'.join(doc_lines))

    # Write out the simpler readme.
    with open(os.path.join(this_dir,'..','README.md'), 'w') as file:
        file.write('\n'.join(doc_short_lines))
        
    # Write out the BB version, suitable for copy/paste.
    with open(os.path.join(this_dir,'..','for_egosoft_forum.txt'), 'w') as file:
        file.write('\n'.join(doc_bb_lines))

    return


def Remove_Line_Indents(line_list):
    '''
    Removes global indentation from the text block.
    Eg. if all lines are indented by 4 spaces, those 4 are removed
    from all lines.
    Takes in a list of lines, and edits the list directly.
    '''
    # Start by finding the global indent level and removing it.
    min_indent = None
    for line in line_list:
        # Skip empty lines.
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(' '))
        if min_indent == None or indent < min_indent:
            min_indent = indent
    # Do removal only if a min_indent was found, and is not 0.
    if min_indent:
        for index, line in enumerate(line_list):
            # Skip empty lines.
            if not line.strip():
                continue
            # Cut off the start of each line.
            line_list[index] = line[min_indent : ]
    return


def Merge_Lines(text_block):
    '''
    To get a better text file from the python docstrings, with proper
     full lines and wordwrap, do a pass over the text block and
     do some line joins.
    General idea is that two lines can merge if:
    -Both have normal text characters (eg. not '---').
    -Not in a code block (4+ space indent series of lines outside of
     a list).
    -Second line does not start a sublist (starts with -,*,etc.).
    Note: markdown merge rules are more complicated, but this should be
    sufficient for the expected text formats.
    This should not be called on code blocks.
    This will also look for and remove <code></code> tags, a temporary
    way to specify in docstrings sections not to be line merged.
    Since much of the text comes from indented doc strings, this will
    also remove the uniform indentation.
    '''
    # Convert the input to a list.
    line_list = [x for x in text_block.splitlines()]
    
    # Start by finding the global indent level and removing it.
    Remove_Line_Indents(line_list)

    # Next, want to collect a list of line indices where merges
    # are wanted, and trim out some tags that were used to
    # help determine this.

    # List of lines to merge with previous.
    merge_line_list = []
    # Note if the prior line had text.
    prior_line_had_text = False
    # Note if a code block appears active.
    code_block_active = False

    for line_number, line in enumerate(line_list):
        # Get rid of indent spacing.
        strip_line = line.strip()
        merge = True

        # If this is a <code> tag, start a code block, and remove
        #  the tag.
        if strip_line == '<code>':
            code_block_active = True
            merge = False
            line_list[line_number] = ''
            strip_line = ''
            
        elif strip_line == '</code>':
            code_block_active = False
            merge = False
            line_list[line_number] = ''
            strip_line = ''

        # When a code block is active, don't merge.
        elif code_block_active:
            merge = False

        # Skip the first line; nothing prior to merge with.
        elif line_number == 0:
            merge = False
        
        # If the line is empty, leave empty.
        elif not strip_line:
            merge = False

        # If the line starts with a sublist character, don't merge.
        elif strip_line[0] in ['*','-']:
            merge = False

        # If the prior line didn't have text, don't merge.
        elif not prior_line_had_text:
            merge = False


        # If merging, record the line.
        if merge:
            merge_line_list.append(line_number)

        # Update the prior line status.
        prior_line_had_text = len(strip_line) > 0


    # Final pass will do the merges.
    # This will aim to remove indentation, and replace with a single space.
    # This will delete lines as going, requiring the merge_line numbers to be
    #  adjusted by the lines removed prior. This can be captured with an
    #  enumerate effectively.
    for lines_removed, merge_line in enumerate(merge_line_list):

        # Adjust the merge_line based on the current line list.
        this_merge_line = merge_line - lines_removed

        # Get the lines.
        prior_line = line_list[this_merge_line-1]
        this_line = line_list[this_merge_line]

        # Remove spacing at the end of the first, beginning of the second.
        prior_line = prior_line.rstrip()
        this_line = this_line.lstrip()

        # Join and put back.
        line_list[this_merge_line-1] = prior_line + ' ' + this_line

        # Delete the unused line.
        line_list.pop(this_merge_line)
        
    # Return as a raw text block.
    return '\n'.join(line_list)


def Get_BB_Text(line_list):
    '''
    Converts a list of markdown suitable lines to forum BB code
    suitable lines.
    '''
    # Version of short for forum BB code.
    # To reduce complexity explosion for all these docs, this one modify
    #  existing text rather than being generated on the first pass.
    bb_lines = []

    # Tag for if a list is in use.
    list_active = False
    # Indent of the list.
    list_indent = None
    # Tag for if a code section is in use.
    code_active = False
    # Tag for if the change log section is active.
    changelog_active = False
    # Tag for if a transform section is active.
    transform_active = False
    # The running line index, used to join list/code tags with
    #  the next line if blank.
    index = 0

    def Add_Tag(tag):
        '''
        Pushes a tag, and advances past the next input line if it is blank,
        or tries to replace the last line if blank.
        '''
        nonlocal index
        # Can psuedo-join with the next line by just advancing the
        #  index to skip it when blank.
        # -Removed; doesn't make too much sense.
        #if index + 1 < len(line_list) and not line_list[index + 1]:
        #    index += 1
        #    bb_lines.append(tag)
        # Check if the prior line was blank and overwrite it.
        if bb_lines and not bb_lines[-1]:
            bb_lines[-1] = tag
        # Otherwise just add another line as normal.
        else:
            bb_lines.append(tag)
        return

    def Open_List():
        'Open a new list.'
        nonlocal list_active
        if not list_active:
            Add_Tag('[list]')
            list_active = True

    def Close_List():
        'Close a current list.'
        nonlocal list_active
        if list_active:
            Add_Tag('[/list]')
            list_active = False

    def Open_Code():
        'Open a new code section.'
        nonlocal code_active
        if not code_active:
            Add_Tag('[code]')
            code_active = True

    def Close_Code():
        'Close a current code section.'
        nonlocal code_active
        if code_active:
            Add_Tag('[/code]')
            code_active = False

    def Bold(string):
        'Apply bold tags to a string.'
        return '[b]{}[/b]'.format(string)
    
    def Underline(string):
        'Apply underline tags to a string.'
        return '[u]{}[/u]'.format(string)

    def Color(string, color):
        'Apply color tags to a string. Should go inside other tags.'
        return '[color={}]{}[/color]'.format(color, string)

    def Small(string):
        'Apply small font tags to a string. Should go inside other tags.'
        # Use BB default small/large sizes.
        # Update: the latest BB software treats this as a %.
        return '[size=75]{}[/size]'.format(string)

    def Large(string):
        'Apply large font tags to a string. Should go inside other tags.'
        return '[size=200]{}[/size]'.format(string)

    def Record(line):
        'Record a line for the BB lines.'
        bb_lines.append(line)
        

    # Work through the original lines, making edits and recording
    #  the new lines.
    # This will be index based, to support look-ahead and line skips.
    while index < len(line_list):
        line = line_list[index]

        # Get a whitespace stripped version for convenience.
        strip_line = line.strip()

        # Empty lines get handled first.
        # Skip newlines while lists are active; the egosoft
        #  forums always hide the later newlines in a list entry,
        #  which just makes earlier ones awkward.
        # This assumes there are no newlines in the middle of
        #  transform description text, which there shouldn't be
        #  for simple documentation.
        if not strip_line:
            if not list_active:
                Record('')

        
        # At every '***', any active list or code is closed.
        elif strip_line == '***':
            Close_Code()
            Close_List()
            changelog_active = False
            transform_active = False
            # Drop the *s for now.
            Record('')

        # Otherwise if code is active, leave the line unchanged.
        elif code_active:
            Record(line)
            
        # Special cases:
        # Hype up the main heading.
        elif line.startswith('X4 Customizer'):
            # Note: tag order is somewhat strict (though in examples it
            #  shouldn't be).
            # Innermost is text size, then color, then bold.
            line = Large(line)
            # The color feels a little tacky; large/bold is enough.
            #line = Color(line, 'yellow')
            line = Bold(line)
            Record(line)

        # The underline under the heading can be swapped to a blank line.
        # In markdown this boldens the line above it; in BB the bolding
        #  is manual.
        elif strip_line.startswith('---'):
            Record('')

        # The 'Full documentation...' line breaks out of a list.
        elif strip_line.startswith('Full documentation'):
            Close_List()
            Record(line)

        # Look for any line that is a term ending in ':', but not
        #  starting with '*' or similar. This will be a header
        #  for a list (or maybe code), including closing a prior list.
        elif strip_line[0] not in ['-','*'] and strip_line[-1] == ':':
            Close_List()
            # Bold the list header.
            Record( Bold( line) )

            # The example input opens a code section, else open a list.
            if strip_line.startswith('Example input file'):
                Open_Code()
            else:
                Open_List()

            # Note when in the change log, to suppress extra formatting.
            if strip_line == 'Change Log:':
                changelog_active = True

            # Note when in a transform or other plugin section,
            #  to add formatting.
            if any(x in strip_line for x in ['Transforms','Analyses','Utilities']):
                transform_active = True


        # If the line starts with '*', it is a major list entry.
        elif strip_line[0] == '*':
            
            # Record the indent of the list, so it can be closed
            #  whenever indent is reduced by a line.
            list_indent = len(line) - len(line.lstrip())

            # Note: any format tags need to be applied after the *,
            #  so prune the * first, handle formatting, then add
            #  the [*] back on.
            new_line = strip_line.replace('*','',1)

            # Apply formatting.
            if transform_active:
                # Note: color appears not to work if there are other
                #  tags inside it, so put color wrapper first.
                # Note: color and underline is ugly; just do one or
                #  the other.
                new_line = Color(new_line, 'yellow')
                #new_line = Underline(new_line)

            # Make the change log items small.
            if changelog_active:
                new_line = Small(new_line)

            # Stick the [*] back on.
            Record('[*]' + new_line)

        # Other lines can record as-is.
        else:
            # Close a list if this line has a smaller indent.
            if list_active and (len(line) - len(line.lstrip()) < list_indent):
                Close_List()
            # Make the change log items small.
            if changelog_active:
                line = Small(line)
            Record(line)

        # Advance the index for next iteration.
        index += 1

    # If a list is active at the end, close it.
    Close_List()

    return bb_lines


if __name__ == '__main__':
    Make(sys.argv)
    
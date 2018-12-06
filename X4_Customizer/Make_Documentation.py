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
 should matter for the markdown version is x3_customizer. That one needs
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

import X4_Customizer
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

    # Set the indent type. A single spaces for now.
    # Avoid indenting by 4 unless wanting a code block, for the simple
    #  file that gets markdowned.
    indent = ' '

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


    def Record_Func(function, 
                    indent_level = 0, 
                    end_with_empty_line = True,
                    include_in_simple = False):
        '''
        Adds lines for a function name with docstring and requirements.
        If include_in_simple == True, the simple file is skipped entirely.
        Otherwise, the simple file will get a truncated name with the initial
        part of the docstring, and no requirement list.
        '''

        # Get the name as-is.
        # Put an asterix in front for markdown.
        name_line = '* ' + function.__name__
        
        Add_Line(name_line, indent_level, 
                  include_in_simple = include_in_simple)

        # If there are required files, print them.
        if hasattr(function, '_file_names'):

            # For markdown, don't want this attached to the file name,
            #  but also don't want it causing an extra list indent on
            #  the docstring. An extra newline and a healthy indent
            #  seems to work.
            Add_Line('', include_in_simple = False)
            Add_Line('{}Requires: {}'.format(
                    indent * (indent_level + 1),
                    # Join the required file names with commas if
                    #  there are any, else print None.
                    ', '.join(function._file_names) 
                    if function._file_names else 'None'),
                indent_level +1,
                include_in_simple = False
                )
            
        # Stick another newline, then the function docstring, maybe
        #  truncated for the simple file.
        Add_Line('', include_in_simple = include_in_simple)
        Add_Lines(function.__doc__, indent_level +1, 
                  include_in_simple = include_in_simple,
                  only_header_in_simple = True,
                  # Get rid of excess newlines.
                  merge_lines = True
                  )

        if end_with_empty_line:
            Add_Line('')


    # Grab the main docstring.
    # Add in the version number.
    main_doc = X4_Customizer.__doc__.replace(
        'X3 Customizer', 
        'X3 Customizer {}'.format(X4_Customizer.Change_Log.Get_Version()),
        # Only change the first spot, the title line.
        1)
    # TODO: figure out how to split off the example tree.
    Add_Lines(main_doc, merge_lines = True)
    
    # Add a note for the simple documentation to point to the full one.
    doc_short_lines.append('\nFull documentation found in Documentation.md.')

    
    # Print out the example module early, to be less scary.
    # The example will accompany the simple version, since it is a good way
    #  to express what the customizer is doing.
    Make_Horizontal_Line()
    Add_Line('Example input file:')
    # Need a newline before the code, otherwise the code block
    #  isn't made right away (the file header gets lumped with the above).
    Add_Line('')
    with open(os.path.join(this_dir,'..','input_scripts',
                           'Example_Transforms.py'), 'r') as file:
        # Put in 4 indents to make a code block.
        Add_Lines(file.read(), indent_level = 4)


    # Grab any setup methods.
    # Skip this for the simple summary.
    Make_Horizontal_Line(include_in_simple = False)
    Add_Line('Setup methods:', include_in_simple = False)
    Add_Line('', include_in_simple = False)
    # For now, just the Set_Path method.
    Record_Func(X4_Customizer.Set_Path, indent_level = 2,
                include_in_simple = False)
    # TODO: full settings.
    

    # Grab the various transform functions.
    # This can grab every item in Transforms that has been decorated with
    #  Transform_Wrapper.
    category_transforms_dict = defaultdict(list)
    for item_name in dir(X4_Customizer.Transforms):
        item = getattr(X4_Customizer.Transforms, item_name)

        # Skip non-transforms.
        # Can check for the _category attribute, attached by the decorator.
        if not hasattr(item, '_category'):
            continue
        
        # Skip if the file name starts with an underscore, indicating
        #  an experimental transform.
        if item.__name__[0] == '_':
            continue

        # Record this transform for the category.
        category_transforms_dict[item._category].append(item)
        

    # Can now print out by category.
    for category, transform_list in sorted(category_transforms_dict.items()):
    
        # Put a header for the category transform list.
        Make_Horizontal_Line()
        Add_Line('{} Transforms:'.format(category))
        Add_Line('')

        # Loop over the transforms in the category, sorted
        #  by their name.
        for transform in sorted(transform_list, key = lambda k: k.__name__):
            # Add the text.
            Record_Func(transform, indent_level = 1, include_in_simple = True)
            

    # Print out the change log.
    Make_Horizontal_Line()
    Add_Lines(X4_Customizer.Change_Log.__doc__, merge_lines = True)

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
        'Full documentation:',
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
    '''
    # List of lines to merge with previous.
    merge_line_list = []
    # Note if the prior line had text.
    prior_line_had_text = False
    # Note if a code block appears active.
    code_block_active = False
    # Convert the input to a list.
    line_list = [x for x in text_block.splitlines()]

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


    # Second pass will do the merges.
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
        if index + 1 < len(line_list) and not line_list[index + 1]:
            index += 1
            bb_lines.append(tag)
        # Check if the prior line was blank and overwrite it.
        elif bb_lines and not bb_lines[-1]:
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
        if not strip_line:
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
        elif line.startswith('X3 Customizer'):
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

            # Note when in a transform section, to add formatting.
            if 'Transforms' in strip_line:
                transform_active = True


        # If the line starts with '*', it is a major list entry.
        elif strip_line[0] == '*':

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
    
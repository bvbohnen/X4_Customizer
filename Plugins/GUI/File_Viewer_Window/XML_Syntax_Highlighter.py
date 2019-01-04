'''
Note: due to sluggish performance, the highlighter will be broken
up into a Qt element and the regex processing block. The regex part
should be independent and safe to run in a thread, and will return
a list of highlighting rules to feed into the qt block in the
main thread.

Performance notes:
    For a t file, original processing with QRegExp style
    inside the class (like done with scripts) took around 8-9 seconds.

    Switching to Get_Highlight_Macros and the re module drops this to
    6.5 seconds, where the class highlightBlock calls the function
    on each line.
    
    Preprocessing the lines drops highlighting from 6.5 to 1.7 seconds.
    Doing so in a single side thread takes 4.5 seconds, which drops
    down to 2.5 seconds when using multiprocessing.

    Overall, preprocessing drops it to 4.2 seconds. Not quite satisfactory,
    but at least the gui lockup period is only 1.7.
    For comparison, notepad++ loading the file takes ~1.2 seconds.
'''
import re
from collections import namedtuple
from functools import lru_cache

from PyQt5.QtGui import QSyntaxHighlighter, QColor, QTextCharFormat, QTextCursor
# Note: the QRegExp causes problems when threaded, even though
# it presumably has no parents and should be safe, so use re instead.
# Update: re works fine, plus it is needed anyway for multiprocessing.
#from PyQt5.QtCore import QRegExp


# Define some colors for terms.
# Pick colors from https://www.december.com/html/spec/colorsvg.html
type_color_dict = {
    'keyword'   : 'blue',
    'comment'   : 'darkGreen',
    'string'    : 'purple',
    'attribute' : 'crimson',
    }

'''
Some global variables, created once.

    * macro_pattern
      - Regex pattern (from re.compile) holding all patterns joined together.
    * formats
      - List of QTextCharFormat objects holding the formatting to
        apply for each subpattern, in grouping order in the
        macro pattern.
    * block_quote_index_closer_dict
      - Dict, keyed by the opening block quote pattern index in
        the macro_pattern, holding the Regex pattern to use
        to close the block.
      - When a block quote is active, the current block will
        be assigned the index for the corresponding quote type
        that opened it.
      - May be extended to cover multiline quotes.
'''
macro_pattern = None
colors = None
block_quote_index_closer_dict = {}

def _Init():
    '''
    Set up the regex rules.
    '''
    global macro_pattern
    global colors
    global block_quote_index_closer_dict
    # Set up the various rules.
    rules = []
        
    # Comment detection, eg. <!-- and -->

    # Since highlighting is done a line at a time (newline separated),
    #  this will be a little tricky to carry state across lines, but
    #  can be done with previousBlockState and setCurrentBlockState.
        

    # Open and close on a single line.
    rules.append((r'<!--(?:.*)-->', type_color_dict['comment']))
            
    # Same, but proceeding until the end of the line.
    # These have some special handling to cross line boundaries
    # later. Note: newline could maybe be omitted, since the regex
    # runs one line at a time, but can keep it for safety.
    rules.append((r'<!--(?:[^\n]*)', type_color_dict['comment']))

    # Special closing rule.
    # This is specially handled, different than other rules.
    # Record the indices of these rules.
    block_quote_index_closer_dict[len(rules)-1] = re.compile(r"(?:.*)-->")

    # Normal quoted strings, on a single line, possibly with nesting
    # that is backslashed.
    for char in ["'",'"']:
        # Looking for:
        # " "     : Pair of quotes.
        # [^"\\]  : Chars that are not a quote, and
        #           not a plain backslash.
        # \\.     : Backslash followed by any character.
        # "([^"\\]|\\.)" : Allow a mix of non-quote chars and backslashed
        #                  quotes. TODO: disallow newlines.
        # (?:     : Make the group non-capturing; mainly to avoid
        #           the match subgroup index advancing for this group,
        #           in case subgrouping is ever wanted, eg. for
        #           chaining multiple patterns together in a group match.
        #           Also, this should be faster than ().
        # For raw strings, include an optional preceeding '\br'.
        #  Use: (?:\br)?
        # So, overall, internally the quote can be anything except
        #  quotes that aren't backslashed.
        rules.append((r'(?:\br)?{0}(?:[^{0}\\]|\\.)*{0}'
                        .format(char), type_color_dict['string']))
            
    # TODO: maybe line-crossing quotes.
    # Similar to comments or the python multiline quotes, so mostly
    # just skipped here for laziness.

    # Node tags.
    # These are <tag> and </tag> and <tag/> and <tag ....>.
    # Look for char strings, "\w+", around the carrot options;
    # just copy out rules instead of making one complex one.
    rules.append((r'<\w+>' , type_color_dict['keyword']))
    rules.append((r'<\w+/>', type_color_dict['keyword']))
    rules.append((r'<\w+'  , type_color_dict['keyword']))
    rules.append((r'</\w+>', type_color_dict['keyword']))
               
    # Attribute tags.
    # \s for space, \w+ for a word, followed by =.
    rules.append((r'\s\w+=' , type_color_dict['attribute']))

    # Gather the regex patterns into a single macro pattern,
    # with capture groups for indexing final matches.
    macro_pattern = '(' + ')|('.join(p for p,c in rules) + ')'

    # There should be as many '(' as there are rules, when
    # omitting the non-capturing groups.
    assert macro_pattern.count('(') - macro_pattern.count('?:') == len(rules)
            
    # Wrap it.
    macro_pattern = re.compile(macro_pattern)
    
    # Set up a list of colors, for easy indexing into based on rule matched.
    colors = [c for p, c in rules]
    return

_Init()


# Containers for highlights to apply to a line,
# using setFormat(index, length, Get_Format(color))
Highlight_Macro = namedtuple(
    'Highlight_Macro', 
    ['index','length', 'color'])

def Get_Highlight_Macros(lines):
    '''
    Returns a list of lists of Highlight_Macro objects.
    Each list entry matches to a text line.
    Sublist entries are the highlight macros to feed to setFormat
    for the line in the QSyntaxHighlighter.
    '''
    line_macros_list = []

    # This will use a similar bit of logic to normal highlighting,
    # where the prior block's state regarding open quotes will
    # be tracked by an id value.
    # 0 is no open rule, other indices match those in
    # the block_quote_index_closer_dict keys.
    current_block_state  = 0
    previous_block_state = 0

    for line in lines:
        # Start a new macro list for this line.
        macros = []
        line_macros_list.append(macros)

        # Default block state to 0 (no block quote active).
        current_block_state = 0

        # Running offset in the text for where to start the next
        # regex search from. This advances as matches are found.
        offset = 0

        # Start by detecting if a block quote was active.
        # Block state will be 0 by default, or 1 for an open quote.
        prior_state = previous_block_state
        if prior_state in block_quote_index_closer_dict:

            # Grab the closing pattern.
            pattern = block_quote_index_closer_dict[prior_state]
            # Look up the color to use.
            color = colors[prior_state]

            # Look for a match.
            match = re.search(pattern, line[offset:])
            if not match:

                # No match, so highlight the entire line.
                macros.append( Highlight_Macro(offset, len(line), color))

                # Flag the block as still in a block quote.
                current_block_state = prior_state

                # Can either advance the offset all the way, or just
                # return. Go with offset advance, in case important
                # code is added later that might get skipped.
                offset = len(line)

            else:
                # Highlight the matched section.
                start, end = match.span()
                assert start == 0
                assert end > start
                length = end - start
                #length = matcher.matchedLength()
                macros.append( Highlight_Macro(offset + start, length, color))

                # Advance the offset. Regular matching will follow
                # from here.
                offset += end


        # Convenience renaming.
        pattern = macro_pattern

        # Loop until the regex returns -1, for no match.
        # Each iteration will advance to the end of the match.
        while 1:
            match = re.search(pattern, line[offset:])
            if not match:
                break

            # Determine which group was captured.
            # Can use the .group() (or []) function of the re match to look up
            #  any matched string for pattern group.
            # Since groups are OR'd together, only one of them is likely 
            #  to match, so most groups should return a blank.
            # Can loop until finding the first match, which also gives
            #  earlier patterns higher priority.
            # Note: the implicit capture group [0] is for the whole pattern,
            #  so include a +1 offset.
            for subpattern_index in range(len(colors)):
                match_text = match[subpattern_index + 1]
                if match_text:
                    break
            # Something should have matched.
            # This probably won't go awry in release code.
            assert match_text

            # Look up the color for this subpattern.
            color = colors[subpattern_index]
            
            # Set up the macro.
            start, end = match.span(subpattern_index + 1)
            assert end > start
            length = end - start
            macros.append( Highlight_Macro(offset + start, length, color))

            # Advance the offset for the next regex check, which will
            # be the current offset plus the end point of the match.
            offset += end

            # If the subpattern index was for opening a block quote,
            # tag the block with the corresponding index.
            if subpattern_index in block_quote_index_closer_dict:
                current_block_state = subpattern_index

        # Move the current block state to the last block for
        # the following iteration.
        previous_block_state = current_block_state

    return line_macros_list


@lru_cache(maxsize = 8)
def Get_Format(color_str):
    '''
    Returns a QTextCharFormat object set for the given color.
    The color string should be understood by QColor.setNamedColor().
    Suitable for feeding to setFormat().
    '''
    format = QTextCharFormat()
    # Wrap the color up.
    color = QColor()
    color.setNamedColor(color_str)
    format.setForeground(color)
    # TODO: other format stuff if desired, though nothing wanted
    # for now (stuff like bold might be set by fonts already).
    return format
    

class XML_Syntax_Highlighter(QSyntaxHighlighter):
    '''
    Apply syntax highlighting to xml files.
    TODO: also color lines with a difference between versions.

    Attributes:
    * enabled
      - Bool, if True then highlighting is enabled, else any
        automated calls to highlightBlock will return early.
    * line_macros_list
      - List of lists of Highlight_Macro objects to apply to
        incoming blocks, in order.
      - Items will be consumed as blocks arrive, until this list
        is empty.
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enabled = True
        self.line_macros_list = []
        return

    def Set_Line_Macros(self, line_macros_list):
        '''
        Record a list of lists of highlighting macros for upcoming
        lines. This will prefix one empty entry, since qt inserts
        a spurious blank text block when setPlainText is called.
        '''
        self.line_macros_list = [''] + line_macros_list
        return

    def highlightBlock(self, text):
        '''
        Apply highlights to the given text block that was
        recently changed.
        '''
        if not self.enabled:
            return
        
        # If macros are present use them for faster processing.
        if self.line_macros_list:
            macros = self.line_macros_list.pop(0)
        else:
            # Get some new macros.
            # It is fed just one line, and returns one sublist.
            macros = Get_Highlight_Macros([text])[0]

        for macro in macros:
            # Look up the format.
            format = Get_Format(macro.color)
            self.setFormat(macro.index, macro.length, format)
        return

        #-Removed; older code processing locally to this class.
        ## Default block state to 0 (no block quote active).
        #self.setCurrentBlockState(0)
        #
        ## Running offset in the text for where to start the next
        ## regex search from. This advances as matches are found.
        #offset = 0
        #
        #
        ## Start by detecting if a block quote was active.
        ## Block state will be 0 by default, or 1 for an open quote.
        #prior_state = self.previousBlockState()
        #if prior_state in self.block_quote_index_closer_dict:
        #
        #    # Grab the closing pattern.
        #    matcher = self.block_quote_index_closer_dict[prior_state]
        #    # Look up the format to use.
        #    format = self.formats[prior_state]
        #
        #    # Look for a match.
        #    index = matcher.indexIn(text, offset)
        #    if index == -1:
        #
        #        # No match, so highlight the entire line.
        #        self.setFormat(offset, len(text), format)
        #
        #        # Flag the block as still in a block quote.
        #        self.setCurrentBlockState(prior_state)
        #
        #        # Can either advance the offset all the way, or just
        #        # return. Go with offset advance, in case important
        #        # code is added later that might get skipped.
        #        offset = len(text)
        #
        #    else:
        #        # Highlight the matched section.
        #        length = matcher.matchedLength()
        #        self.setFormat(offset, length, format)
        #
        #        # Advance the offset. Regular matching will follow
        #        # from here.
        #        offset = length
        #
        #
        ## Convenience renaming.
        #matcher = self.macro_pattern
        #
        ## Loop until the regex returns -1, for no match.
        ## Each iteration will advance to the end of the match.
        #while 1:
        #    index = matcher.indexIn(text, offset)
        #    if index == -1:
        #        break
        #
        #    # Determine which group was captured.
        #    # The .cap() function takes an integer, the pattern capture group,
        #    # and return the text captured by that group.
        #    # Since groups are OR'd together, only one of them is likely 
        #    # to match, so most groups should return a blank.
        #    # Can loop until finding the first match, which also gives
        #    # earlier patterns higher priority.
        #    # Note: the implicit capture group [0] is for the whole pattern,
        #    # so include a +1 offset.
        #    for subpattern_index in range(len(self.formats)):
        #        match_text = matcher.cap(subpattern_index + 1)
        #        if match_text:
        #            break
        #    # Something should have matched.
        #    # This probably won't go awry in release code.
        #    assert match_text
        #
        #    # Look up the formatter for this subpattern.
        #    format = self.formats[subpattern_index]
        #    
        #    # Call the built-in function for formatting this length.
        #    length = matcher.matchedLength()
        #    self.setFormat(index, length, format)
        #    # Advance the offset for the next regex check, to the
        #    # match position plus length.
        #    offset = index + length
        #
        #    # If the subpattern index was for opening a block quote,
        #    # tag the block with the corresponding index.
        #    if subpattern_index in self.block_quote_index_closer_dict:
        #        self.setCurrentBlockState(subpattern_index)
        #
        #return

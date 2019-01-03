

from PyQt5.QtGui import QSyntaxHighlighter, QColor, QTextCharFormat, QTextCursor
from PyQt5.QtCore import QRegExp

class XML_Syntax_Highlighter(QSyntaxHighlighter):
    '''
    Apply syntax highlighting to xml files.
    TODO: also color lines with a difference between versions.

    Attributes:
    * enabled
      - Bool, if True then highlighting is enabled, else any
        automated calls to highlightBlock will return early.
    * macro_pattern
      - QRegExp holding all patterns joined together.
    * formats
      - List of QTextCharFormat objects holding the formatting to
        apply for each subpattern, in grouping order in the
        macro pattern.
    * block_quote_index_closer_dict
      - Dict, keyed by the opening block quote pattern index in
        the macro_pattern, holding the QRegExp pattern to use
        to close the block.
      - When a block quote is active, the current block will
        be assigned the index for the corresponding quote type
        that opened it.
      - May be extended to cover multiline quotes.
    '''
    # Define some colors for terms.
    # Pick colors from https://www.december.com/html/spec/colorsvg.html
    type_color_dict = {
        'keyword'   : 'blue',
        'comment'   : 'darkGreen',
        'string'    : 'purple',
        'attribute' : 'crimson',
        }    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.block_quote_index_closer_dict = {}
        self.enabled = True
        
        # Set up the cursor, attached to the document.
        self.cursor = QTextCursor(self.document())

        # Set up the various rules.
        rules = []
        
        # Comment detection, eg. <!-- and -->

        # Since highlighting is done a line at a time (newline separated),
        #  this will be a little tricky to carry state across lines, but
        #  can be done with previousBlockState and setCurrentBlockState.
        

        # Open and close on a single line.
        rules.append((r'<!--(?:.*)-->', self.type_color_dict['comment']))
            
        # Same, but proceeding until the end of the line.
        # These have some special handling to cross line boundaries
        # later. Note: newline could maybe be omitted, since the regex
        # runs one line at a time, but can keep it for safety.
        rules.append((r'<!--(?:[^\n]*)', self.type_color_dict['comment']))

        # Special closing rule.
        # This is specially handled, different than other rules.
        # Record the indices of these rules.
        self.block_quote_index_closer_dict[len(rules)-1] = QRegExp(r"(?:.*)-->")

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
                          .format(char), self.type_color_dict['string']))
            
        # TODO: maybe line-crossing quotes.
        # Similar to comments or the python multiline quotes, so mostly
        # just skipped here for laziness.

        # Node tags.
        # These are <tag> and </tag> and <tag/> and <tag ....>.
        # Look for char strings, "\w+", around the carrot options;
        # just copy out rules instead of making one complex one.
        rules.append((r'<\w+>', self.type_color_dict['keyword']))
        rules.append((r'<\w+/>', self.type_color_dict['keyword']))
        rules.append((r'<\w+' , self.type_color_dict['keyword']))
        rules.append((r'</\w+' , self.type_color_dict['keyword']))
               
        # Attribute tags.
        # \s for space, \w+ for a word, followed by =.
        rules.append((r'\s\w+=' , self.type_color_dict['attribute']))

        # Gather the regex patterns into a single macro pattern,
        # with capture groups for indexing final matches.
        macro_pattern = '(' + ')|('.join(p for p,c in rules) + ')'

        # There should be as many '(' as there are rules, when
        # omitting the non-capturing groups.
        assert macro_pattern.count('(') - macro_pattern.count('?:') == len(rules)
            
        # Wrap it.
        self.macro_pattern = QRegExp(macro_pattern)

        # Set up a list of formatters.
        self.formats = [self.Get_Format(c) for p, c in rules]

        return


    def Get_Format(self, color_str):
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
    

    def highlightBlock(self, text):
        '''
        Apply highlights to the given text block that was
        recently changed.
        '''
        if not self.enabled:
            return

        # Default block state to 0 (no block quote active).
        self.setCurrentBlockState(0)

        # Running offset in the text for where to start the next
        # regex search from. This advances as matches are found.
        offset = 0


        # Start by detecting if a block quote was active.
        # Block state will be 0 by default, or 1 for an open quote.
        prior_state = self.previousBlockState()
        if prior_state in self.block_quote_index_closer_dict:

            # Grab the closing pattern.
            matcher = self.block_quote_index_closer_dict[prior_state]
            # Look up the format to use.
            format = self.formats[prior_state]

            # Look for a match.
            index = matcher.indexIn(text, offset)
            if index == -1:

                # No match, so highlight the entire line.
                self.setFormat(offset, len(text), format)

                # Flag the block as still in a block quote.
                self.setCurrentBlockState(prior_state)

                # Can either advance the offset all the way, or just
                # return. Go with offset advance, in case important
                # code is added later that might get skipped.
                offset = len(text)

            else:
                # Highlight the matched section.
                length = matcher.matchedLength()
                self.setFormat(offset, length, format)

                # Advance the offset. Regular matching will follow
                # from here.
                offset = length


        # Convenience renaming.
        matcher = self.macro_pattern

        # Loop until the regex returns -1, for no match.
        # Each iteration will advance to the end of the match.
        while 1:
            index = matcher.indexIn(text, offset)
            if index == -1:
                break

            # Determine which group was captured.
            # The .cap() function takes an integer, the pattern capture group,
            # and return the text captured by that group.
            # Since groups are OR'd together, only one of them is likely 
            # to match, so most groups should return a blank.
            # Can loop until finding the first match, which also gives
            # earlier patterns higher priority.
            # Note: the implicit capture group [0] is for the whole pattern,
            # so include a +1 offset.
            for subpattern_index in range(len(self.formats)):
                match_text = matcher.cap(subpattern_index + 1)
                if match_text:
                    break
            # Something should have matched.
            # This probably won't go awry in release code.
            assert match_text

            # Look up the formatter for this subpattern.
            format = self.formats[subpattern_index]
            
            # Call the built-in function for formatting this length.
            length = matcher.matchedLength()
            self.setFormat(index, length, format)
            # Advance the offset for the next regex check, to the
            # match position plus length.
            offset = index + length

            # If the subpattern index was for opening a block quote,
            # tag the block with the corresponding index.
            if subpattern_index in self.block_quote_index_closer_dict:
                self.setCurrentBlockState(subpattern_index)

        return

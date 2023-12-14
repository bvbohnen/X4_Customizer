
from Framework.Documentation import Doc_Category_Default
_doc_category = Doc_Category_Default('GUI')

from PyQt5.QtGui import QSyntaxHighlighter, QColor, QTextCharFormat, QTextCursor
from PyQt5.QtCore import QRegExp

import Plugins

def Get_Plugin_Names():
    'Return a list with all plugin names.'
    name_list = []
    for item_name in dir(Plugins):
        item = getattr(Plugins, item_name)

        # Can check for the _plugin_type attribute, attached
        #  by the decorator.
        if not getattr(item, '_plugin_type', None):
            continue
        name_list.append(item_name)
    return name_list


'''
Apparently, after some source code poking, QSyntaxHighlighter takes 
the QTextDocument as an input during init, will attach its contentsChange
signal to a local _q_reformatBlocks function, which in turn gathers up a
block of text and calls highlightBlock automatically.
'''
'''
The general matching approach will differ from examples seen (and differ
from some python highlighting found online) to be more robust.
In particular, regex matching rules will be grouped together into
a macro-expression to be checked all at once, such that once a high
priority rule gets matched, its highlighting will take prededence over
all later rules over the match range.
This avoids a problem in the examples where, eg., keywords would get
highlighted inside comments.
'''
class Script_Syntax_Highlighter(QSyntaxHighlighter):
    '''
    Apply syntax highlighting to python script files.
    This will be mostly python style highlights, with maybe some
    tweaks for plugin names.
    Note: this will connect to the document's contentsChange signal;
    any other functions connected to this signal should be connected
    before the highlighter is attached if they might edit the text.

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
    '''
    # Define some colors for terms.
    # Pick colors from https://www.december.com/html/spec/colorsvg.html
    type_color_dict = {
        'keyword' : 'blue',
        'comment' : 'darkGreen',
        'string'  : 'crimson',
        'plugin'  : 'blueviolet',
        }

    # Python keywords.
    keywords = (
        'False'   ,  'class'    ,  'finally' ,  'is'       , 'return',
        'None'    ,  'continue' ,  'for'     ,  'lambda'   , 'try',
        'True'    ,  'def'      ,  'from'    ,  'nonlocal' , 'while',
        'and'     ,  'del'      ,  'global'  ,  'not'      , 'with',
        'as'      ,  'elif'     ,  'if'      ,  'or'       , 'yield',
        'assert'  ,  'else'     ,  'import'  ,  'pass'     ,
        'break'   ,  'except'   ,  'in'      ,  'raise'    ,
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enabled = True
        
        # Set up the cursor, attached to the document.
        self.cursor = QTextCursor(self.document())

        # Set up the various rules.
        rules = []
        
        # Comment detection.
        # Just a # until the end of the line.
        # Note: match this first, before others.
        rules.append((r'#[^\n]*', self.type_color_dict['comment']))
                

        # Strings.
        # Start with triple quotes as highest priority.
        # Since highlighting is done a line at a time (newline separated),
        #  this will be a little tricky to carry state across lines, but
        #  can be done with previousBlockState and setCurrentBlockState.
        
        # Triple quotes on a single line, optional 'r' prefix.
        # Handling escapes is a headache, so ignore that for now;
        # it will probably never come up.
        for char in ["'",'"']:
            rules.append((r'(?:\br)?{0}{0}{0}(?:.*){0}{0}{0}'
                          .format(char), self.type_color_dict['string']))
            
        # Same, but proceeding until the end of the line.
        # These have some special handling to cross line boundaries
        # later. Note: newline could maybe be omitted, since the regex
        # runs one line at a time, but can keep it for safety.
        for char in ["'",'"']:
            rules.append((r'(?:\br)?{0}{0}{0}(?:[^\n]*)'
                          .format(char), self.type_color_dict['string']))

        # Special closing rules: any character until the closing triple
        # quote. These are specially handled, different than other rules.
        # Record the indices of these rules.
        self.block_quote_index_closer_dict = {
            len(rules) -2 : QRegExp(r"(?:.*)'''"),
            len(rules) -1 : QRegExp(r'(?:.*)"""'),
            }

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
            

        # Keywords and plugins are straightforward.
        for word in self.keywords:
            # \b : matches blank space before/after a word.
            rules.append((r'\b{}\b'.format(word), self.type_color_dict['keyword']))
        for word in Get_Plugin_Names():
            rules.append((r'\b{}\b'.format(word), self.type_color_dict['plugin']))



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
        # Block state will be 0 by default, or the index of the active
        # quote type otherwise.
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

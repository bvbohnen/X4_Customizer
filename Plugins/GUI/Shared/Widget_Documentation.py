
from PyQt5.QtWidgets import QTextBrowser
from Framework.Make_Documentation import Merge_Lines, Remove_Line_Indents

class Widget_Documentation(QTextBrowser):
    '''
    Documentation display window.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)        
        return

    def setPlainText(self, text):
        '''
        Displays text, maybe after doing some formatting.
        '''
        # -Removed; this requires line wrap, and ends up looking
        #  really bad when markdown indents are lost.
        #text = Merge_Lines(text)
        # If not merging lines, still want to remove excess indentation.
        # This takes a line list, for now.
        line_list = [x for x in text.splitlines()]
        Remove_Line_Indents(line_list)
        text = '\n'.join(line_list)

        super().setPlainText(text)


    def mimeData(self, selections):
        '''
        Customize the dragged item to be somewhat formatted, for
        when examples are dragged to the script.
        '''
        mimedata = super().mimeData(selections)
        if selections:
            item = selections[0]

            # Add empty args and a newline for now.
            # TODO: maybe add named args and defaults; that would
            # take some inspection. Alternatively, could create
            # custom defaults for each transform.
            text = item.plugin.__name__ + '()\n'
            mimedata.setText(text)

        return mimedata

    # Nope, doesnt work.
    def QDrag(self, *args):
        return
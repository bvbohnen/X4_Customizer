
from PyQt5.QtWidgets import QTextBrowser
from ..Make_Documentation import Merge_Lines

class Widget_Documentation(QTextBrowser):
    '''
    Documentation display window.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)        
        return

    def setPlainText(self, text):
        '''
        Displays text, after doing some formatting.
        '''
        text = Merge_Lines(text)
        super().setPlainText(text)


    # See comments in Widget_Plugins for this.
    # TODO: doesn't work in brief testing, for whatever reason;
    # this is all super shady.
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
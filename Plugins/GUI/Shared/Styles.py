'''
Module for organizing available Qt styles.

For now, other styles will not be included in the release version
because the one of interest, QDarkStyleSheet, has an annoyingly
long license file, sadly, and not worth the time to read through
and copy/paste right now.

TODO: look into style sheets, which can paper over the style
and are maybe better than offering styles (which tend to be
pretty similar).

Side note: windows_nt style does not allow coloring the labels
in a table; try to default to Fusion if available.
'''
from Framework.Documentation import Doc_Category_Default
_doc_category = Doc_Category_Default('GUI')

from PyQt5 import QtWidgets

# Can get the available system styles from QStyleFactory.
builtin_style_names = list(QtWidgets.QStyleFactory.keys())

#style_sheet_names = []
#try:
#    import qdarkstyle
#    style_sheet_names.append('style_names')
#except:
#    pass


def Get_Style_Names():
    '''
    Returns a list of supported style names.
    '''
    return builtin_style_names


def Make_Style(style_name):
    '''
    Returns a QStyle object for the given style name.
    If the creation failed, returns None.
    '''
    try:
        if style_name in builtin_style_names:
            return QtWidgets.QStyleFactory.create(style_name)
    except Exception:
        return None

        
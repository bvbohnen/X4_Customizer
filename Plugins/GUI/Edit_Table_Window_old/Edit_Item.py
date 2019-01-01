
from PyQt5 import QtWidgets, QtGui, QtCore

class Widget_Edit_Item(QtWidgets.QLineEdit):
    '''
    Custom widget to handle items, trigging updates on a text change
    if the item was editable.

    Attributes:
    * version
      - String, version of the item value this widget displays.
    * item
      - Display_Item or Edit_Item attached to this widget.
      - Currently only 'edited' version widgets will have an item linked.
    * stylesheet
      - String, the current style sheet text.
    '''
    # Some static style terms.
    # This is a little too dark: 'background: lightGray;'
    #style_read_only = 'background: lightGray;'
    # These adjustments are surprisingly swingy; 250 is barely
    # darkened, 240 is super darkened. 247 seems okay.
    #style_read_only     = 'background: rgb(247, 247, 247);'
    #style_modified      = 'border-width: 1px; border-style: solid; border-color: red;'
    #style_modified  = 'background: lightBlue;'
    
    # Switching to use palletes; stylesheets are too bugged up in qt.
    pallete_standard = QtGui.QPalette()
    pallete_readonly = QtGui.QPalette()
    pallete_modified = QtGui.QPalette()
    pallete_mod_read = QtGui.QPalette()

    pallete_standard.setColor(QtGui.QPalette.Base, QtGui.QColor('white'))
    pallete_standard.setColor(QtGui.QPalette.Text, QtGui.QColor('black'))

    pallete_readonly.setColor(QtGui.QPalette.Base, QtGui.QColor(247, 247, 247))
    pallete_readonly.setColor(QtGui.QPalette.Text, QtGui.QColor('black'))

    pallete_modified.setColor(QtGui.QPalette.Base, QtGui.QColor('white'))
    pallete_modified.setColor(QtGui.QPalette.Text, QtGui.QColor('red'))
    
    pallete_mod_read.setColor(QtGui.QPalette.Base, QtGui.QColor(247, 247, 247))
    pallete_mod_read.setColor(QtGui.QPalette.Text, QtGui.QColor('red'))


    def __init__(self, parent, version, **kwargs):
        super().__init__(parent, **kwargs)
        self.version = version
        self.item = None
        #self.stylesheet = ''
        self.modified = False
        self.readonly = False
        self.pallete  = None

        if version == 'edited':
            self.editingFinished.connect(self.Handle_editingFinished)

        # For coloring modified text, need to hook into two places,
        #  textChanged for setText events, and something else for
        #  when the user edits the text (for some reason that is not
        #  captured by textChanged, though its documentation says/implies
        #  that it should be).
        self.textChanged.connect(self.Color_Modified_Items)
        self.editingFinished.connect(self.Color_Modified_Items)

        # Ran into issues dynamically changine the style sheet, since
        # apparently the font changes are applied to the style sheet
        # and get overwritten.
        # Instead, try out a more complex style sheet with conditional
        # properties for some display options, and only edit those
        # conditional bits.
        #old_sheet = self.styleSheet()
        #style_sheet = """
        #QLineEdit[readonly = "1"]{
        #    background-color: rgb(247, 247, 247);
        #}
        #QLineEdit[modified = "1"]{
        #    border-width: 1px; border-style: solid; border-color: red;
        #}
        #"""
        #self.setProperty('readonly','1')
        #self.setProperty('modified','0')
        #self.setStyleSheet(style_sheet)
        #old_sheet = self.styleSheet()
        

        self.setAutoFillBackground(True)        
        # Default to readonly, after style is set up.
        self.setReadOnly(True)
         
        return


    #def Add_Style(self, style_text):
    #    '''
    #    Add the given text to the style sheet, if not present already.
    #    Text should end in a ';' always.
    #    '''
    #    if style_text not in self.stylesheet:
    #        self.stylesheet += style_text
    #    #self.setStyleSheet(self.stylesheet)
    #    return
    #
    #
    #def Remove_Style(self, style_text):
    #    '''
    #    Remove the given text from the style sheet.
    #    '''
    #    if style_text in self.stylesheet:
    #        self.stylesheet = self.stylesheet.replace(style_text,'')
    #    #self.setStyleSheet(self.stylesheet)
    #    return
    

    def Update_pallete(self):
        '''
        Based on the read-only and modified state, sets a pallete
        for this widget.
        '''
        if self.readonly == False and self.modified == False:
            pallete = self.pallete_standard
        if self.readonly == False and self.modified == True:
            pallete = self.pallete_modified
        if self.readonly == True  and self.modified == False:
            pallete = self.pallete_readonly
        if self.readonly == True  and self.modified == True:
            pallete = self.pallete_mod_read

        # Note: the pallete attribute in the documentation doesn't
        # seem to be accessible easily, so store a local copy.
        if self.pallete != pallete:
            self.pallete = pallete
            self.setPalette(pallete)
        return


    def setReadOnly(self, readonly = True):
        '''
        Set or disable the 'read only' state on this box.
        This may also attempt to grey out read only boxes for visual
        clarity.
        '''
        super().setReadOnly(readonly)
        # TODO: how to dim the widget?
        # Using setEnabled(not readonly) will do the job, but it makes
        # the text unselectable (so it can't copy/paste or drag over to
        # the editable boxes), and greys a bit too much.
        # -Look into using a style sheet.
        if readonly:
            #self.Add_Style(self.style_read_only)
            #self.setProperty('readonly','1')
            self.readonly = True
        else:
            #self.Remove_Style(self.style_read_only)
            #self.setProperty('readonly','0')
            self.readonly = False
            
        #self.ensurePolished()
        self.Update_pallete()
        # TODO: highlight text in some way for modified fields.
        return


    def Set_Item(self, item):
        '''
        Change the Edit_Item or Display_Item (or None) attached
        to this widget. Updates text display and readonly state.
        Links to the item if this is the 'edited' widget.
        '''
        # Handle linking to edited versions first, before updating
        # text, so that modified text coloring will work correctly.
        if self.version == 'edited':
            # The edited widget will set a placeholder with the patched value,
            # and then may fill its text if there is any edited value in the
            # item.
            # -Removed; this doesn't quite work out; the edited field will
            # default to the patched value instead for easier display updates.
            #if item == None:
            #    patched_value = None
            #else:
            #    patched_value = item.Get_Value('patched')
            #self.setPlaceholderText(patched_value)

            # Set as editable if there is an item and it is not read only.
            if item != None and item.read_only == False:
                self.setReadOnly(False)
            else:
                self.setReadOnly(True)
                
            # Handle item/widget linking for the edited widget.

            # Two way link.
            self.item = item
            if item != None:
                item.Set_Widget(self)
        
        # Look up the item's value for this key, which will
        # match version names. This may return None for the
        # edited value if no edits are available. It may return
        # None for other versions if the field is unused by
        # the object for this row.
        # Note: the item itself may be None, in which case just
        # leave this blank. (This could come up if, eg. a patch
        # added an xml attribute that the vanilla version lacks.)
        if item == None:
            item_value = None
        else:
            item_value = item.Get_Value(self.version)
                
        if item_value != None:
            self.setText(item_value)
        else:
            self.setText('')

        return
    
    # Add a signal for requesting the parent window redraw.
    redraw_request = QtCore.pyqtSignal()

    def Handle_editingFinished(self):
        '''
        Handle cases when the user clicks out of a box.
        Note: this will trigger even if the widget is readonly and
        not actually clickable, for whatever reason.
        '''
        # Ignore if read only.
        if self.isReadOnly():
            return
        # TODO: Check if the text has actually been modified.
        # For now, just always update.
        # Send the text to the item.
        if self.item != None:
            # This will handle clearing and refreshing dependents.
            self.item.Set_Edited_Value(self.text())

            # If this item was a reference, the entire table should
            # be redrawn to swap it out for the new ref'd object.
            # Do this last, because when this finishes the item
            # will have been swapped out.
            if self.item.is_reference:
                self.redraw_request.emit()
        return
    

    def setText(self, text):
        '''
        Wrapper on setText that will call Color_Modified_Items, because
        the textChanged doesn't follow its documentation and catch
        such calls on its own.
        '''
        super().setText(text)
        self.Color_Modified_Items()
        return


    def Color_Modified_Items(self):
        '''
        This should be called whenever the text changes.
        Will color the box and/or text if the linked item is in a modified
        state.
        '''
        # In case this is called without an item attached, return
        # early with no highlight.
        if not getattr(self, 'item', None):
            self.modified = False
            #self.Remove_Style(self.style_modified)

        # Note: readonly items can still be modified in the case of display
        # values that source from modified values, so only check the
        # modified state.
        elif self.item.Is_Modified():
            #self.Add_Style(self.style_modified)
            #self.setProperty('modified','1')
            self.modified = True
        else:
            #self.Remove_Style(self.style_modified)
            #self.setProperty('modified','0')
            self.modified = False
            
        #self.ensurePolished()
        self.Update_pallete()
        return
    


    
'''
Notes on font/stylesheet headaches:

    - It seems that this widget only inherits font when created
      if it has a non-empty style sheet applied; later setFont calls
      to the parent don't reach the children.

    - Conditional styles (QLineEdit[readonly = "1"]{...}) do not seem
      to work; maybe examples are out of date.
      Or maybe this is nonfunctional for dynamic changes, and only
      works at init (though examples imply it working at runtime).
      Docs suggest removing and reapplying the stylesheet on
      a Qt property change.
      However, these still mess up the fonts even when not working as wanted.

    - Can maybe try psuedo states for ":read-only", though highlighting
      edited boxes won't work out so well.

    - Readonly items seem to somewhat preserve their starting font.
    - Modified items do not, even when also just changing background color.

    - Initial 'styleSheet()' is a blank string.
    - Setting a blank style sheet doesn't cause problems.

    - When just using the modified highlight, the very first
      setStyleSheet did not change the font, but removing the
      style (setStyleSheet('')) did.
      Packing the empty sheet in "QLineEdit{}" did not matter.

    - Maybe some fluff stylesheet term can help, acting as a placeholder
      so that an empty string is never used?
      - Didn't help.

    - Maybe ensure style properties are never removed.
      - Didn't help.

    - Spam clicking on cells also causes other oddities, like readonly
      cells with no item getting highlighted as modified somehow.

    - Maybe set styles to have two alternate versions, which both
      set the same fields?
      - Didn't help.

    - Supposition: whenever a widget has a stylesheet set that is not
      blank, some internal piping gets broken and the widget can no
      longer inherit font properly on later calls.
      Hard to see how this could be intentional, so consider a qt bug.  

    - Maybe look into palletes? or setBackgroundRole or similar?
      https://wiki.qt.io/How_to_Change_the_Background_Color_of_QWidget
      Success!  finally...
'''


from Framework.Documentation import Doc_Category_Default
_doc_category = Doc_Category_Default('GUI')

from pathlib import Path
from PyQt5 import QtWidgets
from Framework import Settings
from ..Shared.Misc import Set_Icon

class Widget_Settings(QtWidgets.QGroupBox):
    '''
    Group box with a grid layout, to be filled with settings
    labels and widgets (text edit fields, on/off buttons).

    Attributes:
    * field_widget_dict
      - Dict, keyed by Settings field name, holding the widget
        responsible for it, either a QLineEdit or QButtonGroup.
    * modified
      - Bool, if True the settings were modified since last being
        loaded or saved.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modified = False
        # Gather the settings fields into a dict, paired up with the
        # widgets to edit them.
        self.field_widget_dict = {}

        # Set up a new layout, form style (rows with 2 columns).
        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)
                
        # Get the settings defualt values.
        defaults = Settings.Get_Defaults()


        def Setup_Modification_Listener(widget, field):
            '''
            Sets the widget changed signal to call the Handle_Widget_Actions
            function, passing along the field changed.
            '''
            if isinstance(widget, QtWidgets.QLineEdit):
                widget.editingFinished.connect(
                    # Use the default name trick to ensure the field
                    # gets through the lambda construction.
                    lambda field = field: self.Handle_Widget_Modification_Signals(field))

            elif isinstance(widget, QtWidgets.QRadioButton):
                widget.clicked.connect(
                    # Catch and ignore the 'clicked' boolean that
                    # is normally emitted.
                    lambda clicked, field = field: self.Handle_Widget_Modification_Signals(field))
            return


        # Set up widgets.
        # Use the categorized and ordered fields.
        for category, field_list in Settings.Get_Categorized_Fields().items():

            # Create a fluff row with just the category.
            # This apparently needs to be a widget, not just raw text,
            # to span both columns and accept richtext format;
            # though QString is who knows where, so try using setText
            # of the label for richtext detection.
            # Bold this.
            layout.addRow(QtWidgets.QLabel('<b>'+category+'</b>'))

            for field in field_list:
                default = defaults[field]

                # Create an edit widget:
                # - Text box for paths
                # - Buttons for booleans
                # Test for bool.
                if isinstance(default, bool):

                    # Looking to set up yes/no/default buttons.
                    # Can apparently use QRadioButton objects for this,
                    # gathered in a QButtonGroup, which will automatically
                    # handle exclusivity and provides state lookup,
                    # though is not actually a widget and doesn't have
                    # layout, so need to nest it inside a QGroupBox with
                    # a layout that has the QButtonGroup that holds
                    # the QRadioButtons. (omg why...)
                    widget = QtWidgets.QGroupBox()
                    this_layout = QtWidgets.QHBoxLayout()
                    widget.setLayout(this_layout)

                    button_t = QtWidgets.QRadioButton('true')
                    button_f = QtWidgets.QRadioButton('false')
                    # Try to keep this label shortish.
                    button_d = QtWidgets.QRadioButton('default ({})'.format(
                        't' if default else 'f'))
                    # Set default enabled by default.
                    # TODO: Move this to Restore_Defaults, and call that
                    # when done.
                    button_d.setChecked(True)
                    # Attach python values to the buttons, for ease of use.
                    button_t.py_value = True
                    button_f.py_value = False
                    button_d.py_value = None

                    # Set these not to save across sessions, to avoid
                    # restored session data overwriting any loaded
                    # values from config.
                    button_t.do_not_save = True
                    button_f.do_not_save = True
                    button_d.do_not_save = True
                    

                    # Listen to the clicked signals.
                    # TODO: use the button group signal.
                    Setup_Modification_Listener(button_t, field)
                    Setup_Modification_Listener(button_f, field)
                    Setup_Modification_Listener(button_d, field)

                    button_group = QtWidgets.QButtonGroup()

                    # Give these integer indexes, positive.
                    # Make somewhat sensible.
                    button_group.addButton(button_f, 0)
                    button_group.addButton(button_t, 1)
                    button_group.addButton(button_d, 2)
                    # Annotate with a reverse lookup dict.
                    button_group.button_dict = {
                        True  : button_t,
                        False : button_f,
                        None  : button_d,
                        }

                    this_layout.addWidget(button_t)
                    this_layout.addWidget(button_f)
                    this_layout.addWidget(button_d)
                    
                    # Though not the top widget, treat the button group
                    # as the main widget, since the group and layout are
                    # just fluff.
                    self.field_widget_dict[field] = button_group
                    button_group.default = default


                # Non-bools are either Paths, strings, or None (for optional
                # paths or strings).
                else:
                    widget = QtWidgets.QLineEdit()

                    # Don't save contents across sessions.
                    widget.do_not_save = True

                    # Treat default text as a placeholder.
                    widget.setPlaceholderText(str(default))
                    
                    # Listen to changes.
                    Setup_Modification_Listener(widget, field)

                    # Record the field:widget pair.
                    self.field_widget_dict[field] = widget
                    widget.default = default
                    
                    # Can pick out paths based on their prefix.
                    if field.startswith('path_'):
                        # This will wrap the text box in a group with
                        # a horizontal layout and a button to open the
                        # file dialog.
                        group = QtWidgets.QGroupBox()
                        this_layout = QtWidgets.QHBoxLayout()
                        group.setLayout(this_layout)

                        button = QtWidgets.QPushButton()
                        # Give a nice icon.
                        Set_Icon(button, 'SP_DirIcon')

                        # Stick the icon on one side or the other.
                        # Can go with left side, since icons are small,
                        # though text would want to go on the right.
                        this_layout.addWidget(button)
                        this_layout.addWidget(widget)

                        # Hook up the button activation signal, which
                        # will pass along the config field being changed.
                        button.clicked.connect(
                            lambda clicked, 
                            field = field : self.Open_File_Dialog(field) )
                        
                        # Rename the top widget for adding to the row.
                        widget = group

                # Set up a new layout row.
                layout.addRow(field, widget)


       
        # Make sure Settings loaded the Json file, and get what fields
        #  it loaded. This is needed to know which values should not
        #  be set to default, particularly when a specified path
        #  exactly matches the default (which can be a problem if
        #  defaults are changed in future versions).
        non_default_fields = Settings.Load_Json()
        
        # For each of these, set up the widgets into a non-default
        # state.
        for field in non_default_fields:
            # Look up the current setting.
            value = getattr(Settings, field)
            # Pick the widget to edit.
            widget = self.field_widget_dict[field]

            # Edit based on type.
            if isinstance(widget, QtWidgets.QLineEdit):
                # Fill in with a string version of the setting.
                widget.setText(str(value))

            elif isinstance(widget, QtWidgets.QButtonGroup):
                # Value should be a bool, for easy dict lookup.
                assert isinstance(value, bool)
                widget.button_dict[value].setChecked(True)
            
        return
    

    def Load_Settings(self):
        '''
        Load the current Settings values into the gui.
        For use at startup, and maybe if changes are ever cancelled
        without saving.
        TODO: fill in if needed
        '''


    def Restore_Defaults(self):
        '''
        Restore all settings to their Settings defaults.
        TODO: fill in if needed
        '''
        # Two options:
        #  1 Tell Settings to go back to its defaults, then load
        #    them back into here.
        #  2 Apply the widget default values to Settings, and then
        #    set widget states back to default.
        #  3 Ignore this and let settings always persist.


    def Store_Settings(self):
        '''
        Update all global Settings with the current selections,
        either overwriting or restoring defaults.
        This should be called after a script runs, in case it did
        local settings edits.
        '''
        # Work through all the widgets with their settings fields.
        for field in self.field_widget_dict:
            self.Update_Settings_Field(field)
        # Reset the Settings, so that it will do path checks again
        # when next used; this should be relatively harmless if
        # a non-path setting was changed.
        Settings.Reset()
        return


    def Update_Settings_Field(self, field):
        '''
        Update the Settings with the current widget for the given field.
        '''
        if field not in self.field_widget_dict:
            self.window.Print('Error when setting field {}'.format(field))
            return
        widget = self.field_widget_dict[field]
        
        # Handle based on widget type.
        if isinstance(widget, QtWidgets.QLineEdit):
            # TODO: How to know when to Path convert, and if it is
            #  a valid path?
            # -Maybe have a Settings function to polish paths, or just
            #  re-call the Settings Delayed_Init code.
            # Only save if text is present.
            if widget.text():
                setattr(Settings, field, widget.text())
            else:
                setattr(Settings, field, widget.default)

        elif isinstance(widget, QtWidgets.QButtonGroup):
            # Use the value, None/True/False.
            value = widget.checkedButton().py_value
            if value != None:
                setattr(Settings, field, value)
            else:
                setattr(Settings, field, widget.default)

        # Special cases.
        # TODO: move to Load_Settings and call that.
        if field == 'show_tab_close_button':
            self.window.Show_Tab_Close_Button(getattr(Settings, field))
        return


    def Save(self):
        '''
        Save the current settings to a json file, and update the
        Settings object.
        '''
        # Make sure settings are up to date.
        # There was a corner case where a text box was being edited
        # when the gui window is closed, that would miss the settings
        # update while having the next text show up here; this call
        # clears up that problem.
        self.Store_Settings()

        # Gather which fields need saving.
        fields_to_save = []
        for field, widget in self.field_widget_dict.items():

            save = False
            # Handle text fields.
            if isinstance(widget, QtWidgets.QLineEdit):
                # If any text is filled in, treat it as non-default.
                if widget.text():
                    save = True

            elif isinstance(widget, QtWidgets.QButtonGroup):
                # Pick out which button is pressed, and get the py value.
                # If not None (default), save.
                if widget.checkedButton().py_value != None:
                    save = True

            if save:
                # Record the field name.
                fields_to_save.append(field)

        # Write the json file.
        # The Settings should already have the correct values applied.
        Settings.Save_Json(fields_to_save)
        self.modified = False
        self.window.Print('Saved config settings')
        return


    def Handle_Widget_Modification_Signals(self, field):
        '''
        Handle events when widgets are modified.
        TODO: stop this from triggering every time the window is tabbed
        away from.
        TODO: get this to trigger if a text field is being edited
        when the gui is closed (causes an oddity in this case
        with the text() of the widget being changed, but the settings
        not having been updated).
        '''
        self.modified = True

        # Update the field that was edited.
        self.Update_Settings_Field(field)

        # Reset the Settings, so that it will do path checks again
        # when next used; this should be relatively harmless if
        # a non-path setting was changed.
        Settings.Reset()

        # For now, don't worry about resaving yet; that isn't normally
        # needed until the gui is closed.
        return


    def Open_File_Dialog(self, field):
        '''
        Handle 'browse' button presses.
        '''
        # Get the current text in the box, if any, to use as
        # an initial dir.
        text = self.field_widget_dict[field].text()
        if Path(text).exists():
            start_dir = text
        else:
            start_dir = None

        # Get the path from the dialogue.
        path_str = QtWidgets.QFileDialog.getExistingDirectory(
            directory = start_dir)

        # If the file path is empty, the user cancelled the dialog.
        if not path_str:
            return
        
        # Dump the text into the widget.
        self.field_widget_dict[field].setText(path_str)
        # Treat it as if modified by user.
        self.Handle_Widget_Modification_Signals(field)
        
        return


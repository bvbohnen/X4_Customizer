'''
Top level of the GUI.

Notes:
- Layout made with Qt designer.
- Widgets organized using custom classes.
    In Designer, promote a widget to the custom name, and give
    the import path as Framework.GUI.<module name>, since relative
    paths don't work out however the ui file is being loaded,
    and this direct import will work since the sys path is setup
    already.
'''
from pathlib import Path

# Needed modules are kinda scattered all over, and get moved around
# between versions.
# The only (rough) documentation is at:
# http://pyqt.sourceforge.net/Docs/PyQt5/modules.html
from PyQt5.QtGui import QFont
from PyQt5.uic import loadUiType
from PyQt5 import QtWidgets, QtCore

from Framework import Settings
from Framework import Print
from Framework import Change_Log
from Framework import Live_Editor

from .Worker_Thread_Handler import Worker_Thread_Handler
from .Shared import Styles, Set_Icon
from Framework.Common import home_path

# Different tab window types.
# Include base classes, so they can be used in isinstance checks.
#from .Edit_Table_Window import Edit_Table_Window
from .Edit_View_Window   import Edit_View_Window
from .Extensions_Window  import Extensions_Window
from .Settings_Window    import Settings_Window
from .Script_Window      import Script_Window
from .Shared             import Tab_Page_Widget
from .VFS_Window         import VFS_Window
from .File_Viewer_Window import File_Viewer_Window


# Load the .ui file into a reuseable base class.
# This will return the designer generated class ("form"), and
# the Qt base class it is based on (QWidget in this case).
# http://pyqt.sourceforge.net/Docs/PyQt5/designer.html
gui_file = Path(__file__).parent / 'x4c_gui_layout.ui'
generated_class, qt_base_class = loadUiType(str(gui_file))


# Reference to the main qt window, for use when it is needed
# but lookups are otherwise awkward.
qt_application = None
    
def Start_GUI():
    '''
    Start up the GUI main window. Returns after the gui is closed.
    '''
    global qt_application
    # Create a new Qt gui object.
    qt_application = QtWidgets.QApplication([])

    # Create the custom gui window itself, and set it to be shown.
    # Presumably this will get attached automatically to the 
    # QApplication object.
    # To be able to changes styles, give this a link back to the app.
    global main_window
    main_window = GUI_Main_Window(qt_application)

    # Launch the QApplication; this will halt execution until the gui exits.
    return_value = qt_application.exec()

    # There is no post-gui cleanup for now, so just return.
    return return_value


class Custom_Settings(QtCore.QSettings):
    '''
    QSettings wrapper which will fix responses, mainly translating
    types appropriately that others are returned as strings.
    '''
    replacements_dict = {
        'true'  : True,
        'false' : False,
        }

    def value(self, field, default = None, type = None):
        '''
        Look up and return the value.

        * default
          - Value to return if fields isn't found.
        * type
          - String, type to convert the value into.
          - Supports 'bool', 'int', others as needed.
        '''
        value = super().value(field, None)
        # Apparently pyqt screwed up comparisons here, and has the
        # qbytearray == None as True; use 'is' to be safer.
        if value is None:
            return default

        if type == 'bool':
            # Start with translating 'true' and 'false'.
            if value in self.replacements_dict:
                value = self.replacements_dict[value]
            # Run through bool() for anything else.
            return bool(value)

        # Simple int cast.
        elif type == 'int':
            return int(value)

        # Normal return value.
        return value


class Tab_Properties:
    '''
    Container for per-tab properties at the main window level.
    These should be saved between sessions, and used to restore
    tabs in a new session.
    This tracker will be annotated to any created widget
    as 'tab_properties'.

    Attributes:
    * window
      - The main window, that should have a widget_tab_container child.
    * label
      - String, label for the tab.
      - May be repeated across tabs, so don't treat as unique.
    * class_name
      - String, name of the widget class for the tab.
      - Eg. 'Script_Window','Settings_Window','Edit_View_Window', etc.
      - Can be matched to the actual class object to build the tab widget.
    * kwargs
      - Dict, any construction arguments to use when building the tab.
    * widget
      - The constructed tab widget, after Make_Widget has been called.
    * unique
      - Bool, if True then other tabs of the same class_name should
        not be created, and it should only be hidden instead of deleted.
      - Not used here, mearly annotation to check elsewhere.
    * index
      - Int, the last known index of the tab in the tab container.
      - May not always be up to date, and mainly is used when hiding
        and restoring tabs.
    * hidden
      - Bool, if True then this widget is in a hidden state, eg. detached
        from the tab container.
    '''
    def __init__(
            self,
            window,
            label = None,
            class_name = None,
            kwargs = None
        ):
        self.window     = window
        self.label      = label
        self.class_name = class_name
        self.kwargs     = {} if not kwargs else kwargs
        self.widget     = None
        self.unique     = False
        self.index      = None
        self.hidden     = False
        return

    def Save_Session_Settings(self, settings):
        '''
        Save details of the tab construction to the current QSettings.
        The appropriate settings group should have been opened already.
        '''
        # Try to avoid names that might conflict with what the
        # widget might save.
        settings.setValue('tab_label'     , self.label)
        settings.setValue('tab_class_name', self.class_name)
        settings.setValue('tab_kwargs'    , self.kwargs)
        settings.setValue('tab_hidden'    , self.hidden)
        settings.setValue('tab_unique'    , self.unique)
        settings.setValue('tab_index'     , self.index)
        # Pass on the call to the widget itself.
        self.widget.Save_Session_Settings(settings)
        return


    def Load_Session_Settings(self, settings):
        '''
        Restore details of the tab construction from the current QSettings.
        The appropriate settings group should have been opened already.
        The tab will be created for the main window before being
        internally restored.
        '''
        self.label      = settings.value('tab_label')
        self.class_name = settings.value('tab_class_name')
        self.kwargs     = settings.value('tab_kwargs')
        self.hidden     = settings.value('tab_hidden', False, type = 'bool')
        self.unique     = settings.value('tab_unique', False, type = 'bool')
        self.index      = settings.value('tab_index', 0, type = 'int')
        # Checks that the settings had the right stuff.
        assert self.label
        assert self.class_name
        assert isinstance(self.kwargs, dict)
        self.Get_Widget()
        self.widget.Load_Session_Settings(settings)
        return


    def Get_Widget(self):
        '''
        Returns the associated widget. Constructs it if needed.
        '''
        # As a safety, do nothing if the widget exists.
        if self.widget != None:
            return self.widget

        # Start by looking up the class name.
        # It should have been imported into globals.
        class_builder = globals()[self.class_name]

        # Create it with no parent (do not use the window as parent).
        self.widget = class_builder(
            parent = None, window = self.window, **self.kwargs)
        self.widget.tab_properties = self
        
        return self.widget



class Custom_Tab_Bar(QtWidgets.QTabBar):
    '''
    A customized tab bar for a tab widget, which will emit a
    tab close request on a middle mouse button click.
    To be attached to a tab widget using .setTabBar(Custom_Tab_Bar()).

    Note: hook directly into the tab bar tabCloseRequested signal,
    and not that of the tab widget, since it will suppress the signal
    when close buttons are disabled.
    '''
    def mouseReleaseEvent(self, event):
        'Intercept mouse button releases.'
        # Check the button pressed for middle mouse.
        if event.button() == QtCore.Qt.MidButton:
            # Emit the tab close signal.
            # Send with it the tab index, pulled using tabAt
            # the mouse press location.
            tab_index = self.tabAt(event.pos())
            self.tabCloseRequested.emit(tab_index)
        # Continue with normal button handling.
        # This should be safe; the tab won't get removed until after
        # the emit is handled, after this function returns.
        super().mouseReleaseEvent(event)
        return


class GUI_Main_Window(qt_base_class, generated_class):
    '''
    Custom Gui class object, as a child of the QMainWindow class.

    Widget names:
    * widget_tab_container
    * widget_output_dock

    Attributes:
    * application
      - Link back to the parent QApplication object.
    * startup_complete
      - Bool, False during init, True afterward.
    * current_font
      - QFont object specifying the current primary display font.
      - This may differ from the main window .font().
    * current_style
      - Name of the current QStyle in use.
    * session_memory
      - Custom_Settings(QSettings) object which will handle saving and
        reloading window settings.
    * tab_properties_list
      - List holding Tab_Properties objects.
      - List order will match the actual tab order.
      - If tabs are ever reordered, this should be updated to match
        the new order.
    * tabs_dict
      - Dict, keyed by tab name, holding the tab widgets.
      - For convenient lookups from other locations.
    * worker_thread
      - Worker_Thread_Handler that will be used to run scripts, plugins,
        and other framework functions that might take some time to return.
      - All widgets should share this thread, queueing requests to
        avoid framework collisions.
    * unique_tabs_dict
      - Dict, keyed by tab name, holding unique widgets to display as tabs.
      - These may not actually be present in the tab widget, such as
        when hidden.
    '''
    '''
    Scrapped: signals like this get messy: if 'loaded' and 'modified'
    are emitted (from a tab that did both), listeners will often do
    a double-refresh (wasteful). Alternatives are to combine signals
    into one macro signal with a series of flags (kinda clumsy), or
    to skip signals entirely and just do function calls to the main
    window (as done before thinking of signals).
    The function calls also allow prioritizing the viewed tab
    for updates, and are no more (maybe less) complicated to manage,
    so signals are skipped in favor of functions.

    Signals (emitted from child tabs, which may emit multiple):
    * sig_file_system_reset
      - Emitted when the File_System is reset completely, as well
        as once at startup to init all tabs.
      - Tabs should generally do a full refresh if they present
        data from the file system.
    * sig_files_modified
      - Emitted when a tab performed some function that may modify
        files in the file system.
      - Tabs should do a soft refresh if they present modified data from
        the file system.
    * sig_files_loaded
      - Emitted when a tab performed a game file loading, but did not
        do modification.
      - Tabs only need to reset if they are conditioned on which
        files are loaded, eg. the VFS.
    '''
    # Signal defs.
    sig_file_system_reset = QtCore.pyqtSignal()
    sig_files_modified    = QtCore.pyqtSignal()
    sig_files_loaded      = QtCore.pyqtSignal()

    def __init__(self, application):
        # Init the QMainWindow.
        super().__init__()
        self.setupUi(self)

        # This icon is kinda like and X.
        # TODO: maybe extract the x4 exe icon, though that will only
        # work on windows.
        # https://stackoverflow.com/questions/1616342/best-way-to-extract-ico-from-exe-and-paint-with-pyqt
        Set_Icon(self, 'SP_DialogCloseButton')

        self.startup_complete = False
        self.application = application
        self.current_font = None
        self.current_style = None
        self.unique_tabs_dict = {}

        # Set up the custom tab bar.
        self.widget_tab_container.setTabBar(Custom_Tab_Bar())
        self.widget_tab_container.tabBar().tabCloseRequested.connect(self.Close_Tab)
        # The custom bar overwrites some settings from qt designer,
        # so fix them here for now.
        self.widget_tab_container.setMovable(True)
        
        # Set up a QSettings object, giving it the path to where
        # the settings are stored. Set it as an ini file, since otherwise
        # it wants to make a mess in the registry.
        self.session_memory = Custom_Settings(
                str(home_path / 'gui_settings.ini'),
                QtCore.QSettings.IniFormat)

        # Set the title with version.
        # -Removed; a little tacky.
        #self.setWindowTitle('X4 Customizer {}'.format(Change_Log.Get_Version()))
        
        
        # Set the Framework to print to the gui.
        # Note: when running a script, the thread will handle
        # intercepting print statements and emit a signal.
        Print.logging_function = self.Print

        # Set how many lines the output will store.
        self.widget_output.setMaximumBlockCount(200)
        
        # Add a threading object.
        self.worker_thread = Worker_Thread_Handler(self)
        # Sends its emitted messages to Print.
        self.worker_thread.send_message.connect(self.Print)
        

        # Connect actions to handlers.
        self.action_Quit          .triggered.connect(self.Action_Quit)
        self.action_Change_Font   .triggered.connect(self.Action_Change_Font)
        self.action_View_Output   .triggered.connect(self.Action_View_Output)
        # TODO: Quit without saving

        # Actions that show/hide unique tabs.
        for action_name, class_name in [
            ('action_View_Script'  , 'Script_Window'),
            ('action_View_Settings', 'Settings_Window'),
            ]:
            action = getattr(self, action_name)
            action.triggered.connect(
                lambda qtjunk, 
                class_name = class_name: 
                self.Show_Hide_Tab(class_name))
            
        # Actions that go straight to tab openers.
        for action_name, class_name, label in [
            ('action_VFS', 'VFS_Window', 'VFS'),
            ('action_Extensions', 'Extensions_Window', 'Extensions'),            
            ]:
            action = getattr(self, action_name)
            action.triggered.connect(
                lambda qtjunk, 
                class_name = class_name,
                label = label : 
                self.Create_Tab(class_name, label))


        # Set up the styles menu.
        # This is done programatically, not in the gui file.
        self.Init_Styles()
        # Set a default font, prior to loading prior settings.
        self.Init_Font()
        # Init some tab options.
        self.Init_Live_Editor_Tab_Options()

        # Restore the settings.
        self.Load_Session_Settings()
        

        # Set up initial tabs, if they weren't restored.
        # These should always be present, even if hidden, and can be
        # referenced by other tabs if needed.
        # TODO: maybe rename existing tabs if found, to be able to
        #  clarify across version changes.
        # Note: these insert at index 0, so have the last one be the
        #  tab that should go first.
        for index, (class_name, label) in enumerate([
                # Trying out naming this different than Settings, to avoid
                # confusion with the gui "settings" menu.
                ('Settings_Window' ,'Config'),
                # Main script window. TODO: try calling "Main Script"
                ('Script_Window'   ,'Script'),
            ]):

            # Need to create it if it is not tracked.
            if class_name not in self.unique_tabs_dict:

                # Place it near the left of the tab bar.
                # This can be handy if adding new unique tabs to an older
                # session, so they go on the left.
                # The user can still move them away, and get their moved
                # position restored through session settings.
                widget = self.Create_Tab(class_name, label, index = 0)
                
                # Flag as unique.
                widget.tab_properties.unique     = True

                # Record it for hiding/showing.
                self.unique_tabs_dict[class_name] = widget

            else:
                widget = self.unique_tabs_dict[class_name]
                # Need to update using an index, annoyingly.
                index = self.widget_tab_container.indexOf(widget)
                # Refine the label.
                self.widget_tab_container.setTabText(index, label)
               

        # TODO: maybe resort the above to be at the start of the
        # tab listing, but that isn't critical for now.

        # Display the GUI.
        self.show()

        # Kick off a file system refresh.
        # Skip this when not using threads, since it extends gui startup
        # by too much.
        if not Settings.disable_threading and Settings.Paths_Are_Valid():
            self.Send_Signal('file_system_reset')

        # Flag startup as completed.
        # This will allow later created tabs to refresh themselves
        # when added.
        self.startup_complete = True
        return

        
    def Print(self, line):
        '''
        Prints a line to the output widget.
        '''
        self.widget_output.appendPlainText(line)
        return


    def Action_View_Output(self):
        '''
        View Output was selected from the menu.
        For now, just toggle the visibility.
        TODO: Maybe add a checkbox to the menu item, though that
        has some complexity for syncing with state restoration.
        TODO: fix bug with output dock that causes it to lose memory of
        sizing when toggled off/on.
        '''
        #checked = self.action_View_Output.isChecked()
        self.widget_output_dock.setVisible(not self.widget_output_dock.isVisible())
        return


    ##########################################################################
    # Tab related actions.

    def Init_Live_Editor_Tab_Options(self):
        '''
        Check the live editor for registers edit_tree_view builder
        functions, and use them to set up the edit tab options
        on the menu.
        '''
        table_names = Live_Editor.Get_Available_Tree_Names()
        for name in sorted(table_names):
            # Remove any underscores and uppercase the table name.
            title = name.replace('_',' ').title()
            action = self.menuEdit.addAction(title)
            
            # Set up the trigger.
            # See Init_Styles for further comments on this.
            action.triggered.connect(
                lambda qtjunk, 
                # Record the live editor function to call.
                class_name = 'Edit_View_Window',
                label = title,
                # Put the table name in the kwargs.
                kwargs = {'table_name' : name} : 
                self.Create_Tab(class_name, label, **kwargs))
        return


    def Create_Tab(self, class_name, label, index = None, **kwargs):
        '''
        Create a new tab holding a widget_class object, with  the
        given tab label. Any extra kwargs are passed.
        If the tab class is meant to be unique and an existing copy
        is open, that one will be focused on.
        Returns the created or freshly shown widget.
        '''
        # Look up the window class.
        window_class = globals()[class_name]
        # Check if it is meant to be unique.
        if window_class.unique_tab:
            # Check if there is a matching window already open.
            open_tabs = self.Get_Tab_Widgets(class_name)
            if open_tabs:
                widget = open_tabs[0]
                # There should just be one. Focus on it.
                index = self.widget_tab_container.indexOf(widget)
                self.widget_tab_container.setCurrentIndex(index)
                return widget

        # Store the tab information for rebuilding on reload.
        tab_properties = Tab_Properties(
            self,
            label,
            class_name,
            kwargs )
        widget = tab_properties.Get_Widget()
        return self.Create_Tab_From_Widget(widget, index)


    def Create_Tab_From_Widget(self, widget, index = None):
        '''
        Create a new tab based on the given widget.
        Switches focus to the new tab, and kicks off its initial
        data filling if startup is complete.
        Returns the widget.
        '''
        # Polish the index, keeping in range.
        tab_count = self.widget_tab_container.count()
        if index == None or index > tab_count:
            index = tab_count

        # Add it to the tab container.
        tab_index = self.widget_tab_container.insertTab(
            index, widget, widget.tab_properties.label)
        
        # Update the font on the new tab.
        self.Update_Font()

        # Switch focus.
        self.widget_tab_container.setCurrentIndex(tab_index)

        # Start processing.
        if self.startup_complete:
            #widget.Reset_From_File_System()
            widget.Handle_Signal('file_system_reset')
        return widget


    def Get_Tab_Widgets(self, *filters):
        '''
        Returns a list of tab page widgets.
        This will include hidden widgets that aren't in the
        tab container currently.
        Visible tabs will be first, in tab order, then followed by
        any hidden tabs in name order.

        * filters
          - Optional strings, names of the classes to be returned.
          - Eg. Get_Tab_Widgets('Settings_Window', 'Script_Window')
          - Subclasses of the filtered classes will be returned.
        '''
        # Start by collecting the widgets.
        widget_list = []
        # Start with the visible tabs, so that their list indices match
        # their tab  indices.
        for index in range(self.widget_tab_container.count()):
            widget_list.append( self.widget_tab_container.widget(index))
        # Fill in the hidden tabs, unique ones that were not found above.
        for name, widget in sorted(self.unique_tabs_dict.items()):
            if widget not in widget_list:
                widget_set.append(widget)

        # If a filter given, swap it over to actual classes
        # for doing an isinstance check.
        # These should all be imported already to this module.
        filters = tuple([globals()[x] for x in filters])

        ret_list = []
        for widget in widget_list:
            # Skip non-matching class types.
            if filters and not isinstance(widget, filters):
                continue
            ret_list.append(widget)

        return ret_list


    def Close_Tab(self, index):
        '''
        Either hide or close the specified tab.
        '''
        # Start by looking up the tab page.
        widget = self.widget_tab_container.widget(index)

        # If this is a unique page, just hide it.
        # TODO: maybe check for its class_name being in the
        # unique dict instead, if that is safer.
        if widget.tab_properties.unique:
            self.Show_Hide_Tab(widget.tab_properties.class_name)
        else:
            # Remove it.
            self.widget_tab_container.removeTab(index)
            # Do any local closure it needs.
            widget.Close()
            # Flag qt to delete the widget.
            widget.deleteLater()
        return


    def Show_Hide_Tab(self, class_name, show_only = False, hide_only = False):
        '''
        Shows or hides a tab of the given class_name, which is
        expected to be in unique_tabs_dict.

        * show_only
          - Bool, if True then the tab will be shown but not hidden.
        * hide_only
          - Bool, if True then the tab will be hidden but not shown.
        '''
        widget = self.unique_tabs_dict[class_name]

        # Apparently the only way to do this is to remove the tab page
        # entirely from the tab container, or add it back in.
        # Start by finding it on the tab bar; this may fail if
        # it is not present.
        if any(widget is self.widget_tab_container.widget(index) 
                for index in range(self.widget_tab_container.count())):
            currently_shown = True
        else:
            currently_shown = False
            
        # Hide it if needed.
        if currently_shown and not show_only:
            # Grab the index.
            index = self.widget_tab_container.indexOf(widget)

            # Remove from the bar and record the index.
            self.widget_tab_container.removeTab(index)
            widget.tab_properties.index = index
            # Flag as hidden for session save/restore.
            widget.tab_properties.hidden = True

            # Error check; this widget should be known.
            assert widget is self.unique_tabs_dict[class_name]

        # Show it if needed.
        elif not currently_shown and not hide_only:
            widget = self.unique_tabs_dict[class_name]
            # Restore it as its prior index.
            self.Create_Tab_From_Widget(widget, widget.tab_properties.index)
            widget.tab_properties.hidden = False
            # In case font changed while it was hidden, update fonts.
            self.Update_Font()
        return


    def Store_Settings(self):
        '''
        Tells the settings widget to Store_Settings.
        '''
        # TODO: maybe make this part of Soft_Reset or another
        # standard method.
        self.unique_tabs_dict['Settings_Window'].widget_settings.Store_Settings()
        
    ##########################################################################
    # Reset related functions.

    def Send_Signal(self, *flags):
        '''
        Signalling function, to be called by child tabs upon various
        events, to trigger updates in other tabs (or even the caller
        tab).  This will call Handle_Signal in all child tabs, with
        priority for the currently viewed tabs.

        * flags
          - Strings, series of supported signal flags, indicating what has
            occurred.
          - Initial flag options (TODO: trim to those used):
            - 'file_system_reset'
            - 'files_modified'
            - 'files_loaded'
            - 'script_completed'
            - 'save'
            - 'save_as'
        '''
        # Want to prioritize the currently viewed tab.
        current_tab = self.widget_tab_container.currentWidget()
        current_tab.Handle_Signal(*flags)

        # Go through all tabs.
        for tab in self.Get_Tab_Widgets():
            # Skip the current_tab since it was already handled.
            if tab is current_tab:
                continue
            tab.Handle_Signal(*flags)

        # Handle some signals here.
        if 'save' in flags or 'save_as' in flags:
            # The live editor doesn't belong to a tab, so save
            # it here.
            Live_Editor.Save_Patches()
            self.Print('Saved Live Editor patches')
        return


    #def Soft_Refresh(self):
    #    '''
    #    To be called after a script run, performs a Soft_Refresh on all
    #    tabs that display 'current' game file information.
    #    TODO: replace with a generic Send_Signal function completely.
    #    '''
    #    # Want to prioritize the currently viewed tab.
    #    current_tab = self.widget_tab_container.currentWidget()
    #    current_tab.Soft_Refresh()
    #
    #    # Go through all tabs.
    #    for tab in self.Get_Tab_Widgets():
    #        # Skip the current_tab since it was already handled.
    #        if tab is current_tab:
    #            continue
    #        # Kick off the refresh.
    #        tab.Soft_Refresh()
    #    return
        

    #def Refresh_File_System(self):
    #    '''
    #    Resets/refreshes the File_System and related components.
    #    This will kick off data loading on all edit tabs.
    #    Meant for use at startup if Settings appear to have proper
    #    paths, or for when paths change.
    #    TODO: maybe a menu option as well.
    #    TODO: replace with a generic Send_Signal function completely.
    #    '''
    #    # TODO: check validity of Settings.
    #    if not Settings.Paths_Are_Valid():
    #        return
    #
    #    # Want to prioritize the currently viewed tab, if any.
    #    # Note: if all tabs are hidden, this will return None.
    #    current_tab = self.widget_tab_container.currentWidget()
    #    if current_tab != None:
    #        current_tab.Reset_From_File_System()
    #
    #    # Go through all tabs.
    #    for tab in self.Get_Tab_Widgets():
    #        # Skip the current_tab since it was already handled.
    #        if tab is current_tab:
    #            continue
    #        # Kick off the refresh.
    #        # These will queue up, so should be safe.
    #        tab.Reset_From_File_System()
    #    return


    ##########################################################################
    # Font related actions.
    # TODO: maybe split off the script edit window font from
    # the others.

    def Init_Font(self):
        '''
        Set up the default font for the various windows.
        This is mainly to pick a monospace font.
        TODO: maybe skip this and use qt default.
        '''
        new_font = QFont()
        new_font.setFamily("Courier")
        # Set the font selection preferences if the above is not found;
        #  aim to select anything monospace.
        new_font.setStyleHint(QFont.Monospace)
        new_font.setFixedPitch(True)
        new_font.setPointSize(10)
        # Update the window fonts.
        self.Update_Font(new_font)
        return

        
    def Action_Change_Font(self):
        '''
        The 'Font' action was selected.
        Launch a font selection window, and update with the resulting
        font selected (if any).
        '''
        # This should return the current_font if a new one is not selected,
        #  along with a second boolean indicating if the font changed.
        new_font, font_changed = QtWidgets.QFontDialog.getFont(
                                            self.current_font, self)
        # Update the font if needed.
        if font_changed:
            self.Update_Font(new_font)
        return


    def Update_Font(self, new_font = None):
        '''
        Update up the font to use in the various windows.
        If called with no arg, this refreshes the current font,
        useful for when new tabs are created.
        '''
        if new_font == None:
            new_font = self.current_font
        else:
            self.current_font = new_font
                
        # Set up a slightly smaller version of the current font.
        small_font = QFont()
        # Unclear on how best to get an initial copy; try passing
        # through strings.
        small_font.fromString(new_font.toString())
        small_font.setPointSize(small_font.pointSize() - 2)

        # Pass the fonts to tag pages.
        for widget in self.Get_Tab_Widgets():
            widget.Update_Font(new_font, small_font)

        # Put a small font on the output window.
        self.widget_output.setFont(small_font)
        return

    
    ##########################################################################
    # Style related actions.

    def Init_Styles(self):
        '''
        Expands the menuStyle submenu with the selection options for
        found available qt styles.
        '''
        # Add submenu items for the style names.
        for name in sorted(Styles.Get_Style_Names()):
            action = self.menuStyle.addAction(name)
            
            # Annotate the action with the style name, for easy 
            # handling when triggered.
            action.style_name = name

            # Connect up the action to a shared handler.
            # This can use a lambda function to pass args to the called
            # handler function.
            # Note: this requires jumping through hoops to get the current
            # name to pass through, instead of all lambdas using the name
            # on the last loop iteration.
            # https://stackoverflow.com/questions/50298582/why-does-python-asyncio-loop-call-soon-overwrite-data
            # The first term is some qt junk term; after that give the
            # wanted term with a default set to the wanted value.
            action.triggered.connect(
                lambda qtjunk, name = name: self.Action_Change_Style(name))

            # Look for Fusion style, to set as the default, to enable
            # table label coloring.
            if name == 'Fusion':
                self.Action_Change_Style('Fusion')

        # Record the current style name; probably default Windows or similar.
        return

        
    def Action_Change_Style(self, style_name):
        '''
        A 'Style' submenu action was selected.
        '''
        # Update the style if needed.
        if style_name != self.current_style:
            self.Update_Style(style_name)
        return


    def Update_Style(self, style_name):
        '''
        Update up the style to use in the various windows.
        '''
        # Build the style.
        style = Styles.Make_Style(style_name)
        # Catch failures.
        if style == None:
            self.Print('Failed to create style ""'.format(style))
            return

        # Update the app.
        self.application.setStyle(style)
        # Save the name.
        self.current_style = style_name
        return
        
    ##########################################################################
    # Shutdown functions.
    
    def Action_Quit(self):
        '''
        Action to take when the close menu item is selected.
        '''
        # Redirect to .close().
        self.close()
        return


    # Specially named function called when the window is closed using
    # the 'x'.
    def closeEvent(self, event):
        '''
        Action to take when the close ('x') button is pressed.
        '''
        success = self.close()
        # Ignore the event if the close was cancelled.
        if success:
            event.accept()
        else:            
            event.ignore()
        return


    def close(self):
        '''
        Wrapped close() handler; called on 'x' press or by the Quit action.
        Returns True when closing the window, False when closing is cancelled.
        '''
        # Call close on all tab pages.
        # If these return False, cancel the close.
        for widget in self.Get_Tab_Widgets():
            if widget.Close() == False:
                return False
            
        # Stop any running script.
        self.worker_thread.Close()

        # Save the gui settings themselves.
        self.Save_Session_Settings()

        # Save the Live_Editor changes.
        # This can fail if the settings don't have a proper output path.
        try:
            Live_Editor.Save_Patches()
        except AssertionError:
            # Ignore for now.
            pass

        super().close()
        return True

    
    ##########################################################################
    # Save/restore gui state        

    def Save_Session_Settings(self):
        '''
        Save gui settings for this run (font, layout, size, etc.).
        '''
        # Convenience renaming.
        settings = self.session_memory

        # These settings objects record all information when an ini
        # was loaded, including stale keys; clear them all out.
        for key in settings.allKeys():
            settings.remove(key)
        
        settings.beginGroup('Main_Window')
        # These functions appear to handle pos, size, and dock widget
        # size, for the main window. They do not capture any
        # internal widget positions (eg. splitters).
        settings.setValue('geometry'  , self.saveGeometry())
        settings.setValue('state'     , self.saveState())
        settings.setValue('font'      , self.current_font)
        settings.setValue('style'     , self.current_style)
        settings.setValue('tab_index' , self.widget_tab_container.currentIndex())
        settings.endGroup()
        

        # Save state from tab pages.
        # Side note: the actual ini order could be jumbled, so these
        #  tabs will have some care during read back to put them in
        #  the right order; they can be sorted based on tab name,
        #  up to 3 digits worth.
        for index, widget in enumerate(self.Get_Tab_Widgets()):
            # Use the tab_properties to handle saving.
            settings.beginGroup('Tab_{:03}'.format(index))
            widget.tab_properties.Save_Session_Settings(settings)
            settings.endGroup()
            
        # Note: there is a .sync() method that writes the file, but
        # it is apparently handled automatically on shutdown.
        return

    
    def Load_Session_Settings(self):
        '''
        Restore gui settings from a prior run.
        '''
        # Convenience renaming.
        settings = self.session_memory

        # Loop over the groups; there are an unspecified number due
        # to variable tab amounts being open.
        # Sort these to restore tabs in order.
        for group in sorted(settings.childGroups()):
            settings.beginGroup(group)

            if group == 'Main_Window':
                # Look up existing settings; change nothing if none found.
                # Note: setting the default for .value() to None causes some
                # default object to be returned, so just use a .contains()
                # check instead. TODO: double check if this is true for pyqt.
                # Use a settings group for scalability, in case other windows
                # need to also be saved in the future.
                for field, method in [
                        ('geometry', self.restoreGeometry),
                        ('state'   , self.restoreState),
                        ('font'    , self.Update_Font),
                        ('style'   , self.Update_Style),
                    ]:
                    if not settings.contains(field):
                        continue
                    # Just in case the ini format is wrong, skip over
                    # problematic setting values.
                    try:
                        value = settings.value(field)
                        method(value)
                    except Exception as ex:
                        self.Print(('Failed to restore prior setting: "{}:{}"'
                                    .format(group, field)))

            elif group.startswith('Tab_'):

                # Note: if save/restore is changed across versions, this
                # restoration might fail, so wrap it for safety and have
                # it fail with assertion errors.
                try:
                    # Start by packing into a tab_properties.
                    tab_properties = Tab_Properties(self)

                    # Restore it; this will make the widget as well.
                    tab_properties.Load_Session_Settings(settings)

                    # Record unique tabs right away, to keep a reference
                    # to them if not showing yet.
                    if tab_properties.unique:
                        self.unique_tabs_dict[tab_properties.class_name] \
                            = tab_properties.Get_Widget()

                    # Create the tab if it isn't set to hidden.
                    if not tab_properties.hidden:
                        self.Create_Tab_From_Widget(tab_properties.Get_Widget())

                except AssertionError:
                    self.Print(('Failed to restore "{}"'.format(group)))

            settings.endGroup()
                    
        
        # Once all tabs are created, restore the tab widget index.
        settings.beginGroup('Main_Window')
        try:
            index = settings.value('tab_index', 0, type = 'int')
            self.widget_tab_container.setCurrentIndex(index)
        except Exception:
            pass
        settings.endGroup()
                
        return
        

    
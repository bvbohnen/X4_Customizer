
from pathlib import Path
from PyQt5 import QtCore, QtWidgets
from Framework.Common import home_path

class Session_Memory:
    '''
    Support for saving and restoring gui state across sessions.

    Attributes:
    * window
      - The parent QMainWindow.
    * gui_settings
      - QSettings object holding gui customizations (window size,
        position, etc.).
    '''
    def __init__(self, window):
        self.window = window
                
        # Set up a QSettings object, giving it the path to where
        # the settings are stored. Set it as an ini file, since otherwise
        # it wants to make a mess in the registry.
        self.gui_settings = QtCore.QSettings(
                str(home_path / 'gui_settings.ini'),
                QtCore.QSettings.IniFormat)
        return


    def Restore_Session_Memory(self):
        '''
        Restore gui settings from a prior run.
        '''
        # Convenience renaming.
        settings = self.gui_settings
        window = self.window

        # Look up existing settings; change nothing if none found.
        # Note: setting the default for .value() to None causes some
        # default object to be returned, so just use a .contains()
        # check instead.
        # Use a settings group for scalability, in case other windows
        # need to also be saved in the future.
        group = 'Main_Window'
        settings.beginGroup(group)
        for field, method in [
            #('size', window.resize),
            #('pos' , window.move),
            ('font', window.Update_Font),
            ('style', window.Update_Style),
            ('geometry', window.restoreGeometry),
            ('state', window.restoreState),
            ]:
            if settings.contains(field):
                # Just in case the ini format is wrong, skip over problematic
                # setting values.
                try:
                    method(settings.value(field))
                except Exception:
                    window.Print(('Failed to restore prior setting: "{}:{}"'
                               .format(group, field)))
        settings.endGroup()
        
        # Iterate over all widgets, finding splitters.
        for splitter in window.findChildren(QtWidgets.QSplitter):
            name = splitter.objectName()
            settings.beginGroup(name)
            if settings.contains('state'):
                try:
                    splitter.restoreState(settings.value(field))
                except Exception:
                    window.Print(('Failed to restore prior setting: "{}:{}"'
                               .format(splitter,field)))
            settings.endGroup()


        ## Custom values.
        ## TODO: move these to a subfunction of Script_Actions that
        ##  will accept the gui settings object.
        ## Note: need to capture 'None' strings and conver them.
        ## Paths need to be cast to a Path if not None.
        #script_actions = window.script_actions
        #stored_value = settings.value('last_dialog_path', None)
        #if stored_value not in [None, 'None']:
        #    script_actions.last_dialog_path = Path(stored_value)
        #
        ## Try to load the prior script.
        #stored_value = settings.value('current_script_path', None)
        #if stored_value not in [None, 'None']:
        #    script_actions.current_script_path = Path(stored_value)
        #    script_actions.Load_Script_File(script_actions.current_script_path)
        #else:
        #    script_actions.Action_New_Script()

        return
        

    def Save_Session_Memory(self):
        '''
        Save gui settings for this run (font, layout, size, etc.).
        '''
        # Convenience renaming.
        settings = self.gui_settings
        window = self.window
        # These settings objects record all information when an ini
        # was loaded, including stale keys; clear them all out.
        for key in settings.allKeys():
            settings.remove(key)
        
        settings.beginGroup('Main_Window')        
        # These functions appear to handle pos, size, and dock widget
        # size, for the main window. They do not capture any
        # internal widget positions (eg. splitters).
        settings.setValue('geometry', window.saveGeometry())
        settings.setValue('state', window.saveState())
        settings.setValue('font', window.current_font)
        settings.setValue('style', window.current_style)
        settings.endGroup()

        # Iterate over all widgets, finding splitters.
        for splitter in window.findChildren(QtWidgets.QSplitter):
            name = splitter.objectName()
            settings.beginGroup(name)
            settings.setValue('state', splitter.saveState())
            settings.endGroup()

        # Custom values.
        #settings.setValue('current_script_path', str(window.script_actions.current_script_path))
        #settings.setValue('last_dialog_path'   , str(window.script_actions.last_dialog_path))

        # Note: there is a .sync() method that writes the file, but
        # it is apparently handled automatically on shutdown.
        return

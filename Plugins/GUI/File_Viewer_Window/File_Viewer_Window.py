
from collections import OrderedDict
from pathlib import Path
import difflib
from PyQt5.uic import loadUiType
from ..Shared import Tab_Page_Widget
from Framework import File_System, XML_Diff

gui_file = Path(__file__).parents[1] / 'x4c_gui_file_viewer_tab.ui'
generated_class, qt_base_class = loadUiType(str(gui_file))


class File_Viewer_Window(Tab_Page_Widget, generated_class):
    '''
    Window used for viewing a single file's contents, in various
    versions.

    Widget names:
    * widget_textBrowser_0
    * widget_textBrowser_1
    * widget_textBrowser_2
    * widget_Hideme
    * widget_button_compare
    * widget_checkBox_0
    * widget_checkBox_1
    * widget_checkBox_2
    * widget_textEdit_compare
    * dockWidget
    TODO: rename textBrowser to textEdit or similar.

    Attributes:
    * window
      - The parent main window holding this tab.
    * virtual_path
      - String, virtual_path for the file to display.
    * version_checkbox_dict
      - Dict, keyed by version, with the associated checkbox widget.
    * version_textbox_dict
      - Dict, keyed by version, with the associated text box widget.
    '''
    version_title_order = OrderedDict([
        ('vanilla', 'Vanilla'),
        ('patched', 'Patched'),
        ('current', 'Current'),
        ])

    def __init__(self, parent, window, virtual_path):
        super().__init__(parent, window)
        self.virtual_path = virtual_path

        self.version_checkbox_dict = {}
        self.version_textbox_dict  = {}

        # Want the placeholder along the top bar to be invisible
        # but still take space.
        # It is a little tricky to hide the placeholder; it will
        # normally stop taking space when invisible; use the sizePolicy
        # to adjust it.
        self.widget_Hideme.setVisible(False)
        # Note: cannot edit the sizepolicy directly; need to pull it
        # out, modify it, and set it back to update properly.
        sizepolicy = self.widget_Hideme.sizePolicy()
        sizepolicy.setRetainSizeWhenHidden(True)
        self.widget_Hideme.setSizePolicy(sizepolicy)

        # Trigger button for loading the comparison.
        self.widget_button_compare.clicked.connect(self.Action_Compare)

        # Start the dock hidden.
        self.dockWidget.setVisible(False)
        
        self.Init_Checkboxes()
        return
    

    def Init_Checkboxes(self):
        '''
        Name and connect up the checkboxes.
        Also record the text boxes for each version, in the same
        order as the checkboxes.
        '''
        # For now, these boxes are pre-created but not named.
        # 0-2 are left to right.
        checkboxes = [
            self.widget_checkBox_0,
            self.widget_checkBox_1,
            self.widget_checkBox_2,
            ]
        textboxes = [
            self.widget_textBrowser_0,
            self.widget_textBrowser_1,
            self.widget_textBrowser_2,
            ]
        
        self.version_textbox_dict  = {}
        for index, (version, label) in enumerate(self.version_title_order.items()):

            # Get the next checkbox.
            checkbox = checkboxes[index]
            # Name it.  TODO: maybe tooltip.
            checkbox.setText(label)

            # Record it.
            self.version_checkbox_dict[version] = checkbox
            # Record the matching text box.
            self.version_textbox_dict[version] = textboxes[index]

            # Connect up its action.
            checkbox.stateChanged.connect(self.Update_Visibilities)

        # Do an initial call to set up the viewer state.
        self.Update_Visibilities()
        return


    def Update_Visibilities(self):
        '''
        Show or hide text boxes based on check box states.
        '''
        for version, checkbox in self.version_checkbox_dict.items():
            textbox = self.version_textbox_dict[version]
            # Show it if the checkbox is checked.
            textbox.setVisible(checkbox.isChecked())
        return


    def Soft_Refresh(self):
        '''
        Redraw the 'current' text.
        '''
        # Side note: cannot record the game_file in general, since
        # it will change between script runs (eg. the old one is
        # removed, a new one created on file system refresh).
        game_file = File_System.Load_File(self.virtual_path, error_if_not_found = False)
        if game_file == None:
            return
        xml_root = game_file.Get_Root_Readonly(version = 'current')
        text = XML_Diff.Print(xml_root, encoding = 'unicode')
        self.version_textbox_dict['current'].setText(text)
        
        # If there is a comparison present, update it.
        self.Get_Diff(version_0 = 'patched', version_1 = 'current')
        return

    
    def Reset_From_File_System(self):
        '''
        Trigger regather of the game file on reset.
        '''
        self.Refresh()
        return

    
    def Refresh(self):
        '''
        Load the file, get its text, and display it.
        '''
        game_file = File_System.Load_File(self.virtual_path,
                                               error_if_not_found = False)
        if game_file == None:
            self.window.Print(('Error loading file for path "{}"'
                              ).format(self.virtual_path))
            return

        # Load the text into the boxes.
        for version, textbox in self.version_textbox_dict.items():
            xml_root = game_file.Get_Root_Readonly(version = version)
            text = XML_Diff.Print(xml_root, encoding = 'unicode')
            textbox.setText(text)
        return


    def Action_Compare(self):
        '''
        The 'compare' button was pressed.
        Based on checkbox states, pick two versions to compare.
        '''
        # First, get the checkboxes.
        versions_selected = set()
        for version, checkbox in self.version_checkbox_dict.items():
            if checkbox.isChecked():
                versions_selected.add(version)

        # If three selected, prune out one. If none selected, pick two.
        # These will both get the same result.
        if len(versions_selected) in [0,3]:
            # vanilla to current is most likely to give changes,
            # so drop patched. Also, before a script runs, this
            # will just compare vanilla to patched anyway.
            versions_selected = ['vanilla','current']

        # If one selected, pick the other one.
        if len(versions_selected) == 1:
            fill_dict = {
                'vanilla': 'current',
                'patched': 'current',
                'current': 'vanilla',
                }
            # Pick from the dict.
            versions_selected.add(fill_dict[versions_selected[0]])

        assert len(versions_selected) == 2

        # Now sort them so the leftmost goes first.
        version_order = []
        for version in self.version_title_order:
            if version in versions_selected:
                version_order.append(version)

        # Call the differ.
        self.Get_Diff(*version_order)
        return


    def Get_Diff(self, version_0 = 'vanilla', version_1 = 'patched'):
        '''
        Creates an html diff between two versions and displays the result.
        '''
        htmldiffer = difflib.HtmlDiff(tabsize = 4)
        # TODO: thread this if it has runtime problems, though none
        # noticed so far.
        # This needs to use make_file to get highlights, though it
        # also comes with an awkward legend.
        html = htmldiffer.make_file(
            # Gives lists of lines.
            fromlines = self.version_textbox_dict[version_0].toPlainText().splitlines(), 
            tolines   = self.version_textbox_dict[version_1].toPlainText().splitlines(),
            # Set the titles to use.
            fromdesc  = self.version_title_order[version_0], 
            todesc    = self.version_title_order[version_1],
            # Switch to context mode, that shows only the diff locations.
            context   = True,
            numlines  = 1,
            )

        # Rip out the legend.
        new_html = []
        removal_section = False
        for line in html.splitlines():
            # It starts with the Legends summary, goes until body end.
            if 'summary="Legends"' in line:
                removal_section = True
            if not removal_section or '</body>' in line:
                new_html.append(line)
        html = '\n'.join(new_html)

        # Write out to a comparison window.
        self.widget_textEdit_compare.setHtml(html)
        # Show the dock hidden.
        self.dockWidget.setVisible(True)
        return
    

    def Save_Session_Settings(self, settings):
        '''
        Save aspects of the current sessions state.
        '''
        super().Save_Session_Settings(settings)
        settings.setValue('virtual_path', self.virtual_path)
        return


    def Load_Session_Settings(self, settings):
        '''
        Save aspects of the prior sessions state.
        '''
        super().Load_Session_Settings(settings)
        self.virtual_path = settings.value('virtual_path', None)
        # TODO: close this tab on error loading the path.
        # For now, just let the tab be blank and the user close it.
        return

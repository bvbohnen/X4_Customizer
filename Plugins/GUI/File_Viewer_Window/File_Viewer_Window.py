
from collections import OrderedDict
from pathlib import Path
import difflib
from PyQt5.uic import loadUiType
from ..Shared import Tab_Page_Widget
from Framework import File_System, XML_Diff, Print
from .XML_Syntax_Highlighter import Get_Highlight_Macros
from multiprocessing import Pool
import time

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
    * widget_button_reload
    * widget_checkBox_0
    * widget_checkBox_1
    * widget_checkBox_2
    * textEdit_compare_left
    * textEdit_compare_right
    * dockWidget
    * widget_label_path
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
    * comparison_versions 
      - List of 2 version strings used in the current comparison.
    '''
    version_title_order = OrderedDict([
        ('vanilla', 'Vanilla'),
        ('patched', 'Patched'),
        ('current', 'Current'),
        ])

    def __init__(self, parent, window, virtual_path):
        super().__init__(parent, window)
        self.virtual_path = virtual_path
        # Disable arg printing for threads; text blocks are sent
        # over and flood the output.
        self.print_thread_args = False
        # Show the path in a label widget.
        self.widget_label_path.setText(virtual_path)

        self.version_checkbox_dict = {}
        self.version_textbox_dict  = {}
        self.comparison_versions   = []

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
        self.widget_button_reload.clicked.connect(self.Action_Reload_File)
        

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
        
        self.version_textbox_dict.clear()
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
        self.Refresh('current')
        return

    
    def Reset_From_File_System(self):
        '''
        Trigger regather of the game file on reset.
        '''
        self.Refresh()
        return

    
    def Refresh(self, *versions):
        '''
        Load the file, get its text, and display it.
        This can take some time to apply highlights, so thread it.

        * versions
          - Series of strings, the versions to be refreshed.
          - If None, all are refreshed.
        '''
        if not versions:
            versions = self.version_title_order.keys()

        # Disable the buttons while working.
        self.widget_button_compare.setEnabled(False)
        self.widget_button_reload.setEnabled(False)

        # Reset the live editor table group that is be re-requested.
        # This will fill in new items that may get created by the
        # user script.
        # -Removed
        #self.Queue_Thread(self._Threaded_Refresh)

        # The above isn't working very well at all, with qt doing
        #  some awkward stuff when a thread touches a widget,
        #  which it needs to do to trigger the highlighter (or if there
        #  is a workaround, it isn't clear).
        # As a different approach, the highlighting will be done in
        #  a first pass manually with no qt objects, just doing the
        #  regex checks and recording start/end/color tuples, then
        #  those will be fed to the normal highlighter in the main
        #  thread.
        
        game_file = File_System.Load_File(self.virtual_path, 
                                          error_if_not_found = False)
        if game_file == None:
            self.window.Print(('Error loading file for path "{}"'
                              ).format(self.virtual_path))
            return

        # Get a dict of version:text blocks, the basic input to 
        # the thread to run.
        version_lines_dict = {}
        for version in versions:
            xml_root = game_file.Get_Root_Readonly(version = version)
            text = XML_Diff.Print(xml_root, encoding = 'unicode')

            # Fill in the line numbers; they are needed before
            # highlighting or else columns are thrown off.
            # (Alternative would be to track how many chars are added
            # to each row and feed them into the macros as an adjustment
            # later, but this is messy enough already.)
            numbered_lines = self.Fill_Text_Line_Numbers(text)
            version_lines_dict[version] = numbered_lines

            # Attach a copy of the original text to the widget,
            # for use in comparisons.
            self.version_textbox_dict[version].orig_text = text
            # Also attach a copy of the line numbered text.
            # (There are other ways to do this, but this is the most
            # convenient.)
            self.version_textbox_dict[version].numbered_text = '\n'.join(numbered_lines)
            
        # Queue up the thread.
        self.Queue_Thread(self.Get_Text_Highlights, 
                          version_lines_dict = version_lines_dict)

        # Try to find a different solution for now.
        #self._Threaded_Refresh()
        #self.Handle_Thread_Finished()

        return
    

    def Fill_Text_Line_Numbers(self, text):
        '''
        Returns the text modified with preceeding line numbers.
        Input is raw text, output is a list of lines.
        '''
        new_lines = []
        for index, line in enumerate(text.splitlines()):
            # Add line numbers on the left.
            new_lines.append('{: >3d} {}'.format(index, line))
        return new_lines


    def Get_Text_Highlights(self, version_lines_dict):
        '''
        Thread suitable function that will convert xml texts into
        a dict of lists of lists of Highlight_Macros.
        Dict key is version; major list entries correspond to lines,
        minor entries to a collection of macros for the line.
        This will use multiprocessing to speed things up for large files.
        '''
        version_macros_list_dict = {}
        #start = time.time()

        # Short text will get processing directly.
        num_lines = len(next(iter(version_lines_dict.values())))
        #print(num_lines)
        #print(len(version_lines_dict))
        if num_lines < 5000 or len(version_lines_dict) == 1:
            # Loop over the versions.
            for version, lines in version_lines_dict.items():
                # Get the highlights.
                macros_list = Get_Highlight_Macros(lines)
                # Record them for output.
                version_macros_list_dict[version] = macros_list

        # Longer will go through multiprocessing.
        # In practice, this cuts a t file from 4.5 to 2.5 seconds.
        # There is still a big delay on applying the formats, though.
        else:
            #print('multiprocessing...')
            pool = Pool()
            # Organize the text into a known order.
            # TODO: this does a bunch of spurious imports of gui stuff;
            # maybe look into breaking some of that up.
            versions = list(version_lines_dict.keys())
            macros_list_list = pool.map(
                Get_Highlight_Macros, 
                [version_lines_dict[x] for x in versions])

            # Pack back into a dict for output.
            for index, version in enumerate(versions):
                version_macros_list_dict[version] = macros_list_list[index]

        #print('time: ', time.time() - start)
        return version_macros_list_dict


    # TODO: split this somehow if also threading comparisons.
    def Handle_Thread_Finished(self, version_macros_list_dict):
        '''
        Finish up after a refresh of the text boxes.
        '''
        super().Handle_Thread_Finished()

        # Turn the buttons back on.
        self.widget_button_compare.setEnabled(True)
        self.widget_button_reload.setEnabled(True)
        
        # This print is pointless; if the highlights take a lot of time,
        # this printout won't show up until they are done.
        #self.window.Print('Applying text highlights...')
        #start = time.time()

        # Load the text into the boxes.
        # Note: this still takes 9 seconds...
        for version, macros_list in version_macros_list_dict.items():
            textbox = self.version_textbox_dict[version]

            # Attach the macros to the textbox highlighter.
            textbox.highlighter.Set_Line_Macros(macros_list)
            assert textbox.highlighter.line_macros_list

            # Apply the text.
            textbox.setPlainText(textbox.numbered_text)

            # Verify the match rules were used up.
            # These get consumed on a line-by-line basis.
            assert not textbox.highlighter.line_macros_list
        #print('time: ', time.time() - start)
        
        # If a comparison is active for any updated version, restore it.
        if any(v in self.comparison_versions for v in version_macros_list_dict):
            self.Refresh_Comparison()
        return


    def Comparison_Active(self):
        '''
        Returns True if there is a comparison visible and computed
        currently.
        '''        
        if self.comparison_versions and self.dockWidget.isVisible():
            return True
        return False


    def Refresh_Comparison(self):
        '''
        Refreshes the last computed comparison, if any.
        Does nothing if a comparison isn't active (and visible).
        '''
        if not self.Comparison_Active():
            return
        self.Get_Diff(*self.comparison_versions)
        return


    def Action_Reload_File(self):
        '''
        Reload the current file, completely resetting it in the File_System.
        Meant for use when testing external file changes, so they
        can get captured in the viewer.
        '''
        if not self.virtual_path:
            return
        File_System.Reset_File(self.virtual_path)
        self.Refresh()
        return


    def Action_Compare(self):
        '''
        The 'compare' button was pressed.
        Based on checkbox states, pick two versions to compare.
        '''        # First, get the checkboxes.
        versions_selected = []
        for version, checkbox in self.version_checkbox_dict.items():
            if checkbox.isChecked():
                versions_selected.append(version)

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
            versions_selected.append(fill_dict[versions_selected[0]])

        assert len(versions_selected) == 2
        assert versions_selected[0] != versions_selected[1]

        # Now sort them so the leftmost goes first.
        version_order = []
        for version in self.version_title_order:
            if version in versions_selected:
                version_order.append(version)

        # Call the differ.
        self.Get_Diff(*version_order)
        
        return


    def Get_Diff(self, version_0, version_1):
        '''
        Creates an html diff between two versions and displays the result.
        '''
        # Turn off the button.
        self.widget_button_compare.setEnabled(False)
        
        # TODO: maybe thread this.

        self.comparison_versions = [version_0, version_1]
        htmldiffer = difflib.HtmlDiff(tabsize = 4)
        # TODO: thread this if it has runtime problems, though none
        # noticed so far.
        # This needs to use make_file to get highlights, though it
        # also comes with an awkward legend.
        html = htmldiffer.make_file(
            # Gives lists of lines.
            fromlines = self.version_textbox_dict[version_0].orig_text.splitlines(), 
            tolines   = self.version_textbox_dict[version_1].orig_text.splitlines(),
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

        # The side-by-side html table looks pretty terrible in the gui
        # widget, which word wraps one side excesively early.
        # To move toward a balanced size split, and also to do it without
        # word wrap, do a processing pass over the html to break it into
        # two versions.
        split_html = [[],[]]
        for line in html.splitlines():

            # "<thead" lines need a split.
            # TODO: left align the table title somehow, else it tends
            # to be scrolled off out of view if any lines are long.
            if '<thead' in line:
                # This looks like (manually newlined):
                # <thead><tr>
                # <th class="diff_next"><br /></th>
                # <th colspan="2" class="diff_header">Vanilla</th>
                # -split here
                # <th class="diff_next"><br /></th>
                # <th colspan="2" class="diff_header">Current</th>
                # </tr></thead>
                start = '<thead><tr>'
                end   = '</tr></thead>'
                splitter = '<th class'

                # Pull off the start/end sections, and scrap the spacing.
                stripline = line.strip().replace(start,'').replace(end,'')

                # Split into an empty string and the two sides.
                header, left, right = stripline.split(splitter)

                # Put the start/end and splitter back on both sides.
                left = start + splitter + left + end
                right = start + splitter + right + end

                # Save.
                split_html[0].append(left)
                split_html[1].append(right)

            elif line.endswith('</tr>'):
                # Normal row splits.
                # These look like:
                # <tr>
                # <td class="diff_next" id="difflib_chg_to0__0"></td>
                # <td class="diff_header" id="from0_125">125</td>
                # <td nowrap="nowrap">stuff</td>
                # -split here
                # <td class="diff_next"></td>
                # <td class="diff_header" id="to0_125">125</td>
                # <td nowrap="nowrap">stuff</td>
                # </tr>
                start = '<tr>'
                end   = '</tr>'
                splitter = '<td class="diff_next"'
                
                # Pull off the start/end sections, and scrap the spacing.
                stripline = line.strip().replace(start,'').replace(end,'')

                # Split into an empty string and the two sides.
                header, left, right = stripline.split(splitter)

                # Put the start/end and splitter back on both sides.
                left = start + splitter + left + end
                right = start + splitter + right + end

                # Save.
                split_html[0].append(left)
                split_html[1].append(right)

            else:
                # Copy to both.
                split_html[0].append(line)
                split_html[1].append(line)

        #with open('test.html','w') as file:
        #    file.write(html)
        left_html  = '\n'.join(split_html[0])
        right_html = '\n'.join(split_html[1])
        
        # Write out to a comparison window.
        self.textEdit_compare_left .setHtml(left_html)
        self.textEdit_compare_right.setHtml(right_html)
        # Show the dock hidden.
        self.dockWidget.setVisible(True)
        
        # Turn on the button.
        self.widget_button_compare.setEnabled(True)
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

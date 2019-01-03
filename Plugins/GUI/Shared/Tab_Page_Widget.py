
from PyQt5 import QtWidgets

class Tab_Page_Widget(QtWidgets.QWidget):
    '''
    Generic widget for tab pages.
    This should be used instead of the Qt Designer specified base class,
    since a limit in the designer prevents proper promotion of tab
    pages to this class.

    Attributes:
    * window
      - The parent main window for this tab, generally expected to
        be the main window.
    * thread_request_active
      - Bool, True while this widget has a work thread request pending.
      - New requests will be ignored while this is True.
    * thread_request
      - The Work_Request object created by the thread handler when
        a request was made.
      - Only filled while a request is active.
    '''
    def __init__(self, parent, window):
        super().__init__(parent)

        self.window = window
        self.thread_request_active = False
        self.thread_request = None
        
        # Call the generated setup function, inherited from the qt form.
        # This will fill in the various widgets from designer.
        self.setupUi(self)

        # Copy the window print method.
        self.Print = window.Print

        # Loop over all owned widgets and set their window to this.
        # TODO: this overlaps with a widget 'window' lookup method;
        # find a better term.
        for widget in self.findChildren(QtWidgets.QWidget):
            widget.window = self

        # TODO: blindly attach to the thread finish signal, setting
        # it to return this window id.
            
        return


    def Soft_Refresh(self):
        '''
        Perform a partial refresh after a script has run, to update
        any 'current' views of game files.
        Subclasses should overwrite this and fill it in.
        '''
        return


    def Reset_From_File_System(self):
        '''
        This will be called after a file system reset (or at the
        end of gui init), to start the tab doing any processing
        to fill or refill itself.
        Subclasses should overwrite this and fill it in.
        '''
        return


    def Handle_Thread_Finished(self, return_value = None):
        '''
        Default handler for completed threads.
        Subclasses should wrap this will their own response handling logic,
        but still call this with super().
        '''
        # Only need to clear the activity flag here, for now.
        self.thread_request_active = False
        return


    def Unqueue_Thread(self):
        '''
        If a thread is currently queued, remove it from the queue.
        This doesn't stop a running thread.
        '''
        if self.thread_request_active:
            self.window.worker_thread.Unqueue_Thread(self.thread_request)
        return


    def Queue_Thread(
            self,
            work_function,
            *args,
            prelaunch_function = None,
            **kwargs,
        ):
        '''
        Queue up a thread to be run. When it finishes, Handle_Thread_Finished
        will be called automatically.

        * work_function
          - The function for the thread to call.
        * args, kwargs
          - Args and kwargs for the function to run.
        * prelaunch_function
          - Optional, requester function that will be called just before
            the thread is launched, after any prior thread has finished.
          - Special actions like File_System resets should be done
            here.
        '''
        # Skip when a request still pending.
        # While this could potentially allow queing multiple requests,
        # that is not an expected case for a single tab page.
        if self.thread_request_active:
            self.Print(('Ignoring thread request for "{}"; prior request'
                        ' still pending.').format(work_function.__name__))
            return

        self.thread_request_active = True
        self.thread_request = self.window.worker_thread.Queue_Thread(
            # Give the work_function and *args as positional args,
            # to match up with the Queue_Thread signature.
            work_function,
            *args,
            callback_function  = self.Handle_Thread_Finished,
            prelaunch_function = prelaunch_function,
            **kwargs
            )

        return


    def Update_Font(self, new_font, small_font):
        '''
        Update the fonts on this tab page.
        '''
        # Blindly update the window, letting children inherit.
        self.setFont(new_font)
        return


    def Save_Session_Settings(self, settings):
        '''
        Save geometry of the current sessions state.
        Subclasses should wrap this with their own saved state.
        '''        
        # Iterate over all widgets.
        for widget in self.findChildren(QtWidgets.QWidget):
            name = widget.objectName()
            settings.beginGroup(name)

            # Save splitter state.
            if isinstance(widget, QtWidgets.QSplitter):
                settings.setValue('state', widget.saveState())

            # Save checkbox status.
            if isinstance(widget, QtWidgets.QCheckBox):
                settings.setValue('checked', widget.isChecked())

            # All widgets have geometry, though it doesn't seem
            # very useful outside the main window.
            #settings.setValue('geometry', widget.saveGeometry())
            settings.endGroup()
        return


    def Load_Session_Settings(self, settings):
        '''
        Loads geometry to the current sessions state.
        Subclasses should wrap this with their own saved state.
        '''
        # Iterate over all widgets.
        for widget in self.findChildren(QtWidgets.QWidget):
            
            name = widget.objectName()
            settings.beginGroup(name)
            
            # Get splitter state.
            if isinstance(widget, QtWidgets.QSplitter):
                try:
                    widget.restoreState(settings.value('state'))
                except Exception:
                    pass

            # Get checkbox status.
            if isinstance(widget, QtWidgets.QCheckBox):
                try:
                    value = settings.value('checked')
                    if value == 'true':
                        widget.setChecked(True)
                    elif value == 'false':
                        widget.setChecked(False)
                except Exception:
                    pass

            settings.endGroup()
        return


    def Save(self):
        '''
        Save any tab information that needs to go to a file.
        '''
        return


    def Close(self):
        '''
        Prepare for closing the tab page.
        Returns True on success, False to cancel the close.
        By default, this calls Save.
        '''
        # Stop any thread requests.
        self.Unqueue_Thread()
        # Save any information.
        self.Save()
        return True
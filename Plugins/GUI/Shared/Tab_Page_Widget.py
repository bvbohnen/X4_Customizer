
from PyQt5 import QtWidgets

class Tab_Page_Widget(QtWidgets.QWidget):
    '''
    Generic widget for tab pages.
    This should be used instead of the Qt Designer specified base class,
    since a limit in the designer prevents proper promotion of tab
    pages to this class.

    Class attributes:
    * unique_tab
      - Bool, if True then only one instance of this tab should exist.
        Attempts to create more should be redirected to focusing on
        the existing tab.

    Attributes:
    * window
      - The parent main window for this tab, generally expected to
        be the main window.
    * thread_requests_active
      - List of Work_Request objects created by the thread handler when
        a request was made, removed as threads are completed.
      - Only filled while a request is active.
    * callback_function
      - The callback function for the current or most recent thread.
    * print_thread_args
      - Bool, if True then threads will print their args when launched.
      - Set False for tabs that have complex thread args.
    '''
    unique_tab = False

    def __init__(self, parent, window):
        super().__init__(parent)

        self.window = window
        self.thread_requests_active = []
        self.print_thread_args = True
        self.callback_function = None
        
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
        Subclasses should overwrite this with their own response
        handling logic, if they don't give callback_functions
        to their requests.
        '''
        # Could clear out finished requests, but it isn't really
        # needed, and is done instead when new requests launch
        # to make things simpler for callback functions.
        return


    def Unqueue_Thread(self):
        '''
        If a thread is currently queued, remove it from the queue.
        This doesn't stop a running thread, though will supress
        its callback function.
        '''
        for request in self.thread_requests_active:
            self.window.worker_thread.Unqueue_Thread(request)
        return


    def Queue_Thread(
            self,
            work_function,
            *args,
            prelaunch_function = None,
            callback_function = None,
            short_run = False,
            print_args = True,
            **kwargs,
        ):
        '''
        Queue up a thread to be run. When it finishes, Handle_Thread_Finished
        will be called automatically, or the callback_function if provided.
        TODO: maybe catch/ignore cases where a pending request has the same
        callback function as a new request.

        * work_function
          - The function for the thread to call.
        * args, kwargs
          - Args and kwargs for the function to run.
        * prelaunch_function
          - Optional, requester function that will be called just before
            the thread is launched, after any prior thread has finished.
          - Special actions like File_System resets should be done
            here.
        * callback_function
          - Optional, requester function that will be called after
            the thread completes, instead of Handle_Thread_Finished.
          - Will be given the return_value.
        * short_run
          - Bool, if True then the function is considered to have a short
            run time, and it will be run in the main thread instead of
            a subthread to reduce call overhead.
        '''
        # Call back to a default function, if none given.
        if callback_function == None:
            callback_function = self.Handle_Thread_Finished

        # Do some cleanup on older requests, removing those that
        # may have finished.
        for old_request in list(self.thread_requests_active):
            if old_request.finished:
                self.thread_requests_active.remove(old_request)

        request = self.window.worker_thread.Queue_Thread(
            # Give the work_function and *args as positional args,
            # to match up with the Queue_Thread signature.
            work_function,
            *args,
            callback_function  = callback_function,
            prelaunch_function = prelaunch_function,
            print_args = self.print_thread_args,
            short_run = short_run,
            **kwargs
            )
        self.thread_requests_active.append(request)
        return


    def Queue_Light_Thread(self, *args, **kwargs):
        '''
        As Queue_Thread, except that the function will be called
        directly instead of through a subthread, but still goes through
        the machinery to avoid running at the same time as other
        threads. For use in simple file system accesses.
        '''
        return self.Queue_Thread(*args, short_run = True, **kwargs)


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
        Widgets with a 'do_not_save' attribute will be skipped.
        '''        
        # Iterate over all widgets.
        for widget in self.findChildren(QtWidgets.QWidget):
            # Skip do_not_save widgets.
            if getattr(widget, 'do_not_save', None):
                continue

            name = widget.objectName()
            settings.beginGroup(name)

            # Save splitter state.
            if isinstance(widget, QtWidgets.QSplitter):
                settings.setValue('state', widget.saveState())

            # Save checkbox status.
            if isinstance(widget, (QtWidgets.QCheckBox,
                                   QtWidgets.QRadioButton)):
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
        Widgets with a 'do_not_save' attribute will be skipped.
        '''
        # Iterate over all widgets.
        for widget in self.findChildren(QtWidgets.QWidget):
            # Skip do_not_save widgets.
            # Normally these weren't saved to begin with, but this
            # check helps avoid hiccups across version changes that
            # add new do_not_save flags.
            if getattr(widget, 'do_not_save', None):
                continue
            
            name = widget.objectName()
            settings.beginGroup(name)
            
            # Get splitter state.
            if isinstance(widget, QtWidgets.QSplitter):
                try:
                    widget.restoreState(settings.value('state'))
                except Exception:
                    pass

            # Get checkbox status.
            if isinstance(widget, (QtWidgets.QCheckBox,
                                   QtWidgets.QRadioButton)):
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


    def Handle_Signal(self, *flags):
        '''
        Handle signals sent from the main window at the request of tabs.
        Subclasses should overwrite this with their own handling logic,
        as needed.
        TODO: think about how to handle cases of back-to-back signals,
        where a prior one may not have finished updates before the
        later one arrives, with opportunities to ignore later ones.
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

import traceback

from PyQt5 import QtCore
from Framework import Print
from Framework import Settings

# Use a named tuple to work requests.
#from collections import namedtuple
#Work_Request = namedtuple(
#    'Work_Request', 
#    ['prelaunch_function', 'callback_function', 
#     'work_function', 'print_args', 'short_run', 'args', 'kwargs'])

# Use a class for this, to dynamically changed the 'finished' flag.
class Work_Request:
    '''
    Object containing work request information.

    Attributes; most are the same as in Queue_Thread.
    * prelaunch_function
    * callback_function
    * work_function
    * print_args
    * short_run
    * args
    * kwargs
    * finished
      - Bool, False when the request is created, True when
        it has finished.
    '''
    def __init__(
                self, 
                prelaunch_function, 
                callback_function, 
                work_function,
                print_args, 
                short_run, 
                args, 
                kwargs
            ):
        self.prelaunch_function = prelaunch_function
        self.callback_function  = callback_function
        self.work_function      = work_function
        self.print_args         = print_args
        self.short_run          = short_run
        self.args               = args
        self.kwargs             = kwargs
        self.finished           = False


class Worker_Thread_Handler(QtCore.QThread):
    '''
    Thread launcher, which will run a script or specific plugin
    or other function.
    This hooks into the framework Print function, plus threads may
    modify customizer state, so only one thread should be active at a time.

    Note: this will handle its own 'finished' signals; requesters
    should not listen in, and instead provide a callback function
    that this will call appropriately when their work finishes.

    TODO: think about safety of wigets accessing minor customizer state
    while threads are running.
    Note: this will queue up work requests, and launches threads either
    when a work request arrives and no thread is running, or when
    a thread completes and there are queued items.

    Attributes:
    * window
      - The main window.
    * request_queue
      - List of Work_Request objects.
      - These will be serviced serially, in arrival order.
    * current_request
      - Work_Request to be handled on an immediately upcoming thread
        launch, or that of the currently active thread or last finished
        thread.
    * return_value
      - Whatever was returned from the function call is stored here.
    * thread_active
      - Bool, True when a thread has been set up to launch, or has
        completed. This is set in the main domain, and used to
        regulate queue service.

    Signals:
    * send_message
      - Emitted when send text to print, with the text as the arg,
        during a thread run.
      - To be listened to by the main window for Print calls,
        and used to cross thread domains.
    '''
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.request_queue = []
        self.current_request = None
        self.thread_active = False

        # To be able to work through a queue, this will listen to
        # its own 'finished' signal.
        self.finished.connect(self.Handle_Finished_Signal)
        return
    
    # To safely handle runtime script Prints being piped to the main
    # gui window, use a Qt signal for this.
    # The main window will hook into this as a listener.
    # Note: this has to be a class attribute due to the pyqt
    # implementation: http://pyqt.sourceforge.net/Docs/PyQt5/signals_slots.html
    send_message = QtCore.pyqtSignal(str)


    def Print(self, line):
        'Pipe threaded framework messages to the main gui.'
        #print('redirecting output')
        self.send_message.emit(str(line))

        
    def Queue_Thread(
            self, 
            work_function, 
            *args,
            callback_function,
            prelaunch_function = None,
            print_args = True,
            short_run = False,
            **kwargs
        ):
        '''
        Queue up a function to be run when the thread is next free.
        Returns the Work_Request object.

        * work_function
          - The function to call in the thread, such as a plugin or
            Framework.Main.Run.
        * args, kwargs
          - List and dict, args and keyword args to pass to the call.
          - For running scripts, the first arg should be the path
            to the script.
        * callback_function
          - The requester function that will be called when the thread
            finishes, being delivered the return value from whatever
            function the thread ran.
          - Will be sent one arg, the work_function return value.
          - Currently not optional, as lack of callback suggests
            a coding mistake.
        * prelaunch_function
          - The requester function that will be called just before
            the thread is launched, after any prior thread has finished.
          - Special actions like File_System resets should be done
            here.
          - Will be sent no args.
          - Optional.
        * print_args
          - Bool, if True (default) then args will be printed in
            an output log message, else they are skipped.
          - Callers should set this False if they use long args.
        * short_run
          - Bool, if True the function will be run locally instead
            of in a subthread.
        '''
        request = Work_Request(
                callback_function  = callback_function,
                prelaunch_function = prelaunch_function,
                work_function      = work_function,
                print_args         = print_args,
                short_run          = short_run,
                args               = args,
                kwargs             = kwargs,
                )
        # Launch the thread if none is active.
        if not self.thread_active:
            self.Start_Work_Request(request)
        else:
            self.request_queue.append(request)
        return request


    def Unqueue_Thread(self, request):
        '''
        Remove the given Work_Request from the queue, if present.
        If the request is running, it will continue until finishing
        but will not have its callback function called.
        '''
        if request in self.request_queue:
            self.request_queue.remove(request)
        if request is self.current_request:
            self.current_request = None
        return


    def Start_Work_Request(self, work_request):
        '''
        Launch a thread for the given work request.
        TODO: wrap some of this in try/except for safety.
        '''
        # Double check no thread is running.
        assert not self.thread_active
        assert not self.isRunning()

        # If there was a prelaunch function, call it.
        if work_request.prelaunch_function != None:
            try:
                work_request.prelaunch_function()
            except Exception as ex:
                self.Print(ex)
                self.Print('Error in thread prelaunch function "{}"'.format(
                    work_request.prelaunch_function.__name__))
                # On error, just ignore the request.
                return

        # Immediately flag the thread as active.
        self.thread_active = True
        self.window.Send_Signal('thread_started')

        # Store the work request into an attribute, for the thread
        # to check when it launches on its own domain.
        self.current_request = work_request
        
        # Run the selected function, starting a side thread unless
        # disabled through Settings, in which case the function
        # is run directly. Also use direct runs for short_run requests.
        if work_request.short_run or Settings.disable_threading:
            # Do a local domain run.
            self.run()
            # Manually send the finished signal, to mimic a thread
            # finishing.
            self.finished.emit()
        else:
            # Call the pyqt start function.
            self.start()
        return


    def Handle_Finished_Signal(self):
        '''
        Clean up when a thread completes, and maybe start the next
        thread in the queue.  The finished requester's callback
        function will be called before the next thread starts.
        '''
        # This could start a new thread before handling the callback
        #  function, but that is somewhat less safe, eg. the next
        #  request may reset the file system when the requester
        #  may check the file system during their callback function.
        # Note: if quitting early, the request may have been cleared
        # to prevent callback.
        if self.current_request != None:
            # Flag this request as finished.
            self.current_request.finished = True

            # Pass the recorded return value in the callback.
            try:
                self.current_request.callback_function(self.return_value)
            except Exception as ex:
                if Settings.developer:
                    self.Print(traceback.format_exc())
                # On error, just ignore the request.
                self.Print(ex)
                self.Print('Error in thread callback function "{}"'.format(
                    self.current_request.callback_function.__name__))

        # Update the activity flag.
        self.thread_active = False
        self.current_request = None
        self.window.Send_Signal('thread_finished')

        # Check if another request was queued while the thread was running.
        if self.request_queue:
            # Grab the first item off the queue.
            request = self.request_queue.pop(0)
            # Launch the next thread.
            self.Start_Work_Request(request)
        return


    def Close(self):
        '''
        Clear the queue and shut down any running thread.
        '''
        self.request_queue.clear()
        # Stop any callbacks when the thread returns.
        self.current_request = None
        # Tell the thread to quit.
        if self.isRunning():
            self.quit()
        return


    def run(self):
        '''
        Entry point called by the qt thread launcher.
        '''
        # Capture runtime output print statements, backing up any
        # old printer. This could be done on the main domain as well,
        # but left here for now.
        old_printer = Print.logging_function
        Print.logging_function = self.Print
        
        function = self.current_request.work_function
        args     = self.current_request.args
        kwargs   = self.current_request.kwargs
        
        # Nice little printout for what is being called.
        # Note: some args can be quite long, so skip anything complex.
        # Skip this for short runs.
        if self.current_request.short_run:
            pass
        elif self.current_request.print_args:
            self.Print('Starting thread: {}({}{}{})'.format(
                function.__name__,
                ', '.join(args),
                ', ' if kwargs and args else '',
                ', '.join(['{} = {}'.format(k,v) for k,v in kwargs.items()])
                ))
        else:
            self.Print('Starting thread: {}(...)'.format(function.__name__))

        # Run the function, with a default return value in case it fails.
        self.return_value = None
        try:
            self.return_value = function(*args, **kwargs)

        except Exception as ex:
            self.Print(str(ex))
            if Settings.developer:
                self.Print(traceback.format_exc())

        # Restore the old printer.
        Print.logging_function = old_printer
        return
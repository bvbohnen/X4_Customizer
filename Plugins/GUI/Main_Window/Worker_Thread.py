
from PyQt5 import QtWidgets, QtCore
from Framework import Print
from Framework import Settings

class Worker_Thread(QtCore.QThread):
    '''
    Thread which will run a script or specific plugin.
    This hooks into the framework Print function, so only one
    thread should be active at a time, preferably by having a
    single thread object for the entire gui that gets shared.

    Attributes:
    * function
      - Function to call, likely either a plugin or Main.Run.
    * args, kwargs
      - List and dict, args and keyword args to pass to the call.
      - For running scripts, the first arg should be the path
        to the script.
    * return_value
      - Whatever was returned from the function call is stored here.
    '''

    def Set_Function(self, _function, *args, **kwargs):
        '''
        Set the function that will be called, along with its args and kwargs.
        '''
        # Using an underscored arg name for this, to avoid possible
        # conflict with a function's kwargs.
        self.function = _function
        self.args = args
        self.kwargs = kwargs
        return

    # To safely handle runtime script Prints being piped to the main
    # gui window, use a Qt signal for this.
    send_message = QtCore.pyqtSignal(str)

    def Print(self, line):
        'Pipe threaded framework messages to the main gui.'
        #print('redirecting output')
        self.send_message.emit(line)


    def Start(self):
        '''
        Runs the selected function, starting a side thread unless
        disabled through Settings, in which case the function
        is run directly.
        '''
        if not Settings.disable_threading:
            # Call the pyqt start function.
            self.start()
        else:
            self.run()
            # Manually send the finished signal, to mimic a thread.
            self.finished.emit()
        return


    def run(self):
        '''
        Entry point called by the qt thread launcher.
        '''
        # Capture runtime output print statements, backing up any
        # old printer.
        old_printer = Print.logging_function
        Print.logging_function = self.Print

        # Run the function, with a default return value in case
        # it fails.
        self.return_value = None
        # Nice little printout for what is being called.
        self.Print('Starting thread: {}({}{}{})'.format(
            self.function.__name__,
            ', '.join(self.args),
            ', ' if self.kwargs and self.args else '',
            ', '.join(['{} = {}'.format(k,v) for k,v in self.kwargs.items()])
            ))
        try:
            self.return_value = self.function(*self.args, **self.kwargs)
        except Exception as ex:
            pass
            # Don't print for now; the framework will generally print the
            # exception on its own.
            #self.Print(str(ex))

        # Restore the old printer.
        Print.logging_function = old_printer
        return
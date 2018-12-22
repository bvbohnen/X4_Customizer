'''
Good examples on Qt threading here:
https://stackoverflow.com/questions/6783194/background-thread-with-qthread-in-pyqt
TODO: maybe try the QObject style.

Notes on signals here (for qt4):
http://pyqt.sourceforge.net/Docs/PyQt4/new_style_signals_slots.html
'''
from PyQt5 import QtWidgets, QtCore
from .. import Main
from ..Common import Print

class Thread_Run_Script(QtCore.QThread):
    '''
    Thread which will run a script.
    '''
    # To safely handle runtime script Prints being piped to the main
    # gui window, use a Qt signal for this.
    send_message = QtCore.pyqtSignal(str)

    def Print(self, line):
        'Pipe threaded framework messages to the main gui.'
        #print('redirecting output')
        self.send_message.emit(line)

    def run(self):
        # Capture runtime output print statements, backing up any
        # old printer.
        old_printer = Print.logging_function
        Print.logging_function = self.Print

        # Run the script.
        # The easiest way to do this is to just call Main.Run, and let
        # it handle the dynamic import.
        # Use command line style args for this, for now.
        # It should be safe to always enable argpass, since the top
        # argparser -h isn't useful.
        try:
            Main.Run(str(self.parent.current_script_path) + ' -argpass')
        except Exception as ex:
            pass
            # Don't print for now; the framework will generally print the
            # exception on its own.
            #self.Print(str(ex))

        # Restore the old printer.
        Print.logging_function = old_printer
        return
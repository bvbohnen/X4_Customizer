
# Note: there are other tricks that can be pulled to redirect prints
# to the gui, but this is straightforward and somewhat more dynamic.
class Print_class:
    '''
    Console printer. Supports redirection when wanted, but otherwise
    acts like a normal print. Primarily added for cleaner GUI support.

    Attributes:
    * logging_function
      - Optional function which will be called by Print instead of
        sending to the console. The function should accept
        one argument, the message string.
    '''
    def __init__(self):
        self.logging_function = None

    def __call__(self, line = ''):
        '''
        Write a line to the console.
        '''
        # If there is a logging_function attached, call it.
        if self.logging_function != None:
            self.logging_function(line)
        else:
            print(line)
        return

# Static print object.
Print = Print_class()


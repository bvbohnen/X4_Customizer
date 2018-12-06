
from .. import Common
Settings = Common.Settings
from .Misc import Init

# Record a set of all transforms.
# This is filled in by the decorator at startup.
Transform_list = []

# Record a set of transforms that were called.
# Transforms not on this list at the end of a run may need to do
#  cleanup of older files generated on prior runs.
#  (Note: cleanup code has largely been removed now, not being needed
#   thanks to delayed file writes.)
# This is filled in by the decorator.
Transforms_names_run = set()

def Transform_Was_Run_Before(transform_name):
    '''
    Returns True if the named transform has been run.
    '''
    return transform_name in Transforms_names_run



'''
Decorator function for transforms to check if their required
 files are found, and have nice handling when not found.

This is implemented as a two-stage decorator, the outer one handling
 the file check, the inner one returning the function.
Eg. decorators have one implicit input argument, the following object,
 such that "@dec func" is like "dec(func)".
To support input args, a two-stage decorator is used, such that
 "@dec(args) func" becomes "dec(args)(func)", where the decorator
 will return a nested decorator after handling args, and the nested
 decorator will accept the function as its arg.
To get the wrapped function's name and documentation preserved,
 use the 'wraps' decorator from functools.
This will also support a keyword 'category' argument, which
 will be the documentation transform category override to use when
 the automated category is unwanted.
'''
from functools import wraps
def Transform_Wrapper(
        category = None,
    ):
    '''
    Wrapper function for transforms.

    * category
      - String, category of the transform; if not given, category
        is set to the name of the containing module without the 'T_'
        prefix and set to singular instead of plural.
      - Subpackages of transforms should set this explicitly for now.
    '''
    # Make the inner decorator function, capturing the wrapped function.
    def inner_decorator(func):
        
        # Attach the override category to the function.
        if category != None:
            func._category = category
        else:

            # Fill a default category from the module name.
            func._category = func.__module__

            # The module may have multiple package layers in it, so
            #  get just the last one.
            func._category = func._category.split('.')[-1]

            # Remove a 'T_' prefix.
            if func._category.startswith('T_'):
                func._category = func._category.replace('T_','')

            # Drop the ending 's' if there was one (which was mostly present to
            #  mimic the X3 source file names, eg. 'tships').
            if func._category[-1] == 's':
                func._category = func._category[0:-1]
            # Special fix for 'Factorie' (after 's' removal).
            if func._category == 'Factorie':
                func._category = 'Factory'

        # Record the transform function.
        Transform_list.append(func)

        # Set up the actual function that users will call, capturing
        #  any args/kwargs.
        @wraps(func)
        def wrapper(*args, **kwargs):

            # On the first call, do some extra setup.
            # Init normally runs earlier when the paths are set up,
            #  but if a script forgot to set paths then init will end
            #  up being called here.
            Init()

            # Check if the settings are requesting transforms be
            #  skipped, and return early if so.
            if Settings.skip_all_transforms:
                return

            # Note this transform as being seen.
            Transforms_names_run.add(func.__name__)            


            # Call the transform function, looking for exceptions.
            # This will be the generally clean fallback when anything
            #  goes wrong, so that other transforms can still be
            #  attempted.
            try:
                results = func(*args, **kwargs)

                # If here, ran successfully.
                # (This may not be the case in dev mode, but that will
                #  have other messages to indicate the problem.)
                if Settings.verbose:
                    print('Successfully ran {}'.format(
                        func.__name__
                        ))

                # If the function is supposed to return anything, return it
                #  here, though currently this is expected to always be None.
                return results
            
            except Exception as ex:
                # When set to catch exceptions, just print a nice message.
                if not Settings.developer:
                    # Give the exception name.
                    print('Skipped {} due to a {} exception.'.format(
                        func.__name__,
                        type(ex).__name__
                        ))
                else:
                    # Reraise the exception.
                    raise ex

            return

        # Return the callable function.
        return wrapper

    # Return the decorator to handle the function.
    return inner_decorator


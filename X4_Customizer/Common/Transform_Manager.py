
from ..Common import Settings

# Record a list of all transforms defined.
# This is filled in by the decorator at startup.
# TODO: maybe remove this if unused.
transform_list = []

# Record a set of transforms that were called.
# Transforms not on this list at the end of a run may need to do
#  cleanup of older files generated on prior runs.
#  (Note: cleanup code has largely been removed now, not being needed
#   thanks to delayed file writes.)
# This is filled in by the decorator.
# TODO: maybe remove this if unused, though it was handy for
#  the x3 customizer.
transforms_names_run = set()

def Transform_Was_Run_Before(transform_name):
    '''
    Returns True if the named transform has been run.
    '''
    return transform_name in transforms_names_run

'''
Decorator function for transforms.

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
            
        # Record the transform function.
        transform_list.append(func)

        # Set up the actual function that users will call, capturing
        #  any args/kwargs.
        @wraps(func)
        def wrapper(*args, **kwargs):

            # On the first call, finalize the settings, verifying
            #  paths and creating the output folder.
            # This is needed for the transform logging file.
            Settings.Delayed_Init()

            # Check if the settings are requesting transforms be
            #  skipped, and return early if so.
            if Settings.skip_all_transforms:
                return

            # Note this transform as being seen.
            transforms_names_run.add(func.__name__)            


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


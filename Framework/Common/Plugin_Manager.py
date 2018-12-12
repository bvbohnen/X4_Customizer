
from ..Common import Settings

# Record a list of all plugins defined.
# This is filled in by the decorator at startup.
# TODO: maybe remove this if unused.
plugin_list = []

# Record a set of plugins that were called.
# Plugins not on this list at the end of a run may need to do
#  cleanup of older files generated on prior runs.
#  (Note: cleanup code has largely been removed now, not being needed
#   thanks to delayed file writes.)
# This is filled in by the decorator.
# TODO: maybe remove this if unused, though it was handy for
#  the x3 customizer.
plugins_names_run = set()

def Plugin_Was_Run_Before(plugin_name):
    '''
    Returns True if the named plugin has been run.
    '''
    return plugin_name in plugins_names_run

'''
Decorator function for plugins.

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
def _Plugin_Wrapper(
        plugin_type = None,
        category = None,
        uses_paths_from_settings = True,
    ):
    '''
    Wrapper function for plugins.

    * plugin_type
      - String, type of this plugin.
      - Currently one of ['Analysis','Transform','Utility'].
    * category
      - String, category of the plugin; if not given, category
        is set to the name of the containing module.
      - Subpackages of plugins should set this explicitly.
    * uses_paths_from_settings
      - Bool, if True (default) then the Settings module will be
        undergo delayed init automatically to check paths and 
        setup the output folder for logging.
      - Not required if a plugin doesn't use any paths from Settings,
        and does not try to write to a log.
    '''
    # Make the inner decorator function, capturing the wrapped function.
    def inner_decorator(func):
        
        # Attach the plugin type and other flags.
        func._plugin_type   = plugin_type
        func._uses_paths_from_settings = uses_paths_from_settings
            
        # Attach the override category to the function.
        if category != None:
            func._category = category
        else:
            # Fill a default category from the module name.
            func._category = func.__module__
            # The module may have multiple package layers in it, so
            #  get just the last one.
            func._category = func._category.split('.')[-1]

        # Record the plugin function.
        plugin_list.append(func)

        # Set up the actual function that users will call, capturing
        #  any args/kwargs.
        @wraps(func)
        def wrapper(*args, **kwargs):

            # Check if the settings are requesting plugins be
            #  skipped, and return early if so.
            if Settings.skip_all_plugins:
                return

            # On the first call, finalize the settings, verifying
            #  paths and creating the output folder.
            # This is needed for the plugin logging file.
            if func._uses_paths_from_settings:
                Settings.Delayed_Init()

            # Note this plugin as having been called.
            plugins_names_run.add(func.__name__)            


            # Call the plugin function, looking for exceptions.
            # This will be the generally clean fallback when anything
            #  goes wrong, so that other plugins can still be
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


# Wrappers on the wrapper, filling in the plugin_type conveniently.
def Transform_Wrapper(**kwargs):
    return _Plugin_Wrapper(plugin_type = 'Transform', **kwargs)
def Utility_Wrapper(**kwargs):
    return _Plugin_Wrapper(plugin_type = 'Utility', **kwargs)
# Don't sub-categorize analyses for now.
def Analysis_Wrapper(**kwargs):
    return _Plugin_Wrapper(plugin_type = 'Analysis', category = '', **kwargs)
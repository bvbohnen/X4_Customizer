
from .Settings import Settings
from .Print import Print

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
        doc_priority = 0,
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
    * doc_priority
      - Int, indicates how early in documentation this should
        be printed relative to other plugins of the same type
        and category.
      - Defaults 0; positive numbers print earlier.
    '''
    # Make the inner decorator function, capturing the wrapped function.
    def inner_decorator(func):
        
        # Attach the plugin type and other flags.
        func._plugin_type   = plugin_type
        func._uses_paths_from_settings = uses_paths_from_settings
        func._doc_priority = doc_priority
            
        if category != None:
            # Attach the override category to the function.
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
                    Print('Successfully ran {}'.format(
                        func.__name__
                        ))

                # If the function is supposed to return anything, return it
                #  here, though currently this is expected to always be None.
                return results
            
            except Exception as ex:
                # When set to catch exceptions, just print a nice message.
                if not Settings.developer:
                    # Give the exception name.
                    Print('Skipped {} due to {}: "{}".'.format(
                        func.__name__,
                        type(ex).__name__,
                        str(ex)
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
# Don't sub-categorize analyses or utilities for now.
def Utility_Wrapper(**kwargs):
    return _Plugin_Wrapper(plugin_type = 'Utility', category = '', **kwargs)
def Analysis_Wrapper(**kwargs):
    return _Plugin_Wrapper(plugin_type = 'Analysis', category = '', **kwargs)


'''
To let transforms share some documentation, support can be added
to specifying categorized docstrings that will be printed at
the head of each documentation section.

Since modules can be spread out, and the doc generator doesn't know
where transforms came from, perhaps the docs should be wrapped into
some sort of object that gets imported upward to the Transforms package.
However, this has some clumsiness since the object would need
to be named, although the name is fluff.

Some ideas:

    @Plugin_Doc(category)
    def somename():
        'doc stuff'

    somename = Plugin_Doc(category, 'doc stuff')

    'doc stuff' (at top of module)
    somename = Plugin_Doc(category, __doc__)

To avoid "somename" fluff, could potentially stick the documentation
in the module or package __doc__, then annotate all transforms
automatically to grab that docstring (through the wrapper), adding
some term to the docstring to indicate it is for printout.

    'doc stuff' (at top of module)
    @Transform_Wrapper(category, ).
    ...
        func.category = ...
        module_doc = globals()['__doc__']
        func.category_doc = module_doc if 'tag' in module_doc else ''

Another approach might be to use a reserved plugin name, and capture
shared documentation in that plugin (that is otherwise uncallable
in some way), which has the advantage of plugin categorization
keeping it combined with others in its category.

    @Transform_Wrapper()
    def Documentation():
        'doc stuff'
        
    This will be a little clumsy with name conflicts as the plugins
    get * imported from multiple places, though, so won't really work out.
    Can put the category in the name, maybe.
    
    @Transform_Wrapper()
    def Weapon_Documentation():
        'doc stuff'

    Uniquifies the documentation during imports. The name is still
    a little fluffy, but serves a purpose. Transform category would
    be filled in like other transforms (from module or package name).
    The doc generator only needs a special handler to sort this
    plugin first when printing; otherwise it gets categorized along
    with what it is documenting automatically
    Can handle sorting with a special transform wrapper arg that
    indicates preferred sorting priority.
        

'''
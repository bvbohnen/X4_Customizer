
from pathlib import Path
import re
from Framework import Utility_Wrapper
from Framework import File_Manager
from Framework import Load_File
from Framework import Plugin_Log
from Framework import Print
from Framework import File_Missing_Exception

@Utility_Wrapper()
def Check_Extension(
        extension_name,
        check_other_orderings = False,
        return_log_messages = False
    ):
    '''
    Checks an extension for xml diff patch errors and dependency errors.
    Problems are printed to the console.
    Returns True if no errors found, else False.

    Performs up to three passes that adjust extension loading order:
    in alphabetical folder order, as early as possible (after its
    dependencies), and as late as possible (after all other extensions 
    that can go before it).

    * extension_name
      - Name of the extension being checked.
      - This should match an enabled extension name findable on
        the normal search paths set in Settings.
    * check_other_orderings
      - Bool, if True then the 'earliest' and 'latest' loading orders
        will be checked, else only 'alphabetical' is checked.
      - These are recommended to identify where dependencies should
        be added to extensions, to protect against other extensions
        changing their folder name and thereby their loading order.
      - Defaults to False, to avoid printing errors that won't be
        present with the current extension order.
    * return_log_messages
      - Bool, if True then instead of the normal True/False return,
        this will instead return a list of logged lines that
        contain any error messages.
      - Does not stop the normal message Prints.
    '''
    # TODO: think about also checking later extensions to see if they
    #  might overwrite this extension.
    
    Print('')
    Print('Checking extension: {}'.format(extension_name))

    # Lowercase the name to standardize it for lookups.
    extension_path_name = extension_name.lower()

    # Success flag will be set false on any unexpected message.
    success = True

    # Pull out the source_reader; this also initializes it if needed.
    source_reader = File_Manager.File_System.Get_Source_Reader()

    # Verify the extension name is valid.
    if extension_path_name not in source_reader.extension_source_readers:
        raise AssertionError(
            'Extension "{}" not found in enabled extensions: {}'.format(
            extension_name, sorted(source_reader.Get_Extension_Names())))
    

    # Handle logging messages during the loading tests.
    # Do this by overriding the normal log function.
    # Keep a history of messages seen, to avoid reprinting them when 
    # the loading order is switched.
    messages_seen = set()

    # Possibly keep a list of lines seen for returning.
    logged_messages = []

    # For name checks, use re to protect against one extension name
    # being inside another longer name by using '\b' as word edges;
    # also add a (?<!/) check to avoid matching when the extension
    # name is in a virtual_path (always preceeding by a '\').
    re_name = r'(?<!/)\b{}\b'.format(extension_name)
    def Logging_Function(message):

        # Want to skip messages based on diff patches by other
        # extensions. Can check the ext_currently_patching attribute
        # of the source_reader for this.
        if (source_reader.ext_currently_patching != None
        and source_reader.ext_currently_patching != extension_name
        # As a backup, don't skip if this extension's name is in 
        # the message for some reason (though that case isn't really
        # expected currently).
        and not re.search(re_name, message)):
            return

        if message in messages_seen:
            return
        if 'Error' in message:
            messages_seen.add(message)
            nonlocal success
            success = False
            
            # Record the message, if requested.
            if return_log_messages:
                logged_messages.append(message)

            # Print with an indent for visual niceness.
            Print('  ' + message)
        return

    # Connect the custom logging function.
    Plugin_Log.logging_function = Logging_Function
    

    # Set up the loading orders by adjusting priority.
    # -1 will put this first, +1 will put it last, after satisfying
    # other dependencies. 0 will be used for standard alphabetical,
    # which some mods may rely on.
    priorities = [0]
    if check_other_orderings:
        priorities += [-1,1]

    # Loop over sorting priorities.
    for priority in priorities:
        if priority == 0:
            Print('  Loading alphabetically...')
        elif priority == -1:
            Print('  Loading at earliest...')
        else:
            Print('  Loading at latest...')

        # Resort the extensions.
        source_reader.Sort_Extensions(priorities = {
            extension_path_name : priority })
        
        # Loop over all files in the extension.
        for virtual_path in source_reader.Gen_Extension_Virtual_Paths(extension_path_name):
            # Do a test load; this preserves any prior loads that
            # may have occurred before this plugin was called.
            # Ignore not-found errors for this; they should only come
            # up if there was a file format problem that got it rejected,
            # which shows up in a different error message.
            Load_File(virtual_path, test_load = True, 
                      error_if_not_found = False)
            
    Print('  Overall result: ' + ('Success' if success else 'Error detected'))

    # Detach the logging function override.
    Plugin_Log.logging_function = None

    # Return the messages if requested, else the success flag.
    if return_log_messages:
        return logged_messages
    return success



@Utility_Wrapper()
def Check_All_Extensions():
    '''
    Calls Check_Extension on all enabled extensions, looking for errors.
    Returns True if no errors found, else False.
    '''
    # Two options here: call Check_Extension on each individual extension,
    #  which maybe does excessive work, or use custom code to check
    #  all extensions at once.
    # For now, just call Check_Extension for simplicity.
    
    # Success flag will be set false on any unexpected message.
    success = True

    # Pull out the source_reader; this also initializes it if needed.
    source_reader = File_Manager.File_System.Get_Source_Reader()

    # Gather the names of enabled extensions.
    extension_names = [x for x in source_reader.extension_source_readers]

    for extension_name in extension_names:
        if not Check_Extension(extension_name):
            success = False
    return success
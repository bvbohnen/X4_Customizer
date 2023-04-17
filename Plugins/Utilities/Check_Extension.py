
from pathlib import Path
import re
from Framework import Utility_Wrapper
from Framework import File_Manager
from Framework import Load_File
from Framework import Plugin_Log
from Framework import Print
from Framework import File_Missing_Exception
from Framework import File_Loading_Error_Exception
from Framework import Unmatched_Diff_Exception
from Framework import Settings

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
      - Name (folder) of the extension being checked.
      - May be given in original or lower case.
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
    extension_name = extension_name.lower()

    # Success flag will be set false on any unexpected message.
    success = True

    # Pull out the source_reader; this also initializes it if needed.
    source_reader = File_Manager.File_System.Get_Source_Reader()

    # Verify the extension name is valid.
    if extension_name not in source_reader.extension_source_readers:
        raise AssertionError(
            'Extension "{}" not found in enabled extensions: {}'.format(
            extension_name, sorted(source_reader.Get_Extension_Names())))
    
    # Look up the display name of the extension, which might be used
    # in some messages being listened to.
    extension_display_name = source_reader.extension_source_readers[
        extension_name].extension_summary.display_name

    # Handle logging messages during the loading tests.
    # Do this by overriding the normal log function.
    # Keep a history of messages seen, to avoid reprinting them when 
    # the loading order is switched.
    messages_seen = set()

    # Keep a list of lines seen, to possibly return.
    logged_messages = []

    # For name checks, use re to protect against one extension name
    # being inside another longer name by using '\b' as word edges;
    # also add a (?<!/) check to avoid matching when the extension
    # name is in a virtual_path (always preceeding by a '\').
    # Note: the extension_name could have special re characters in it;
    #  can use re.escape to pre-format it.
    # Use (a|b) style to match both forms of the extension name.
    re_name = r'(?<!/)\b({}|{})\b'.format(re.escape(extension_name),
                                          re.escape(extension_display_name))

    def Logging_Function(message):

        # Detect if this extension has its name in the message.
        this_ext_name_in_message = re.search(re_name, message)

        # Want to skip messages based on diff patches by other
        # extensions. Can check the ext_currently_patching attribute
        # of the source_reader for this.
        if (source_reader.ext_currently_patching != None
        and source_reader.ext_currently_patching != extension_name
        # As a backup, don't skip if this extension's name is in 
        # the message for some reason (though that case isn't really
        # expected currently).
        and not this_ext_name_in_message):
            return

        # Skip dependency errors from other extensions.
        # TODO: think of a smarter way to do this that can safely ignore
        # messages like this without ignoring those caused by this extension.
        # (Perhaps don't rely on the extension resort to catch these,
        #  but a specific extension checker.)
        if not this_ext_name_in_message:
            for skip_string in ['duplicated extension id', 
                                'missing hard dependency',
                                'multiple dependency matches']:
                if skip_string in message:
                    return

        if message in messages_seen:
            return
        if 'Error' in message or 'error' in message:
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
        # This will also check dependencies and for unique extension ids.
        source_reader.Sort_Extensions(priorities = {
            extension_name : priority })

        # TODO: maybe think about doing a dependency version check as well,
        # but that isn't very important since x4 will catch those problems,
        # so this tool can somewhat safely assume they will get dealt with
        # by the user.
        
        # Loop over all files in the extension.
        for virtual_path in source_reader.Gen_Extension_Virtual_Paths(extension_name):

            # Caught exception.
            exception = None

            # Skip non-xml files for now, to avoid checking every binary
            # file. TODO: maybe a way to still check dependency orders
            # for substitutions.
            if not virtual_path.endswith('xml'):
                continue

            # The path could be to an original file, or to a patch on an
            # existing file.  Without knowing, need to try out both cases
            # and see if either works.
            # Start by assuming this is an original file.
            try:
                Load_File(
                    virtual_path, 
                    test_load = True, 
                    error_if_unmatched_diff = True)

            # If it was a diff with no base file, catch the error.
            except Unmatched_Diff_Exception:

                # Pop off the extensions/mod_name part of the path.
                _, _, test_path = virtual_path.split('/', 2)
                
                # Note: some mods may try to patch files from other mods that
                # aren't enabled. This could be an error or intentional.
                # Here, only consider it a warning; explicit dependencies
                # should be caught in the content.xml dependency check.
                # Check if this path is to another extension.
                error_if_not_found = True
                if test_path.startswith('extensions/'):
                    error_if_not_found = False

                # Do a test load; this preserves any prior loads that
                # may have occurred before this plugin was called.
                try:
                    game_file = Load_File(
                        test_path, 
                        test_load = True, 
                        error_if_not_found = error_if_not_found)
                    if game_file == None:
                        Print('  Warning: could not find file "{test_path}"; skipping diff')

                # Some loading problems will be printed to the log and then
                # ignored, but others can be passed through as an exception;
                # catch the exceptions.
                # TODO: maybe in developer mode reraise the exception to
                # get the stack trace.
                except Exception as ex:
                    exception = ex

            except Exception as ex:
                exception = ex

            # Did either attempt get an exception?
            if exception != None:
                # Pass it to the logging function.
                Logging_Function(
                    ('Error when loading file {}; returned exception: {}'
                        ).format(virtual_path, exception))
            

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
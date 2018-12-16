
from pathlib import Path
from Framework import Utility_Wrapper, File_Manager, Load_File, Plugin_Log

@Utility_Wrapper()
def Check_Extension(
        extension_name
    ):
    '''
    Checks an extension for xml diff patch errors and dependency errors.
    Performs two passes: scheduling this extension as early as possible
    (after its dependencies), and as late as possible (after all other
    extensions that can go before it). Problems are printed to the console.
    Returns True if no errors found, else False.

    * extension_name
      - Name of the extension being checked.
      - This should match an enabled extension name findable on
        the normal search paths set in Settings.
    '''
    # TODO: think about also checking later extensions to see if they
    #  might overwrite this extension.
    
    print('Checking extension: "{}"'.format(extension_name))

    # Success flag will be set false on any unexpected message.
    success = True

    # Pull out the source_reader; this also initializes it if needed.
    source_reader = File_Manager.File_System.Get_Source_Reader()

    # Verify the extension name is valid.
    if extension_name not in source_reader.extension_source_readers:
        raise AssertionError(
            'Extension "{}" not found in enabled extensions: {}'.format(
            extension_name, sorted(source_reader.extension_source_readers.keys())))

    # Pull out the reader for this extension.
    extension_source_reader = source_reader.extension_source_readers[extension_name]


    # Handle logging messages during the loading tests.
    # Do this by overriding the normal log function.
    # Keep a history of messages seen, to avoid reprinting them when 
    # the loading order is switched.
    messages_seen = set()
    quoted_ext_name = '"{}"'.format(extension_name)
    def Logging_Function(message):
        # Skip if the extension name isn't in the message, and if
        # the extension isn't currently having its patch applied.
        if (source_reader.ext_currently_patching != extension_name
        and quoted_ext_name not in message):
            return
        if message in messages_seen:
            return
        if 'Error' in message:
            messages_seen.add(message)
            nonlocal success
            success = False
            # Add an indent for visual niceness.
            print('  ' + message)
        return

    Plugin_Log.logging_function = Logging_Function


    # Loop over sorting priorities.
    # -1 will put this first, +1 will put it last, after satisfying
    # other dependencies.
    for priority in [-1,1]:
        if priority == -1:
            print('  Loading {} early...'.format(quoted_ext_name))
        else:
            print('  Loading {} late...'.format(quoted_ext_name))

        # Resort the extensions.
        source_reader.Sort_Extensions(priorities = {
            extension_name : priority })
        
        # Loop over all files in the extension.
        for virtual_path in extension_source_reader.Get_Virtual_Paths():

            # Do a test load; this preserved any prior loads that
            # may have occurred before this plugin was called.
            # TODO: how to filter this to ignore extensions after the
            # selected one, and to only print errors for the selected one?
            Load_File(virtual_path, test_load = True)
            

    # Detach the logging function override.
    Plugin_Log.logging_function = None
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
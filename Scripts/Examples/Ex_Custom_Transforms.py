'''
Creates a custom transform, leveraging the file loaders to deal with
cat/dat unpacking, diff patch application, and using the file writers
to create diff patches.

This example removes the blue dock glow from all dockarea files.
'''

from Plugins import *
from Framework import Transform_Wrapper, Load_File, Load_Files

# Pick a custom name for the generated extension.
Settings(extension_name = 'remove_dock_glow')

# Create a custom transform.
# Note: the transform wrapper isn't required, but has a little extra error
# detection and recover support.
@Transform_Wrapper()
def Remove_Dock_Glow():
    '''
    Removes the glow effect from station docks.
    '''
    # Find every "dockarea" file of interest, using a wildcard pattern.
    # This will catch the vanilla docks. The path can be modified if
    # needing to catch other name patterns from extensions.
    dock_files = Load_Files('*dockarea_arg_m_station*.xml')

    for game_file in dock_files:
        # Extract an editable version of its xml.
        xml_root = game_file.Get_Root()

        # Do an xpath search to find xml elements.
        # This looks for the fx_glow parts.
        results = xml_root.xpath(".//connection[parts/part/@name='fx_glow']")
        # Skip if none found.
        if not results:
            continue

        # Loop over the connection elements.
        for conn in results:
            # Remove it from its parent.
            # (lxml syntax)
            conn.getparent().remove(conn)        

        # Now that the xml has been edited, and didn't have an error,
        # apply it back to the game_file.
        game_file.Update_Root(xml_root)
    return


# Run the transform.
Remove_Dock_Glow()

# Write the modified files out.
Write_To_Extension()
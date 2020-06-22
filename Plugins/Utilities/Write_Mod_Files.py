
from pathlib import Path
from lxml import etree as ET
import Framework
from Framework import File_System, Settings, Print, Load_File, XML_File

__all__ = [
    'Write_To_Extension',
    'Write_Modified_Binaries',
    'Make_Extension_Content_XML',
    'Update_Content_XML_Dependencies',
    ]


@Framework.Utility_Wrapper()
def Write_Modified_Binaries():
    '''
    Write out any modified binaries.  These are placed in the main x4
    folder, not in an extension.
    '''    
    # Return early if settings have writeback disabled.
    if Settings.disable_cleanup_and_writeback:
        Print('Skipping Write_Extension; writeback disabled in Settings.')
        return
    
    # Trigger writeback.
    # Don't clear old stuff; this has no associated log, and just overwrites.
    File_System.Write_Non_Ext_Files()
    return


@Framework.Utility_Wrapper()
def Write_To_Extension(skip_content = False):
    '''
    Write all currently modified game files to the extension
    folder. Existing files at the location written on a prior
    call will be cleared out. Content.xml will have dependencies
    added for files modified from existing extensions.

    * skip_content
      - Bool, if True then the content.xml file will not be written.
      - Content is automatically skipped if Make_Extension_Content_XML
        was already called.
      - Defaults to False.
    '''
    # TODO: maybe make path and extension name into arguments,
    # though for now they should be set up in Settings since
    # this is the location log files were written to.

    ## If no name given, use the one from settings.
    #if not extension_name:
    #    extension_name = Settings.extension_name

    # Return early if settings have writeback disabled.
    if Settings.disable_cleanup_and_writeback:
        Print('Skipping Write_Extension; writeback disabled in Settings.')
        return

    # Clean old files, based on whatever old log is there.
    File_System.Cleanup()

    # Create a content.xml game file.
    if not skip_content:
        Make_Extension_Content_XML()
    
    # Trigger writeback.
    File_System.Write_Files()
    return


def Make_Extension_Content_XML(
        name        = None,
        author      = None,
        version     = None,
        save        = False,
        sync        = False,
        enabled     = True,
        description = None,
    ):
    '''
    Adds an xml file object defining the content.xml for the top
    of the extension.  Common fields can be specified, or left as defaults.

    * name
      - String, display name; defaults to extension folder name.
    * author
      - String, author name; defaults to X4 Customizer.
    * version
      - String, version code; defaults to customizer version.
    * save
      - Bool, True if saves made with the extension require it be enabled.
    * sync
      - Bool.
    * enabled
      - Bool, True to default to enabled, False disabled.
    * description
      - String, extended description to use, for all languages.
      - Newlines are automatically converted to "&#10;" for display in-game.
    '''
    # If the content exists already, return early.
    if Load_File('content.xml', error_if_not_found = False) != None:
        return
    
    if not version:
        # Content version needs to have 3+ digits, with the last
        #  two being sub version. This doesn't mesh will with
        #  the version in the Change_Log, but can do a simple conversion of
        #  the top two version numbers.
        version_split = Framework.Change_Log.Get_Version().split('.')
        # Should have at least 2 version numbers, sometimes a third.
        assert len(version_split) >= 2
        # This could go awry on weird version strings, but for now just assume
        # they are always nice integers, and the second is 1-2 digits.
        version_major = version_split[0]
        version_minor = version_split[1].zfill(2)
        assert len(version_minor) == 2
        # Combine together.
        version = version_major + version_minor

    # If a description given, format slightly.
    if description:
        # Need to use "&#10;" for newlines in-game.
        description = description.replace('\n', '&#10;')
    else:
        description = ' '

    # Set the ID based on replacing spaces.
    this_id = Settings.extension_name.replace(' ','_')

    # Set up the root content node.
    content_node = ET.Element(
        'content',
        attrib = {
            # Swap spaces to _; unclear on if x4 accepts spaces.
            'id'         : this_id,
            'name'       : name if name else Settings.extension_name,
            'author'     : author if author else 'X4_Customizer',
            'version'    : version,
            'date'       : File_System.Get_Date(),
            # TODO: maybe track when changes are save breaking, eg. if
            #  adding in new ships or similar. Though in practice, it
            #  may be best to always keep this false, and offer transforms
            #  that can undo breaking changes safely before uninstall.
            'save'       : 'true' if save else 'false',
            'sync'       : 'true' if sync else 'false',
            'enabled'    : 'true' if enabled else 'false',
            'description': description,
            })

    
    # Fill out language description text.
    # This loops over all language ids noticed in the cat/dat t files.
    for lang_id in ['7','33','37','39','44','49','55','81','82','86','88']:
        # Set up a new text node.
        # TODO: per-language descriptions.
        text_node = ET.Element('language', language = lang_id, description = description)

        # Add to the content node.
        content_node.append(text_node)

    # Record it.
    File_System.Add_File( XML_File(
        xml_root = content_node,
        virtual_path = 'content.xml',
        modified = True))
    
    # Use shared code to fill in dependencies.
    Update_Content_XML_Dependencies()
    return


def Update_Content_XML_Dependencies():
    '''
    Update the dependencies in the content xml file, based on which other
    extensions touched files modified by the current script.
    If applied to an existing content.xml (not one created here), existing
    dependencies are kept, and only customizer dependencies are updated.

    Note: an existing xml file may loose custom formatting.
    '''
    # TODO: framework needs more development to handle cases with an
    # existing content.xml cleanly, since currently the output extension is
    # always ignored, and there is no particular method of dealing with
    # output-ext new files not having an extensions/... path.

    # Try to load a locally created content.xml.
    content_file = Load_File('content.xml', error_if_not_found = False)

    # If not found, then search for an existing content.xml on disk.
    if not content_file:
        # Manually load it.
        content_path = Settings.Get_Output_Folder() / 'content.xml'
        # Verify the file exists.
        if not content_path.exists():
            Print('Error in Update_Content_XML_Dependencies: could not find an existing content.xml file')
            return

        content_file = File_System.Add_File( XML_File(
            # Plain file name as path, since this will write back to the
            # extension folder.
            virtual_path = 'content.xml',
            binary = content_path.read_bytes(),
            # Edit the existing file.
            edit_in_place = True,
            ))

    root = content_file.Get_Root()
    
    # Set the ID based on replacing spaces.
    this_id = Settings.extension_name.replace(' ','_')
    
    # Remove old dependencies from the customizer, and record others.
    existing_deps = []
    for dep in root.xpath('./dependency'):
        if dep.get('from_customizer'):
            dep.getparent().remove(dep)
        else:
            existing_deps.append(dep.get('id'))

    # Add in dependencies to existing extensions.
    # These should be limited to only those extensions which sourced
    #  any of the files which were modified.
    # TODO: future work can track specific node edits, and set dependencies
    #  only where transform modified nodes might overlap with extension
    #  modified nodes.
    # Dependencies use extension ids, so this will do name to id
    #  translation.
    # Note: multiple dependencies may share the same ID if those extensions
    #  have conflicting ids; don't worry about that here.
    source_extension_ids = set()
    for file_name, game_file in File_System.game_file_dict.items():
        if not game_file.modified:
            continue
        
        for ext_name in game_file.source_extension_names:
            # Translate extension names to ids.
            ext_id = File_System.source_reader.extension_source_readers[
                                ext_name].extension_summary.ext_id
            source_extension_ids.add(ext_id)

    # Add the elements; keep alphabetical for easy reading.
    for ext_id in sorted(source_extension_ids):

        # Omit self, just in case; shouldn't come up, but might.
        if ext_id == this_id:
            Print('Error: output extension appears in its own dependencies,'
                  ' indicating it transformed its own prior output.')
            continue

        # Skip if already defined.
        if ext_id in existing_deps:
            continue
        
        # Add it, with a tag to indicate it came from the customizer.
        # TODO: optional dependencies?
        root.append( ET.Element('dependency', id = ext_id, from_customizer = 'true' ))

    content_file.Update_Root(root)
    return
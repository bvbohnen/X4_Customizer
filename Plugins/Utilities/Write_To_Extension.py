
from pathlib import Path
from lxml import etree as ET
import Framework
from Framework import File_System, Settings

@Framework.Utility_Wrapper()
def Write_To_Extension(skip_content = False):
    '''
    Write all currently modified game files to the extension
    folder. Existing files at the location written on a prior
    call will be cleared out. Content.xml will have dependencies
    added for files modified from existing extensions.

    * skip_content
      - Bool, if True then the content.xml file will not be written.
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
        print('Skipping Write_Extension; writeback disabled in Settings.')
        return

    # Clean old files, based on whatever old log is there.
    File_System.Cleanup()

    # Create a content.xml game file.
    if not skip_content:
        Make_Extension_Content_XML()
    
    # Trigger writeback.
    File_System.Write_Files()
    return

    
def Make_Extension_Content_XML():
    '''
    Adds an xml file object defining the content.xml for the top
    of the extension.
    '''
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

    # Set up the root content node.
    content_node = ET.Element(
        'content',
        attrib = {
            # Swap spaces to _; unclear on if x4 accepts spaces.
            'id'        : Settings.extension_name.replace(' ','_'),
            'name'      : Settings.extension_name,
            'author'    : 'X4_Customizer',
            'version'   : version,
            'date'      : File_System.Get_Date(),
            # TODO: maybe track when changes are save breaking, eg. if
            #  adding in new ships or similar. Though in practice, it
            #  may be best to always keep this false, and offer transforms
            #  that can undo breaking changes safely before uninstall.
            'save'      : 'false',
            'sync'      : 'false',
            'enabled'   : 'true',
            })

    
    # Fill out language description text.
    # This loops over all language ids noticed in the cat/dat t files.
    for lang_id in ['7','33','37','39','44','49','55','81','82','86','88']:
        # Set up a new text node.
        text_node = ET.Element('langugage', attrib={
            'language' : lang_id,
            'description':''})

        # Fill in description for 44, english, if no other.
        if lang_id == '44':
            # Note: need to use "&#10;" for newlines in-game.
            # TODO: maybe list some transforms run, or similar.
            text_node.set('description', 'Generated by X4_Customizer')

        # Add to the content node.
        content_node.append(text_node)


    # Add in dependencies to existing extensions.
    # These should be limited to only those extensions which sourced
    #  any of the files which were modified.
    # TODO: future work can track specific node edits, and set dependencies
    #  only where transform modified nodes might overlap with extension
    #  modified nodes.
    source_extension_names = set()
    for file_name, game_file in File_System.game_file_dict.items():
        if game_file.modified or 1:
            source_extension_names |= set(game_file.source_extension_names)

    # Add the elements; keep alphabetical for easy reading.
    for source_extension_name in sorted(source_extension_names):
        content_node.append( ET.Element('dependency', attrib={
            'id' : source_extension_name }))

    # Record it.
    File_System.Add_File( Framework.File_Manager.XML_File(
        xml_root = content_node,
        virtual_path = 'content.xml',
        modified = True))

    return
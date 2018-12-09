'''
Any misc support functions can be placed here.
Initially, this just has one function used by some other transform categories.
'''
from collections import defaultdict
import xml.etree.ElementTree as ET

from ... import File_Manager
from ...Common import Flags



def Make_Director_Shell(cue_name, body_text = None, file_name = None):
    '''
    Support function to make a director shell file, setting up a queue
    with the given body text.
    The file name will reuse the cue_name if file_name not given.
    Optionally, delete any old file previously generated instead of
    creating one.
    '''
    raise Exception('TODO: update for X4.')
    #  Set the default file name.
    if not file_name:
        file_name = cue_name + '.xml'
    assert '.xml' in file_name


    # Copied shell text from a patch script that cleared invulnerable station flags.
    # This will make the queue name and text body replaceable.
    # Since the shell text naturally has {} in it, don't use format here, just
    #  use replace.
    # Update: the 'check' term in the cue definition indicates what to do when
    #  the first condition check fails; in the invuln-station-fix, it is set to
    #  cancel, indicating that when it checks on a new game (player age check
    #  fails) it will cancel and not run the cue.
    #  To ensure these cues do run on new games, do not use a check value, or
    #  set it to none, which should put the cue on a constant recheck.
    shell_text = r'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<?xml-stylesheet href="director.xsl" type="text/xsl" ?>
<director name="template" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="director.xsd">
    <documentation>
    <author name="X4_Customizer" alias="..." contact="..." />
    <content reference="X4_Customizer" name="X4_Customizer generated" description="Director command injector." />
    <version number="0.0" date="today" status="testing" />
    </documentation>
    <cues>
    <cue name="INSERT_CUE_NAME">
        <condition>
        <check_value value="{player.age}" min="1s"/>
        </condition>
        <timing>
        <time exact="1s"/>
        </timing>
        <action>
        <do_all>
            INSERT_BODY
        </do_all>
        </action>
    </cue>
    </cues>
</director>
'''.replace('INSERT_CUE_NAME', cue_name).replace('INSERT_BODY', body_text)

    # TODO: maybe clean up formatting here for indents, which will also
    #  allow for cleaning up the text block indents above.

    # Record a file object to be written later.
    File_Manager.Add_File(File_Manager.Misc_File(
        virtual_path = 'director/' + file_name, 
        text = shell_text))

    return


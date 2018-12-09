'''
Classes to represent game files.
'''
import os
#import xml.etree.ElementTree as ET
#from xml.dom import minidom
from lxml import etree as ET
from copy import deepcopy
from collections import OrderedDict, defaultdict

from .. import Common
Settings = Common.Settings
from . import XML_Diff

class Game_File:
    '''
    Base class to represent a source file.
    This may be read from the source folder or a cat/dat pair.
    In either case, this will capture some properties of the file
    for organization purposes.

    Attributes:
    * name
      - String, name of the file, without pathing, and uncompressed.
      - Automatically parsed from virtual_path.
    * virtual_path
      - String, the path to the file in the game's virtual file system,
        using forward slash separators, including name, uncompressed.
      - Does not include the 'addon' folder.
      - This is the same as used in transform requirements and loads.
    * file_source_path
      - String, sys path where the file's original contents were read from,
        either a loose file or a cat file.
      - Mainly for debug checking.
      - None for generated files.
    * modified
      - Bool, if True then this file should be treated as modified,
        to be written out.
      - Files only read should leave this flag False.
      - Pending development; defaults False for now.
    * from_source
      - Bool, if True then this file originates from some source
        which was possibly modified, else it is completely new.
      - Has some impact on write format, eg. xml diff patching.
    '''
    def __init__(
            self,
            virtual_path,
            file_source_path = None,
            modified = False,
            from_source = False,
        ):
        # Pick out the name from the end of the virtual path.
        self.name = virtual_path.split('/')[-1]
        self.virtual_path = virtual_path
        self.file_source_path = file_source_path
        self.modified = modified
        self.from_source = from_source


    # TODO: maybe merge this into usage locations.
    def Get_Output_Path(self):
        '''
        Returns the full path to be used when writing out this file
        after any modifications, including file name.
        '''
        return Settings.Get_Output_Path() / self.virtual_path

        
# Note: encoding assumed to be utf-8 in general.
# A grep of the x4 dat files didn't find any non-utf8 xml encodings.
# Mods may be non-utf8; keep the logic for handling encoding here just
#  for these cases, though always output again in utf8.
class XML_File(Game_File):
    '''
    Simple XML file contents holder.

    Attributes:
    * encoding
      - String indicating the encoding type of the xml.
    * _text
      - Raw text for this file. Do not access directly, as this may be
        changed in the future to store only xml nodes.
    * xml_header_lines
      - List of strings, original header lines from the xml text,
        including the encoding declaration and the stylesheet
        declaration.
    * original_root
      - Element holding the original parsed xml, pre-transforms,
        possibly with prior diff patches applied.
    * modified_root
      - Element holding transformed xml, suitable for generating
        new diff patches.
    '''
    def __init__(self, file_binary, modifies_existing_xml = False, **kwargs):
        super().__init__(**kwargs)
        
        # Get the encoding to use, since xml files are sensitive to this.
        self.encoding = self.Find_Encoding(file_binary)

        # Translate to text with this encoding.
        # Note: when using 'open()' to read a file, python will convert
        #  line endings to \n even if they were \r\n. Python strings also
        #  use a bare \n, so doing string searches on file contents
        #  requires the file be normalized to \n. When using bytes.decode,
        #  it does not do newline conversion, so that is done explicitly
        #  here.
        self._text = file_binary.decode(self.encoding).replace('\r\n','\n')

        # Process into an xml tree.
        # Strip out blank text here, so that prettyprint works later.
        self.original_root = ET.XML(
            file_binary,
            parser = ET.XMLParser(remove_blank_text=True))
        # Set the initial modified tree to a deep copy of the above,
        #  so it can be freely modified.
        self.modified_root = None
        return
    

    @staticmethod
    def Find_Encoding(file_binary):
        '''
        Tries to determine the encoding to use for reading or writing an
        xml file.
        Returns a string name of the encoding.
        '''
        # Codec is found on the first line. Examples:
        #  <?xml version="1.0" encoding="ISO-8859-1" ?>
        #  <?xml version="1.0" encoding="UTF-8" ?>
        # Getting the encoding right is important for special character
        #  handling, and also ensuring other programs that load any written
        #  file based on the xml declared encoding will be using the right one
        #  (eg. utf-8 wasn't used to write an xml file declared as iso-8859
        #   or similar).

        # Convert binary to text; always treating as utf-8 (since this
        #  seems to be the most reliable, and is generally the default).
        file_text = file_binary.decode('utf-8').replace('\r\n','\n')

        # Get the first line by using split lines in a loop, and break early.
        for line in file_text.splitlines():
            # If there is no encoding specified on the first line, as with
            #  script files, just assume utf-8.
            if not 'encoding' in line:
                return 'utf-8'

            # Just do some quick splits to get to the code string.
            # Split on 'encoding'
            subline = line.partition('encoding')[2]

            # This should now have '="ISO-8859-1"...'.
            # Remove the '='.
            subline = subline.replace('=','')

            # Split on all quotes.
            # This will create a an empty string for text before
            #  the first quote.
            split_line = subline.split('"')

            # There should be at least 3 entries,
            #  [empty string, encoding string, other stuff].
            assert len(split_line) >= 3

            # The second entry should be the encoding.
            encoding = split_line[1]
            # Send it back.
            return encoding
            
        # Shouldn't be here.
        assert False
        return


    def Get_Root(self):
        '''
        Return an Element object with a copy of the current modified xml.
        The first call of this should occur after all initial patching is
        complete.
        '''
        if self.modified_root == None:
            # Set the initial modified tree to a deep copy of the original.
            self.modified_root = deepcopy(self.original_root)
        # Return a deepcopy of the modified_root, so that a transform
        #  can edit it safely, even if it exceptions out and doesn't
        #  complete.
        return deepcopy(self.modified_root)


    def Update_Root(self, element_root):
        '''
        Update the current modified xml from an xml node, either Element
        or ElementTree. Flags this file as modified. Requires the root
        element type be unchanged.
        '''
        assert element_root.tag == self.modified_root.tag
        # Assume the xml changed from the original.
        self.modified = True
        self.modified_root = element_root
        return


    # Note: xml only needs diffing if it originates from somewhere else,
    #  and isn't new.
    # TODO: set up a flag for new, non-diff xml files. For now, all need
    #  a diff.
    def Get_Diff(self):
        '''
        Generates an xml tree holding a diff patch, will convert from
        the original tree to the modified tree.
        '''
        patch_node = XML_Diff.Make_Patch(
            original_node = self.original_root, 
            modified_node = self.Get_Root())
        return patch_node


    def Get_Binary(self):
        '''
        Returns a bytearray with the full modified_root.
        TODO: swap to diff patch output.
        '''
        # Pack into an ElementTree, to get full header.
        # Modified source files will form a diff patch, others
        # just record full xml.
        if self.from_source:
            etree = ET.ElementTree(self.Get_Diff())
        else:
            etree = ET.ElementTree(self.Get_Root())

        # Pretty print it. This returns bytes.
        binary = ET.tostring(etree, encoding = 'utf-8', pretty_print = True)
        # To be safe, add a newline at the end if there.
        if not binary.endswith(b'\n'):
            binary += '\n'.encode(encoding = 'utf-8')
        return binary


    def Write_File(self, file_path):
        '''
        Write these contents to the target file_path.
        '''
        # Do a binary write.
        with open(file_path, 'wb') as file:
            file.write(self.Get_Binary())                      
        return


    def Patch(self, other_xml_file):
        '''
        Merge another xml_file into this one.
        Changes the original_root, and does not flag this file as modified.
        '''
        # Diff patches have a series of add, remove, replace nodes.
        # These will operate on the original tree, not the original root,
        # (allowing direct removal/replacement of the root), so first
        # set up proper trees.
        modified_node = XML_Diff.Apply_Patch(
            original_node = self.original_root, 
            patch_node    = other_xml_file.original_root )
        
        # Record this as the new original root.
        self.original_root = modified_node
        return


# TODO: split this into separate text and binary versions.
class Misc_File(Game_File):
    '''
    Generic container for misc file types transforms may generate.
    This will only support file writing.

    Attributes:
    * text
      - String, raw text for the file. Optional if binary is present.
    * binary
      - Bytes object, binary for this file. Optional if text is present.
    '''
    def __init__(self, text = None, binary = None, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.binary = binary
        

    def Get_Text(self):
        '''
        Returns the text for this file.
        '''
        return self.text

    
    def Get_Binary(self):
        '''
        Returns a bytearray with the file contents.
        '''
        if self.binary != None:
            return self.binary
        else:
            assert self.text != None
            binary = bytearray(self.text.encode())
            # To be safe, add a newline at the end if there.
            if not self.text.endswith('\n'):
                binary += '\n'.encode()
            return binary
        

    def Write_File(self, file_path):
        '''
        Write these contents to the target file_path.
        '''
        if self.text != None:
            # Do a text write.
            with open(file_path, 'w') as file:
                # To be safe, add a newline at the end if there isn't
                #  one, since some files require this (eg. bods) to
                #  be read correctly.
                file.write(self.text)
                if not self.text.endswith('\n'):
                    file.write('\n')

        elif self.binary != None:
            # Do a binary write.
            with open(file_path, 'wb') as file:
                file.write(self.binary)
                
        return


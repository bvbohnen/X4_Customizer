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
      - Should be False (default) for any original files.
    * source_extension_names
      - List of strings, the names of the extensions that contributed
        to this file's contents, either directly or through patching.
    '''
    def __init__(
            self,
            virtual_path,
            file_source_path = None,
            modified = False,
            from_source = False,
            # Can supply an initial extension name.
            extension_name = None,
        ):
        # Pick out the name from the end of the virtual path.
        self.name = virtual_path.split('/')[-1]
        self.virtual_path = virtual_path
        self.file_source_path = file_source_path
        self.modified = modified
        self.from_source = from_source
        self.source_extension_names = []
        if extension_name:
            self.source_extension_names.append(extension_name)
        return


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
    XML file contents. This will keep a record of the original xml
    intitialized with, returns a copy of it for editing, and interfaces
    with the diff patch module for both applying and creating patches.

    Parameters:
    * file_binary
      - Bytes object holding the xml text binary.
      - Optional if xml_root given.
    * xml_root
      - Element holding the root node.
      - Optional if file_binary given.

    Attributes:
    * original_root
      - Element holding the original parsed xml, pre-transforms,
        possibly with prior diff patches applied.
    * modified_root
      - Element holding transformed xml, suitable for generating
        new diff patches.
    '''
    def __init__(
            self, 
            file_binary = None, 
            xml_root = None,
            **kwargs):
        super().__init__(**kwargs)

        # Should receive either the binary or the xml itself.
        assert file_binary != None or xml_root != None
        
        if file_binary != None:
            # Process into an xml tree.
            # Strip out blank text here, so that prettyprint works later.
            self.original_root = ET.XML(
                file_binary,
                parser = ET.XMLParser(remove_blank_text=True))

        elif xml_root != None:
            assert isinstance(xml_root, ET._Element)
            self.original_root = xml_root

        # Set the initial modified tree to a deep copy of the above,
        #  so it can be freely modified.
        self.modified_root = None
        return
    

    def Get_Root(self):
        '''
        Return an Element object with a copy of the current modified xml.
        The first call of this should occur after all initial patching is
        complete, as that is when the original_root is first annotated
        and copied.
        '''
        if self.modified_root == None:
            # Annotate the original_root with node ids, since it is no
            #  longer changing.
            XML_Diff.Fill_Node_IDs(self.original_root)
            # Set the initial modified tree to a deep copy of the original;
            #  this will keep node_ids intact.
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
            modified_node = self.Get_Root(),
            maximal = Settings.make_maximal_diffs,
            verify = True)
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
            tree = ET.ElementTree(self.Get_Diff())
        else:
            tree = ET.ElementTree(self.Get_Root())

        # Pretty print it. This returns bytes.
        binary = XML_Diff.Print(tree, encoding = 'utf-8')
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
        #  (allowing direct removal/replacement of the root), so first
        #  set up proper trees.
        modified_node = XML_Diff.Apply_Patch(
            original_node = self.original_root, 
            patch_node    = other_xml_file.original_root )
                
        # Record this as the new original root.
        self.original_root = modified_node

        # Record the extension holding the patch, as a source for
        #  this file.
        self.source_extension_names.extend(other_xml_file.source_extension_names)        
        # TODO: for extension dependencies, maybe also track which
        #  nodes were modified by the extension (so that if they are
        #  further modified by transforms then that extension can be
        #  set as a final dependency). Think about how to do this
        #  in detail. For now, other extensions always create dependencies
        #  on any file modification.
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


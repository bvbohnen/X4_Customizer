'''
Classes to represent game files.
'''
__all__ = [
    'New_Game_File',
    'Generate_Signatures',
    'Misc_File',
    'XML_File',
    'XML_Text_File',
    'XML_Wares_File',
    'XML_Index_File',
    'Machine_Code_File',
    'Signature_File',
    'Text_File',
    ]

import os
#import xml.etree.ElementTree as ET
#from xml.dom import minidom
from lxml import etree as ET
from copy import deepcopy
from collections import OrderedDict, defaultdict
import fnmatch
import time

from ..Common import Plugin_Log
from ..Common import Settings
from ..Common import Print
#Settings = Common.Settings
from . import XML_Diff


def New_Game_File(binary, **kwargs):
    '''
    Creates and returns a Game_File, picking an appropriate subclass
    based on the virtual_path.  For use with 'binary' input data.
    All inputs should be given as keyword args.
    '''
    virtual_path = kwargs['virtual_path']
    split = virtual_path.rsplit('.',1)

    # If no suffix, just consider misc.
    if len(split) == 1:
        class_type = Misc_File

    else:
        suffix = split[1]

        # Check for xml files (ogl is an xml shader spec).
        if suffix in ['xml','ogl']:

            # Default generic xml.
            class_type = XML_File

            # Check for special file types.
            if virtual_path.startswith('t/'):
                class_type = XML_Text_File

            elif virtual_path == 'libraries/wares.xml':
                class_type = XML_Wares_File

            # Macros and components are in index/, but mousecursors is in
            # libraries and doesn't have full paths.
            # TODO: maybe drop support for mousecursors.
            elif (virtual_path.startswith('index/') 
            or virtual_path == 'libraries/mousecursors.xml'):
                class_type = XML_Index_File

        elif suffix == 'xsd':
            # These are xml style documentation of xml syntax.
            # May be compatible with xml, so try that.
            class_type = XML_File

        elif suffix in ['exe','dll']:
            # Raw x86 code files.
            class_type = Machine_Code_File
        
        elif suffix == 'sig':
            # Generic signature.
            class_type = Signature_File
        
        elif suffix in ['f','v','vh','tcs','tes']:
            class_type = Text_File

        else:
            # Generic binary file.
            class_type = Misc_File

    # Build and return the game file.
    return class_type(binary = binary, **kwargs)


def Generate_Signatures(game_file_list):
    '''
    Given a list of Game_Files, identifies which are missing signatures
    and creates them. All sig files are set as modified if their base
    file is also modified. Returns a list with the new Signature_Files.
    '''
    ret_list = []
    game_file_dict = {x.virtual_path : x for x in game_file_list}

    # Figure out which game_files do not already have a sig.
    std_virtual_paths = [x.virtual_path for x in game_file_list
                        if not isinstance(x, Signature_File)]
    sig_virtual_paths = [x.virtual_path for x in game_file_list
                        if isinstance(x, Signature_File)]

    for path in std_virtual_paths:
        sig_path = path + '.sig'

        # Create a sig file if needed.
        if sig_path not in sig_virtual_paths:
            # Empty sig for now. Could also give a 1024 byte value.
            sig_file = Signature_File(virtual_path = sig_path)
            game_file_dict[sig_path] = sig_file
            ret_list.append(sig_file)

        # Copy over the modified flag.
        game_file_dict[sig_path].modified = game_file_dict[path].modified

    return ret_list


class Game_File:
    '''
    Base class to represent a source file.
    This may be read from the source folder or a cat/dat pair.
    In either case, this will capture some properties of the file
    for organization purposes.

    Attributes:
    * name
      - String, name of the file, without pathing.
      - Automatically parsed from virtual_path.
    * virtual_path
      - String, the path to the file in the game's virtual file system,
        using forward slash separators, including name.
      - This is the same as used in transform requirements and loads.
    * suffix
      - The name suffix, with dot, eg. ".xml", or None if no suffix found.
    * file_source_path
      - String, sys path where the file's original contents were read from,
        either a loose file or a cat file.
      - None for generated files.
    * is_substitution
      - Bool, if True then this file came from a "subst_##.cat" style of
        catalog file, and is meant to replace any file that came before
        it.
      - False for core game files or other extension files.
    * modified
      - Bool, if True then this file should be treated as modified,
        to be written out.
      - Files only read should leave this flag False.
      - Pending development; defaults False for now.
    * from_source
      - Bool, if True then this file originates from some source
        on disk (cat, loose, etc.).
      - If False (default), this is is generated by the customizer.
      - Has some impact on write format, eg. xml diff patching.
      - If loading a file from disk but wanting to overwrite it during
        writeback, leave this as False.
    * edit_in_place
      - Bool, if True then this file originates from some loose file source
        and is being edited, where the original will be overwritten.
      - Intended just for use with an existing content.xml in the output
        extension folder.
      - Such files will not be recorded in the customizer log of
        written files.
    * extension_name
      - String, optional, name of the extension this file was read
        from.
    * source_extension_names
      - List of strings, the names of the extensions that contributed
        to this file's contents, either directly or through patching.
      - Will always include extension_name if given.
      - Empty if this is just a vanilla file.
    * written
      - Bool, if this file has had its changes written back out.
      - Used selectively by the file writeback system.
    * load_error
      - Bool, True if this file experienced a load error.
      - Generally, error files should be skipped.
      - Primarily used for empty xml files.
    '''
    def __init__(
            self,
            virtual_path,
            file_source_path = None,
            modified = False,
            from_source = False,
            edit_in_place = False,
            # Can supply an initial extension name.
            extension_name = None,
        ):
        # Pick out the name from the end of the virtual path.
        self.name = virtual_path.split('/')[-1]
        self.virtual_path = virtual_path
        
        split = self.name.rsplit('.',1)
        self.suffix = None
        if len(split) > 1:
            self.suffix = '.' + split[1]

        self.file_source_path = file_source_path
        self.written = False
        self.load_error = False

        # Can determine substitution status based on the source
        # catalog name.
        self.is_substitution = False
        if (self.file_source_path 
        and fnmatch.fnmatch(self.file_source_path.name, 'subst_*.cat')):
            self.is_substitution = True
            
        self.modified = modified
        self.from_source = from_source
        self.edit_in_place = edit_in_place
        self.source_extension_names = []
        self.extension_name = extension_name
        if extension_name:
            self.source_extension_names.append(extension_name)
        return

    def Get_Index_Path(self):
        '''
        Returns a path string matching the form used in index files, using
        backward slashes and no extension.
        TODO: somehow automate an extension prefix?
        '''
        path = self.virtual_path
        if self.suffix:
            path.replace(self.suffix,'')
        return path.replace('/', '\\')

    def Is_Patched(self):
        '''
        Returns True if this file is partly or wholy from an extension,
        else False. It will be considered 'patched' if it was overwritten.
        '''
        if self.source_extension_names:
            return True
        return False


    def Get_Source_Names(self):
        '''
        Returns a sorted list of source extension names, or [] if there
        are none.
        '''
        return sorted(self.source_extension_names)


    def Is_Modified(self):
        '''
        Returns True if this file has been modified by the customizer.
        '''
        return self.modified
    

    def Set_Modified(self):
        '''
        Sets this file as modified by the customizer.
        '''
        self.modified = True
        return


    # TODO: maybe merge this into usage locations.
    def Get_Output_Path(self):
        '''
        Returns the full path to be used when writing out this file
        after any modifications, including file name.
        '''
        return Settings.Get_Output_Folder() / self.virtual_path

    def Needs_Subst(self):
        '''
        Returns True if this file needs to be placed in a subst catalog
        due to replacing some original file.
        '''
        # If there was a source this read from, then assume a subst is
        # needed. XML type will override this.
        if self.file_source_path:
            return True
        return False

    def Copy(self, new_path):
        '''
        Make a copy of this game file, with the new virtual path.
        Does not automatically add to the file system; use Add_File.
        Does not update the index component or macro file with a reference.
        '''
        raise NotImplementedError()

    #def Is_Patch(self):
    #    '''
    #    Returns True if this file is a patch on existing files, else False.
    #    The general rule is that extension loose files are patches,
    #    as well as files sourced from catalogs with an 'ext_' prefix.
    #    '''
    #    # Non-extensions are not patches.
    #    if not self.extension_name:
    #        return False
    #
    #    # Files not sourced are not patches (this should never come
    #    # up since Is_Patched isn't called on such files, but include this
    #    # to be thorough.).
    #    if not self.from_source:
    #        return False
    #
    #    # 'subst_*.cat' catalog sources are not patches.
    #    if self.is_substitution:
    #        return False
    #
    #    # Everything else should be a patch.
    #    return True
        

    def Merge(self, other_file):
        '''
        Merge another file into this file, during loading.
        Returns the merged file, which may not be this object.
        Substitutions will overwrite this file, xml files will
        be patched, other files will be ignored.
        '''
        # Handle substitutions.
        if other_file.is_substitution:
            return self.Substitute(other_file)

        # Handle xml diff patches (or extra child nodes).
        elif isinstance(other_file, XML_File):
            self.Patch(other_file)
            return self

        # Handle everything else.
        # This was probably a mistake, so print a nice warning or error.
        # TODO: also comes up with gz (gzipped) model files; 
        #  maybe look into these, though not generally important.
        # Manually suppress warning for gz files for now, so dlc has
        # a clean printout.
        if not self.virtual_path.endswith('.gz'):
            Plugin_Log.Print(('Error: Skipping merge for "{}", extension file from "{}", '
                ).format( self.virtual_path,  other_file.file_source_path))
        return self


    def Substitute(self, other_file):
        '''
        Replace this file with the other_file, maybe copying over
        some properties. Returns the modified other_file.
        Subclasses should replace this with their own function
        as needed.
        '''
        # For generic files, just a straight copy.
        return other_file


    def Delayed_Init(self):
        '''
        Placeholder function for running any post-merging init.
        '''
        return

    def Standardize_Binary_Newlines(self, binary):
        '''
        If the given binary represents text, has newlines, and does not
        have carriage returns, this method adds the carriage returns
        and passed back the modified binary.
        '''
        # Standardize newlines to \r\n.
        newline = '\n'.encode()
        creturn = '\r'.encode()
        # Just in case it already uses \r\n, check for carriage returns first.
        # (Assume they don't show up otherwise.)
        if newline in binary and creturn not in binary:
            binary = binary.replace(newline, creturn + newline)
        return binary


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
    * binary
      - Bytes object holding the xml binary.
      - Optional if xml_root given.
    * xml_root
      - Element holding the root node.
      - Optional if binary given.

    Attributes:
    * original_root
      - Element holding the original parsed xml, pre-patches, pre-transforms.
    * patched_root
      - Element holding the diff patched root, pre-transforms.
    * modified_root
      - Element holding transformed xml, suitable for generating
        new diff patches.
    * root_tag
      - Tag name of the root node, for convenient referencing.
      - This is never expected to change across diff patches or transforms.
    * asset_class_name_dict
      - Dict, keyed by asset class as defined in the xml, holding a list of
        names of the asset nodes of the class type.
      - None if this xml doesn't contain asset nodes.
      - Example keys: 'weapon', 'missile', etc.
      - Often or always holds a single name that matches the last component
        of the virtual_path, without suffix.
      - TODO: maybe move this to an xml file subclass.
    * forced_xpath_attributes
      - String, similar to the option in Settings, these attributes or child
        xpath checks are added to any taken from Settings.
    '''
    # For assets, the names of the asset group, and asset node tag.
    # Tag is generally or always the singular of a plural asset group.
    valid_asset_tags = {'macros'     : 'macro',
                        'components' : 'component'}
    def __init__(
            self, 
            binary = None, 
            xml_root = None,
            **kwargs):
        super().__init__(**kwargs)
        self.asset_class_name_dict = None
        self.forced_xpath_attributes = ''

        # Should receive either the binary or the xml itself.
        assert binary != None or xml_root != None

        if binary != None:
            # Dummy files may have empty binary; handle specially.
            if len(binary) == 0:
                Plugin_Log.Print(f'Error: empty xml format file: {self.virtual_path}')
                self.original_root = None
            else:
                # Process into an xml tree.
                # Strip out blank text here, so that prettyprint works later.
                # Note: this could throw xml parsing errors if there are problems
                # with the file. Let the higher level catch such problems.

                # Note: in testing, if the xml file starts with a comment block,
                # and that block has a blank line, this XML function will double
                # count that line, causing the sourceline attributes on nodes
                # to be off. (This doesn't happen when using parse() on file
                # objects.) No clear fix at this time.
                self.original_root = ET.XML(
                binary,
                parser = ET.XMLParser(remove_blank_text=True))

        elif xml_root != None:
            assert isinstance(xml_root, ET._Element)
            self.original_root = xml_root
            
        if self.original_root != None:
            # Init the patched version to the original.
            # Deepcopy this, since patching will edit it in place.
            self.patched_root = deepcopy(self.original_root)
            self.modified_root = self.patched_root

            # The root tag should never be changed by mods, so can
            #  record it here pre-patching.
            self.root_tag = self.original_root.tag
        else:
            self.patched_root = None
            self.modified_root = None
            self.root_tag = None
            self.load_error = True
        return
    
    
    def Delayed_Init(self):
        '''
        Fills in node ids for the patched_root, and any other delayed
        setup that needs to account for diff patches.
        This should be called once after all patching is finished.
        '''
        if self.load_error:
            return

        # Annotate the patched_root with node ids.
        XML_Diff.Fill_Node_IDs(self.patched_root)
        
        # Skip if the tag doesn't match supported asset types.
        # Note: diff patches will have a 'diff' root, and don't
        # get matched here.
        if self.patched_root.tag not in self.valid_asset_tags:
            return

        # Get the subnode tag to look for.
        node_tag = self.valid_asset_tags[self.patched_root.tag]

        # Look through the root children for class attributes.
        # Normally there is just one for vanilla files, but there could
        # be multiple for mods.
        # If something is amiss, this might return none.
        # Note: observed to be empty in dlc for zone highways, so avoid
        #  printing error messages.
        asset_nodes = self.patched_root.findall('./'+node_tag)
        if not asset_nodes:
            #Plugin_Log.Print(('Error: asset file contains no assets;'
            #    'in file {}; sources: {}.').format(
            #        self.virtual_path, self.source_extension_names))
            return

        # Start a fresh dict to record these.
        self.asset_class_name_dict = defaultdict(list)
        for node in asset_nodes:
            asset_class_name = node.get('class')
            asset_name       = node.get('name')

            # Note: XR shippack has a garbage dock.xml file which has
            # no class defined. Skip errors, maybe with warning.
            if asset_class_name == None or asset_name == None:
                Plugin_Log.Print(('Error: asset file contains oddities;'
                    'in file {}; sources: {}; asset {} of class {}; skipping.'
                    ).format(
                        self.virtual_path, 
                        self.source_extension_names,
                        asset_class_name,
                        asset_name
                        ))
                continue

            # -Removed; multiple assets of same class and different name
            #  does come up, eg. in map cluster definitions.
            ## It is possible that the same asset name was defined
            ##  multiple times, most likely due to a file format
            ##  mistake (eg. a replacement style file was dropped in
            ##  with extensions).
            ## Catch that here with a warning, and continue in the
            ##  x4 style of using the first match.
            ## Generated xpaths below will need to account for this.
            #if asset_class_name in self.asset_class_name_dict:
            #    # Give the extensions sourced from in the log, to help
            #    # the extension checker know which ext to assign the
            #    # error to.
            #    Plugin_Log.Print(('Error: multiple assets found with name'
            #           ' {} in file {}; sources: {}; only the first will be used.'
            #           ).format(asset_name, self.virtual_path,
            #                    self.source_extension_names))

            self.asset_class_name_dict[asset_class_name].append(asset_name)
        return
    
    def Copy(self, new_path):
        '''
        Make a copy of this game file, with the new virtual path.
        Does not automatically add to the file system; use Add_File.
        '''
        assert new_path != self.virtual_path
        return self.__class__(
            virtual_path = new_path,
            xml_root = self.Get_Root(),
            )

    def Add_Forced_Xpath_Attributes(self, forced_xpath_attributes):
        '''
        Add a string of additional forced xpath attributes to any already
        present for this file.
        '''
        # Combine forced attributes with a comma.
        new_forced_attributes = self.forced_xpath_attributes
        if new_forced_attributes and forced_xpath_attributes:
            new_forced_attributes += ','
        new_forced_attributes += forced_xpath_attributes

        self.forced_xpath_attributes = new_forced_attributes
        return

    def Get_Asset_Xpath(self, name):
        '''
        Returns an xpath which will look up the base node for an asset.
        Used to distinguish between assets when multiple are present
        in a single file. This does not verify that the name or xpath
        are valid. Returns None if this is not an asset file.
        
        * name
          - String, name of the asset (macro or component) 
            as defined in the xml.
        '''
        if not self.asset_class_name_dict:
            return None
        # Look up the base node type. TODO: maybe pre-record this.
        tag = self.valid_asset_tags[self.root_tag]
        # To protect against multiple elements of the same name,
        # clarify this as the first match.
        return './{}[@name="{}"][1]'.format(tag,name)


    def Get_Root(self):
        '''
        Return an Element object with a copy of the current modified xml.
        The first call of this should occur after all initial patching is
        complete, as that is when the patched_root is first annotated
        and copied.
        '''
        if self.modified_root == None:
            # Set the initial modified tree to a deep copy of the patched
            #  version; this will keep node_ids intact.
            self.modified_root = deepcopy(self.patched_root)
        # Return a deepcopy of the modified_root, so that a transform
        #  can edit it safely, even if it exceptions out and doesn't
        #  complete.
        return deepcopy(self.modified_root)


    def Get_Root_Readonly(self, version = None):
        '''
        Returns an Element object with the current modified xml,
        or patched xml if no modifications made. It should not
        be written to, only read.

        * version
          - String, optional version of the root to return.
          - 'vanilla': returns the original root, pre-patching.
          - 'patched': returns the patched root, pre-transforms.
          - 'current': Default, returns the current modified root.
        '''
        if not version or version == 'current':
            # TODO: maybe just have modified_root init to the patched_root,
            # removing this check.
            if self.modified_root != None:
                return self.modified_root
            return self.patched_root
        elif version == 'vanilla':
            return self.original_root
        elif version == 'patched':
            return self.patched_root
        else:
            raise AssertionError(('Get_Root_Readonly version "{}" not'
                                    ' recognized').format(version))


    def Update_Root(self, element_root):
        '''
        Update the current modified xml from an xml node, either Element
        or ElementTree. Flags this file as modified. Requires the root
        element type be unchanged.
        '''
        # Error checks: make sure the returned element isn't any of the
        # existing nodes, which would indicate it was pulled as a
        # read only root.
        if (element_root is self.patched_root 
            or element_root is self.original_root 
            or element_root is self.modified_root
            # Backup check in case node ids go awry; the modified root
            # should have been created.
            or self.modified_root == None):
            raise AssertionError('Attempted to Update_Root with a read-only'
                                 ' existing root.')
        # Ensure tags match up.
        # TODO: consider ensuring the node ids match up; though that
        # wouldn't support complete xml replacements, it can catch
        # xml being written back from a different file (unless that
        # should be allowed).
        assert element_root.tag == self.modified_root.tag
        # Assume the xml changed from the patched version.
        self.modified = True
        self.modified_root = element_root
        return


    def Get_Xpath_Nodes(self, xpath, version = 'current'):
        '''
        Returns a list of read-only nodes found using the given xpath on
        the given version of the xml root. Defaults to the 'current' version.
        Nodes should not be modified.
        Subclasses may offer special handling of this to speed up
        xpath searches on large xml files with regular structure
        for doing value lookups.
        '''
        root = self.Get_Root_Readonly(version)
        nodes = root.xpath(xpath)
        return nodes


    # Note: xml only needs diffing if it originates from somewhere else,
    #  and isn't new.
    # TODO: set up a flag for new, non-diff xml files. For now, all need
    #  a diff.
    def Get_Diff(self):
        '''
        Generates an xml tree holding a diff patch, will convert from
        the original tree to the modified tree.
        '''
        if Settings.profile:
            start = time.time()

        # Combine forced attributes with a comma.
        forced_attributes = Settings.forced_xpath_attributes
        if forced_attributes and self.forced_xpath_attributes:
            forced_attributes += ','
        forced_attributes += self.forced_xpath_attributes

        patch_node = XML_Diff.Make_Patch(
            original_node = self.patched_root, 
            modified_node = self.Get_Root_Readonly(),
            forced_attributes = forced_attributes,
            maximal = Settings.make_maximal_diffs,
            verify = True)

        if Settings.profile:
            Print('XML_Diff.Make_Patch for {} time: {:.2f}'.format(
                self.name, time.time() - start))
        return patch_node


    def Get_Binary(self, version = 'current', no_diff = False, for_cat = False):
        '''
        Returns a bytearray with the full modified_root.

        * version
          - Version of the file to return binary for.
        * no_diff
          - Bool, set False to suppress diff packing and get the fully
            expanded binary.
          - Note: only edited source files, current version, return diff
            files normally; others will always have full binary.
        * for_cat
          - Bool, set True if this binary is going to be placed in a catalog
            file. Changes newline handling (simple linefeed).
        '''
        # Pack into an ElementTree, to get full header.
        # Modified source files will form a diff patch, others
        # just record full xml.
        # Non-xml will not support diffs.
        if (self.from_source
        and not self.edit_in_place
        and not no_diff 
        and version == 'current' 
        and self.virtual_path.endswith('.xml')):
            tree = ET.ElementTree(self.Get_Diff())
        else:
            tree = ET.ElementTree(self.Get_Root_Readonly(version))

        # Pretty print it. This returns bytes.
        binary = XML_Diff.Print(tree, encoding = 'utf-8', xml_declaration = True)

        # To be safe, add a newline at the end if not there, since
        # some file readers need it.
        # -Removed for now; ego cat/dats do not add extra newlines.
        #newline_char = '\n'.encode(encoding = 'utf-8')
        #if not binary.endswith(newline_char):
        #    binary += newline_char
        
        # TODO: maybe standardize always anyway.
        if for_cat:
            binary = self.Standardize_Binary_Newlines(binary)
        return binary


    def Write_File(self, file_path):
        '''
        Write these contents to the target file_path.
        '''
        # Create the directory as needed.
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents = True)

        # Do a binary write. Get binary first, in case of error, then
        # open the file to write.
        binary = self.Get_Binary()
        with open(file_path, 'wb') as file:
            file.write(binary)
        return
    
    def Needs_Subst(self):
        '''
        Returns False for xml files, True for other extensions.
        '''
        # Note: in a quick test of ogl it did not seem diff patching worked
        # for non-xml. Further, ogl files have to be in subst else they
        # are not found.
        if not self.virtual_path.endswith('.xml'):
            return True
        return False
    
    def Substitute(self, other_file):
        '''
        Replace this file with the other_file, this version's vanilla
        code into the other_file, and verifying tags match.
        '''
        # Start with the tag match. This can go wrong if there was
        # a mistake in the substitution.
        # This will be a soft error message only, since x4 allows this
        # to happen silently.
        if self.root_tag != other_file.root_tag:
            Plugin_Log.Print(('Error: xml file substitution performed with'
                ' mismatched root tags: [{}, {}]; in file {}, from extension {}.'
                ).format(self.root_tag, other_file.root_tag,
                    self.virtual_path, other_file.extension_name))
            
        # Preserve this root as the original.
        other_file.original_root = self.original_root
        
        # Based on x4 log errors, it seems that it will handle
        #  diff xmls (when fed as an original file or substitution)
        #  as empty files. Do that here, to better match
        #  the game's error logging.
        if other_file.root_tag == 'diff':
            # Remove all children of the diff node, on the assumption
            # x4 is processing them somehow. Still want a base node
            # to remain in place.
            for child in list(other_file.patched_root.getchildren()):
                other_file.patched_root.remove(child)

        return other_file


    def Patch(self, other_xml_file):
        '''
        Merge another xml_file into this one.
        Changes the patched_root, and does not flag this file as modified.
        '''        
        # Add a nice printout.
        # -Removed; kinda spammy.  TODO: add back in in a verbose mode.
        #Plugin_Log.Print('XML patching {}: to {}, from {}'.format(
        #        self.virtual_path,
        #        self.file_source_path,
        #        other_xml_file.file_source_path))

        # Diff patches have a series of add, remove, replace nodes.
        # Operated on the patched_root, leaving the original_root untouched.
        # Note: the patched_node root may be replaced, so need to capture
        # the result and restore it (normally it will just be the same
        # patched_root object).
        self.patched_root = XML_Diff.Apply_Patch(
            original_node = self.patched_root, 
            patch_node    = other_xml_file.patched_root,
            # For any errors, print out the file name, the patch extension
            # name. TODO: maybe include the already applied source
            # extension names, though that gets overly verbose.
            error_prefix  = '"{}" patched from extension "{}"'.format(
                self.virtual_path,
                other_xml_file.extension_name )
            )

        # Record the extension holding the patch, as a source for this file.
        self.source_extension_names.extend(other_xml_file.source_extension_names)
        
        # TODO: for extension dependencies, maybe also track which
        #  nodes were modified by the extension (so that if they are
        #  further modified by transforms then that extension can be
        #  set as a final dependency). Think about how to do this
        #  in detail. For now, other extensions always create dependencies
        #  on any file modification.
        return



class XML_Text_File(XML_File):
    '''
    XML file holding game text.
    This provides functionality for looking up text references.

    Attributes:
    * page_text_dict
      - Dict, keyed by 'page[id]' then 't[id]', holding the current
        text values. Keys are kept as strings.
      - Added to speed up performance compared to looking up
        text each time in the xml with xpath.
    * requests_until_refresh
      - Int, how many text lookup requests may occurred since the
        last page_text_dict reset (due to modification) before
        an automatic refresh is triggerred.
      - Used to prevent refreshing too often when fine grain
        modifications occur.
    '''
    '''
    Note: for writing out wares to html, 16% of the long runtime
    was spent on xpath lookups of ware names, hence the effort
    to speed this process up. (This may have been influenced
    by using a .// style xpath, since reduced to ./ style.)
    '''
    # Static value for how many requests are allowed before a refresh.
    # One request may count multiple times if there are recursive
    # text lookups, so don't make this too sensitive.
    # Note: number is an intuitive guess, and wasn't tested for optimality.
    # Note: setting 0 here will disable the refreshes.
    requests_until_refresh_limit = 20

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_text_dict = defaultdict(dict)
        self.requests_until_refresh = self.requests_until_refresh_limit
        return


    def Refresh_Cache(self):
        '''
        Reads the xml and sets up the page_text_dict.
        This will need a rerun when the xml gets modified and a new
        Read is requested, if it is to be beneficial.
        '''
        # Stop the counter.
        self.requests_until_refresh = 0
        # Skip early if the dict is already filled in.
        if self.page_text_dict:
            return
        for page_node in self.Get_Root_Readonly().getchildren():
            if page_node.tag != 'page':
                continue
            page_id = page_node.get('id')
            for t_node in page_node.getchildren():
                if t_node.tag != 't':
                    continue
                self.page_text_dict[page_id][t_node.get('id')] = t_node.text
        return


    def Update_Root(self, *args, **kwargs):
        '''
        Clears the page_text_dict when root is updated.
        '''
        super().Update_Root(*args, **kwargs)
        self.page_text_dict.clear()
        # Set the refresh countdown.
        self.requests_until_refresh = self.requests_until_refresh_limit
        return


    def Read(
            self, 
            text = None, 
            page = None, 
            id = None,
            ):
        '''
        Reads and returns the text at the given {page,id}.
        Returns None if no text found, or an error occurs.

        * text
          - String, including any internal '{page,id}' terms.
        * page, id
          - Int or string, page and id separated; give for direct
            dereference instead of a full text string.
        '''
        # Maybe do a refresh of the page_text_dict.
        if self.requests_until_refresh > 0:
            self.requests_until_refresh -= 1
            if self.requests_until_refresh <= 0:
                self.Refresh_Cache()

        # Verify if text is given, it is just in brackets, and split it.
        if text != None:
            try:
                # Split it apart.
                page, id = (text.replace(' ','').replace('{','')
                            .replace('}','').split(','))
            except Exception as ex:
                # Failure case; something weird was given as input.
                return
        else:
            # Verify page/id are given; failure it not.
            # TODO: maybe failure message.
            if page == None or id == None:
                return
            # Convert page/id to strings if needed.
            page = str(page)
            id = str(id)
            
        # Look up the entry.
        # Use xpath if the page_text_dict is not ready,
        # else use the dict for faster lookup.
        ret_text = None
        if self.page_text_dict:
            try:
                ret_text = self.page_text_dict[page][id]
            except KeyError:
                return
        else:
            nodes = self.Get_Root_Readonly().xpath(f'./page[@id="{page}"]/t[@id="{id}"]')
            if not nodes:
                return
            ret_text = nodes[0].text

        return ret_text

    
class XML_Index_File(XML_File):
    '''
    XML file holding a an index (effectively dict) of name:path pairs.
    Expected to be used for macros, components, and mousecursors.
    This will append a '.xml' extension to the looked up paths, since
    it is missing from the x4 source file paths.

    Attributes:
    * name_path_dict
      - Dict, keyed by entry name, with the virtual_path to an
        xml source file.
      - Paths will be lower cased; name is kept in original case.
    * requests_until_refresh
      - Int, how many text lookup requests may occurred since the
        last page_text_dict reset (due to modification) before
        an automatic refresh is triggerred.
      - Used to prevent refreshing too often when fine grain
        modifications occur.
    '''
    requests_until_refresh_limit = 5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name_path_dict = {}
        self.requests_until_refresh = self.requests_until_refresh_limit
        return

    def Refresh_Cache(self):
        '''
        Reads the xml and sets up the name_path_dict.
        This will need a rerun when the xml gets modified and a new
        Get is requested, if it is to be beneficial.
        '''
        # Stop the counter.
        self.requests_until_refresh = 0
        # Skip early if the dict is already filled in.
        if self.name_path_dict:
            return
        # Root is an <index> node, children are <entry> nodes.
        for entry_node in self.Get_Root_Readonly().getchildren():
            if entry_node.tag != 'entry':
                continue
            # Note: if a mod appends new entries to the index, they will
            #  overwrite those earlier in the index, as described at
            #  https://forum.egosoft.com/viewtopic.php?t=347831 .
            # No warning will be printed here, as such cases are assumed
            #  to be intentional.
            self.name_path_dict[entry_node.get('name')] = entry_node.get('value').lower() + '.xml'
        return


    def Update_Root(self, *args, **kwargs):
        '''
        Clears the page_text_dict when root is updated.
        '''
        super().Update_Root(*args, **kwargs)
        self.name_path_dict.clear()
        # Set the refresh countdown.
        self.requests_until_refresh = self.requests_until_refresh_limit
        return


    def Find(self, name):
        '''
        Returns the indexed path matching the given name, or None
        if the name is not found. Name is case sensitive.
        '''
        # Maybe do a refresh of the name_path_dict.
        if self.requests_until_refresh > 0:
            self.requests_until_refresh -= 1
            if self.requests_until_refresh <= 0:
                self.Refresh_Cache()

        # Do a normal or xpath lookup, depending on cache status.
        # Name is not lowercased, to preserve it for the xpath.
        if self.name_path_dict:
            return self.name_path_dict.get(name, None)
        else:
            root = self.Get_Root_Readonly()
            nodes = root.xpath('./entry[@name="{}"]'.format(name))
            if not nodes:
                value = nodes[0].get('value', None)
                if value != None:
                    return value.lower() + '.xml'
        return None


    def Findall(self, pattern):
        '''
        Find and returns a set of all values matching the given key
        pattern, with wildcard support.
        Eg. Findall('ship_*') is expected to find every ship file path.
        Duplicates are ignored.
        '''
        # Use the cached dict for this; ensure it is filled in.
        self.Refresh_Cache()

        # Seach the keys.
        #ret_list = []
        #for key, value in self.name_path_dict.items():
        #    if fnmatch(key, pattern):
        #        ret_list.add(value)
        # Switch to filter() for speed.
        keys = fnmatch.filter(self.name_path_dict.keys(), pattern.lower())
        # TODO: is the set cast needed?
        return set([self.name_path_dict[x] for x in keys])


class XML_Wares_File(XML_File):
    '''
    The libraries/wares.xml file. This has some functionality for
    speeding up xpath reads.

    Attributes:
    * version_ware_node_dict
      - Dict, keyed by version then by 'ware[id]', holding the node for
        each ware.
      - Added to speed up performance compared to looking up
        nodes each time in the xml with xpath, when the xpaths
        have ware id qualifiers.
    * requests_until_refresh
      - Int, how many text lookup requests may occurred since the
        last ware_node_dict reset (due to modification) before
        an automatic refresh is triggerred.
      - Used to prevent refreshing too often when fine grain
        modifications occur.
    '''
    '''
    Note: this caching dropped the wares live editor object parsing
    from 18 seconds down to 2, compared to using the full xpath
    every time.
    '''
    requests_until_refresh_limit = 5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert self.virtual_path == 'libraries/wares.xml'
        self.version_ware_node_dict = defaultdict(dict)
        self.requests_until_refresh = self.requests_until_refresh_limit
        return
    

    def Refresh_Cache(self):
        '''
        Reads the xml and sets up the ware_node_dict.
        This will need a rerun when the xml gets modified and a new
        Get_Xpath_Nodes is requested, if it is to be beneficial.
        The 'vanilla' and 'patched' versions will be filled once
        and never cleared.
        '''
        # Stop the counter.
        self.requests_until_refresh = 0
        for version in ['vanilla','patched','current']:
            # Skip if already filled in.
            if self.version_ware_node_dict[version]:
                continue
            # Convenience renaming.
            this_dict = self.version_ware_node_dict[version]
            # Loop over the wares.
            for ware_node in self.Get_Root_Readonly(version).getchildren():
                if ware_node.tag != 'ware':
                    continue
                # Store it by id.
                this_dict[ware_node.get('id')] = ware_node
        return


    def Update_Root(self, *args, **kwargs):
        '''
        Clears version_ware_node_dict['current'] when root is updated.
        '''
        super().Update_Root(*args, **kwargs)
        self.version_ware_node_dict['current'].clear()
        # Set the refresh countdown.
        self.requests_until_refresh = self.requests_until_refresh_limit
        return
    

    def Get_Xpath_Nodes(self, xpath, version = 'current'):
        '''
        Returns a list of nodes found using the given xpath on the given
        version of the xml root. Defaults to the 'current' version.
        Nodes should be considered read only.

        If the xpath starts with the pattern './ware[@id="*"]/*', its
        lookup will be accelerated.
        '''
        # Maybe do a refresh of the version_ware_node_dict.
        if self.requests_until_refresh > 0:
            self.requests_until_refresh -= 1
            if self.requests_until_refresh <= 0:
                # This will fill in all versions, which shouldn't
                # have much overhead vs just one version, and saves
                # this from having to have separate version countdowns.
                self.Refresh_Cache()

        # Check if the cache is ready.
        ware_nodes = None
        if self.version_ware_node_dict[version]:

            # Check the xpath start.
            if xpath.startswith('./ware[@id="'):
                # Split out the id.
                id, remainder = xpath.replace('./ware[@id="','').split('"]',1)

                # If the remainder is empty or a '/', can continue,
                # otherwise do a normal xpath since there are more
                # qualifiers.
                if not remainder or remainder[0] == '/':

                    # Look up the node from the cache.
                    ware_node = self.version_ware_node_dict[version].get(id)
                    if ware_node != None:
                        # If there is a remainder, reform it into a further
                        #  xpath starting from the ware node.
                        if remainder:
                            new_xpath = '.' + remainder
                            ware_nodes = ware_node.xpath(new_xpath)
                        # Otherwise, just return this ware.
                        else:
                            ware_nodes = [ware_node]                               

        # If nothing was found in the cache, do a normal lookup.
        if not ware_nodes:
            ware_nodes = super().Get_Xpath_Nodes(xpath, version)            
        return ware_nodes


# TODO: split this into separate text and binary versions.
class Misc_File(Game_File):
    '''
    Generic container for misc file types transforms may generate.
    This will only support file writing.

    Attributes:
    * text
      - String, raw text for the file. 
      - Optional if binary is present.
    * binary
      - Bytearray object holding the binary (may be given as bytes).
      - Optional if text is present.
    '''
    def __init__(self, text = None, binary = None, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.binary = binary
        if binary != None:
            self.binary = bytearray(binary)
        

    def Get_Text(self):
        '''
        Returns the text for this file.
        '''
        return self.text

    def Set_Text(self, text):
        '''
        Overwrites the text for this file.
        '''
        self.modified = True
        self.text = text
    
    def Get_Binary(self, for_cat = False, **kwargs):
        '''
        Returns a bytearray with the file contents.
        Does not currently support distinguishing vanilla from patched files.

        * for_cat
          - Bool, set True if this binary is going to be placed in a catalog
            file. Changes newline handling (simple linefeed) for text.
        '''
        if self.binary != None:
            return self.binary
        else:
            assert self.text != None

            # To be safe, add a newline at the end.
            # -Removed for now; ego cat/dats do not add extra newlines.
            #text = self.text
            #if not text.endswith('\n'):
            #    text += '\n'

            # Encode it, using generic utf-8.
            binary = bytearray(self.text.encode(encoding = 'utf-8'))

            # TODO: maybe standardize always anyway.
            if for_cat:
                binary = self.Standardize_Binary_Newlines(binary)
            return binary
        

    def Write_File(self, file_path):
        '''
        Write these contents to the target file_path.
        '''
        # Create the directory as needed.
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents = True)

        if self.text != None:
            binary = self.Get_Binary()
        elif self.binary != None:
            binary = self.binary
        else:
            return

        # Do a binary write.
        with open(file_path, 'wb') as file:
            file.write(binary)
        return
    

class Text_File(Misc_File):
    '''
    File holding text.  Eg. shader c-style code.
    Mostly a dummy class.
    '''
    def __init__(self, text = None, binary = None, **kwargs):
        super().__init__(**kwargs)
        if text != None:
            self.text = text
        else:
            assert binary != None
            # Manually standardize newlines.
            self.text = binary.decode().replace('\r\n','\n').replace('\r','\n')
    
    def Needs_Subst(self):
        # Shader files may need to be packed, else they are not found
        # and crash the game right away (if referenced by ogl specs).
        # Since text_files are only used for shaders right now, always pack.
        return True


class Machine_Code_File(Game_File):
    '''
    Contents of an exe or dll file, holding the binary data.
    These files are not packed into cats/dats, and may have some
    other special handling.
    
    Attributes:
    * binary
      - Bytearray object holding the machine binary (may be given as bytes).
    '''
    def __init__(
            self, 
            binary, 
            **kwargs):
        super().__init__(**kwargs)
        self.binary = bytearray(binary)
        return
    
    def Get_Output_Path(self):
        '''
        Returns a path back to the X4 main folder to write to, using
        a modified file name. Avoids overwriting the original.
        '''
        suffix = '.' + self.virtual_path.split('.')[-1]
        return Settings.Get_X4_Folder() / self.virtual_path.replace(
                suffix, Settings.root_file_tag + suffix)
    
    # Note: no Get_Binary method for now; this shouldn't be
    # packed with anything, which is the primary use of such a method.

    def Write_File(self, file_path):
        '''
        Write these contents to the target file_path.
        '''
        # Create the directory as needed.
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents = True)

        # Do a binary write.
        with open(file_path, 'wb') as file:
            file.write(self.binary)
        return
    
    def Needs_Subst(self):
        'Machine code never goes in catalogs, so does not need subst.'
        return False
    

class Signature_File(Misc_File):
    '''
    Small file holding the 1024-byte signature (or 0-byte dummy)
    of some other file. This is an alias of Misc_File.
    '''
    def __init__(self, text = None, binary = None, **kwargs):
        super().__init__(**kwargs)
        # Give default empty binary.
        if self.text == None and self.binary == None:
            self.binary = b''
        return
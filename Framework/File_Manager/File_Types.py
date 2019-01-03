'''
Classes to represent game files.
'''
import os
#import xml.etree.ElementTree as ET
#from xml.dom import minidom
from lxml import etree as ET
from copy import deepcopy
from collections import OrderedDict, defaultdict
import re
from fnmatch import fnmatch

from .. import Common
Settings = Common.Settings
from . import XML_Diff


def New_Game_File(binary, **kwargs):
    '''
    Creates and returns a Game_File, picking an appropriate subclass
    based on the virtual_path.  For use with 'binary' input data.
    All inputs should be given as keyword args.
    '''
    virtual_path = kwargs['virtual_path']

    # Check for xml files.
    if virtual_path.endswith('.xml'):

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

    else:
        # Generic binary file.
        class_type = Misc_File

    # Build and return the game file.
    return class_type(binary = binary, **kwargs)



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
    * extension_name
      - String, optional, name of the extension this file was read
        from.
    * source_extension_names
      - List of strings, the names of the extensions that contributed
        to this file's contents, either directly or through patching.
      - Will always include extension_name if given.
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
        self.extension_name = extension_name
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


    def Is_Patch(self):
        '''
        Returns True if this file is a patch on existing files,
        else False. The general rule is that extension loose
        files are patches, as well as files sourced from
        catalogs with an 'ext_' prefix.
        '''
        # Non-extensions are not patches.
        if not self.extension_name:
            return False
        # 'subst_*.cat' catalog sources are not patches.
        if (self.file_source_path.name.startswith('subst_')
        and self.file_source_path.suffix == '.cat'):
            return False
        return True
        

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
      - TODO: maybe remove if not used often enough.
    * asset_class_name
      - Name of the asset class as defined in the xml, if this appears
        to be a recognized asset file (based on root node tag).
      - Eg. 'macro', 'component', etc.
    * asset_name
      - Specific name of the object defined in this file.
      - Often or always matches the last component of the virtual_path,
        without suffix.
    '''
    valid_asset_tags = ['macros','components']

    def __init__(
            self, 
            binary = None, 
            xml_root = None,
            **kwargs):
        super().__init__(**kwargs)
        self.asset_class_name = None
        self.asset_name = None

        # Should receive either the binary or the xml itself.
        assert binary != None or xml_root != None
        
        if binary != None:
            # Process into an xml tree.
            # Strip out blank text here, so that prettyprint works later.
            self.original_root = ET.XML(
                binary,
                parser = ET.XMLParser(remove_blank_text=True))

        elif xml_root != None:
            assert isinstance(xml_root, ET._Element)
            self.original_root = xml_root

        # Init the patched version to the original.
        # Deepcopy this, since patching will edit it in place.
        self.patched_root = deepcopy(self.original_root)
        self.modified_root = None

        # The root tag should never be changed by mods, so can
        #  record it here pre-patching.
        self.root_tag = self.original_root.tag
        return
    
    
    def Delayed_Init(self):
        '''
        Fills in node ids for the patched_root, and any other delayed
        setup that needs to account for diff patches.
        This should be called once after all patching is finished.
        '''
        # Annotate the patched_root with node ids.
        XML_Diff.Fill_Node_IDs(self.patched_root)
        
        # Skip if the tag doesn't match supported asset types.
        # Note: diff patches will have a 'diff' root, and don't
        # get matched here.
        if self.patched_root.tag not in self.valid_asset_tags:
            return

        # Look through the root children for class attributes.
        # Currently, this always expects 1 child that should always
        #  have a class; toss an error if that isn't so.
        assert len(self.patched_root) == 1

        # Want the inner tag, eg. 'macro' instead of 'macros',
        #  just because it makes for nicer lookup syntax.
        # -Nevermind; plural form helps visually distinguish from
        #  class_name
        #tag_name   = root[0].tag
        self.asset_class_name = self.patched_root[0].get('class')
        self.asset_name       = self.patched_root[0].get('name')
        assert self.asset_class_name != None
        assert self.asset_name != None

        return


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
        nodes = root.findall(xpath)
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
        patch_node = XML_Diff.Make_Patch(
            original_node = self.patched_root, 
            modified_node = self.Get_Root_Readonly(),
            maximal = Settings.make_maximal_diffs,
            verify = True)
        return patch_node


    def Get_Binary(self):
        '''
        Returns a bytearray with the full modified_root.
        '''
        # Pack into an ElementTree, to get full header.
        # Modified source files will form a diff patch, others
        # just record full xml.
        if self.from_source:
            tree = ET.ElementTree(self.Get_Diff())
        else:
            tree = ET.ElementTree(self.Get_Root_Readonly())

        # Pretty print it. This returns bytes.
        binary = XML_Diff.Print(tree, encoding = 'utf-8', xml_declaration = True)
        # To be safe, add a newline at the end if not there, since
        # some file readers need it.
        newline_char = '\n'.encode(encoding = 'utf-8')
        if not binary.endswith(newline_char):
            binary += newline_char
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
        Changes the patched_root, and does not flag this file as modified.
        '''
        assert other_xml_file.Is_Patch()

        # Diff patches have a series of add, remove, replace nodes.
        # Operated on the patched_root, leaving the original_root untouched.
        XML_Diff.Apply_Patch(
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
        text values.
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


    # TODO: maybe a version that takes separate page and id terms.
    def Read(self, text = None, page = None, id = None):
        '''
        Reads and returns the text at the given {page,id}.
        Recursively expands nested references.
        Removes comments in parentheses.
        Returns None if no text found.

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

        # If page and id given, pack them in a string to reuse the
        # following code. Probably don't need to worry about performance
        # of this.
        if text == None:
            text = '{{{},{}}}'.format(page,id)
                       
        # Remove any comments, in parentheses.
        if '(' in text:
            # .*?     : Non-greed match a series of chars.
            # \( \)   : Match parentheses
            # (?<!\\) : Look behind for no preceeding escape char.
            # Note: put all this in a raw string to avoid python escapes.
            text = ''.join(re.split(r'(?<!\\)\(.*?(?<!\\)\)', text))
        #if text.startswith('(') and ')' in text:
        #    text = text.split(')',1)[1]

        # Remove leftover escape characters, blindly for now (assume
        # they are never escaped themselves).
        text = text.replace('\\','')

        # If lookups are present, deal with them recursively.
        # TODO: isn't this always the case with the current setup?
        #  -Maybe remove this check.
        if '{' in text:
            if not self.page_text_dict or 1:
                root = self.Get_Root_Readonly()

            # RE pattern used:
            #  .*    : Match a series of chars.
            #  .*?   : As above, but changes to non-greedy.
            #  {.*?} : Matches between { and }.
            #  ()    : When put around pattern in re.split, returns the
            #          separators (eg. the text lookups).
            new_text = ''
            for term in re.split('({.*?})', text):
                # Skip empty terms (eg. when there is no text before the 
                # first '{').
                if not term:
                    continue

                # Check if it is a nested lookup.
                if term.startswith('{'):
            
                    # Split it apart.
                    page, id = (term.replace(' ','').replace('{','')
                                .replace('}','').split(','))
            
                    # Look up the initial replacement.
                    # Use xpath if the page_text_dict is not ready,
                    # else use the dict for faster lookup.
                    if self.page_text_dict:
                        try:
                            replacement_text = self.page_text_dict[page][id]
                        except KeyError:
                            return
                    else:
                        node = root.find('./page[@id="{}"]/t[@id="{}"]'.format(page, id))
                        if node == None:
                            return
                        replacement_text = node.text
            
                    # In case this replacement has nested terms,
                    # recursively process it, and append to the running
                    # result.
                    new_text += self.Read(replacement_text)
                else:
                    # There was no lookup for this term; just append
                    # it back to the text string.
                    new_text += term

            # Overwrite the text with the replacements.
            text = new_text
            
        return text

    
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
            self.name_path_dict[entry_node.get('name')] = entry_node.get('value') + '.xml'
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
        if the name is not found.
        '''
        # Maybe do a refresh of the name_path_dict.
        if self.requests_until_refresh > 0:
            self.requests_until_refresh -= 1
            if self.requests_until_refresh <= 0:
                self.Refresh_Cache()

        # Do a normal or xpath lookup, depending on cache status.
        if self.name_path_dict:
            return self.name_path_dict.get(name, None)
        else:
            root = self.Get_Root_Readonly()
            node = root.find('./entry[@name="{}"]'.format(name))
            if node != None:
                value = node.get('value', None)
                if value != None:
                    return value + '.xml'
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
        ret_list = set()
        for key, value in self.name_path_dict.items():
            if fnmatch(key, pattern):
                ret_list.add(value)
        return ret_list


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
                            ware_nodes = ware_node.findall(new_xpath)
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


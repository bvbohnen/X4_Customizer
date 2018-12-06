'''
These transforms fix known bugs in the egosoft MD scripts.

Note: transforms planned; not yet implemented.
'''
import xml.etree.ElementTree as ET
from .Support import XML_Find_Match, XML_Find_All_Matches, Make_Director_Shell
from . import Support # TODO: move xml functions to another module.
from ... import File_Manager

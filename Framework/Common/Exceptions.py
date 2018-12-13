'''
Container for exception messages.
'''

class File_Missing_Exception(Exception):
    '''
    Exception raised when File_Manager.Load_File doesn't find the file,
    or the file is empty.
    '''

class Obj_Patch_Exception(Exception):
    '''
    Exception raised when an obj binary patch fails to find a
    matching reference pattern.
    '''
    
class Text_Patch_Exception(Exception):
    '''
    Exception raised when an text patch (often xml) fails to find a
    matching reference line.
    '''
    
class Gzip_Exception(Exception):
    '''
    Exception raised when gzip runs into a problem decompressing a file.
    '''    
    
class XML_Patch_Exception(Exception):
    '''
    Exception raised when failing during verification of a generated
    xml patch.
    '''

class Cat_Hash_Exception(Exception):
    '''
    Exception raised when a catalog being unpacked fails to verify
    an md5 hash.
    '''
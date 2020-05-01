'''
Various shared support functions for the transforms.
'''

import inspect
# This function will convert hex strings to bytes objects.
from binascii import unhexlify as hex2bin
from binascii import hexlify as bin2hex
import re

from Framework import Settings
from Framework import Print
from Framework import Binary_Patch_Exception
from Framework import File_Manager

# TODO: maybe move this to Analyses.
def Float_to_String(this_float, precision = 2):
    '''
    Returns a float as a string with cleaned up precision decimal places.
    '''
    return '{1:.{0}f}'.format(precision, this_float).rstrip('0').rstrip('.')

def Standardize_Match_Rules(rules):
    '''
    Puts matching rules into a standard form:
    (key string, match string, *values).
    Input forms supported are:
     (*values)
     ('*', *values)
     ('key match', *values)
    Value lists should never start with a string.
    Returns a list of standard form tuples.
    '''
    rule_list = []
    for rule in rules:
        try:
            # If length one, treat as just an always-matched value.
            if not isinstance(rule, (tuple,list)):
                # Prefix with wildcards.
                rule_list.append(('*','*',rule))
                continue

            # If the first item isn't a string, treat as a list of values.
            if not isinstance(rule[0], str):
                # Prefix with wildcards.
                rule_list.append(('*','*',*rule))
                continue

            # Break apart the first string.
            match_rule = rule[0]
            # The key could be a plain '*', or a key and match value
            # separated by a space (with maybe more spaces in the
            # match value).
            if match_rule == '*':
                rule_list.append(('*','*',*rule[1:]))
            else:
                key, match_value = match_rule.split(' ',1)
                # Strip off excess spacing that may have been present between
                # the key and value.
                match_value = match_value.strip()
                rule_list.append((key, match_value, *rule[1:]))

        except Exception:
            raise AssertionError(('Error when handling match'
                                  ' rule "{}"').format(rule))
    return rule_list


def XML_Modify_Int_Attribute(node, attr, rhs, operation):
    '''
    Operates on the given node attribute's value, eg. mult, sum, etc.
    Value is treated as an integer, and rounded before replacement.
    The value will be floored to 1 if the original was positive
    and non-0 and the multiplier is non-0.

    * rhs
      - The right hand side of the operation.
    * operation
      - String, one of ['*','+'].
    '''
    # Convert to int.
    value = int(node.get(attr))

    # Operate on it.
    if operation == '*':
        new_value = value * rhs
    elif operation == '+':
        new_value = value + rhs
    else:
        raise Exception()

    # Round, and re-int.
    new_value = int(round(new_value))
    node.set(attr, str(new_value))
    return



def XML_Multiply_Int_Attribute(node, attr, multiplier):
    '''
    Multiplies the given node attribute's value by the multiplier.
    Value is treated as an integer, and rounded before replacement.
    The value will be floored to 1 if the original was positive
    and non-0 and the multiplier is non-0.
    '''
    # Convert to int.
    value = int(node.get(attr))
    # Multiply, round, and re-int.
    new_value = int(round(value * multiplier))
    # If neither original term was 0, set a min of 1.
    if value > 0 and multiplier > 0 and new_value == 0:
        new_value = 1
    node.set(attr, str(new_value))
    return


def XML_Modify_Float_Attribute(node, attr, rhs, operation, precision = 4):
    '''
    Operates on the given node attribute's value, eg. mult, sum, etc.
    Value is treated as a float.

    * rhs
      - The right hand side of the operation.
    * operation
      - String, one of ['*','+'].
    * precision
      - Int, can set the number of decimal places, or None for unlimited.
      - Defaults to 4.
    '''
    # Convert to float.
    value = float(node.get(attr))

    # Operate on it.
    if operation == '*':
        new_value = value * rhs
    elif operation == '+':
        new_value = value + rhs
    else:
        raise Exception()
        
    # Limit string precision to a couple decimals.
    # For the sake of printouts, trim off trailing 0s; kinda ugly
    #  to do this in python, sadly.
    format_spec = ':{}f'.format('.{}'.format(precision) if precision else '')
    new_value_str = ('{'+format_spec+'}').format(new_value).rstrip('0').rstrip('.')
    node.set(attr, new_value_str)
    return


def XML_Multiply_Float_Attribute(node, attr, multiplier, precision = 4):
    '''
    Multiplies the given node attribute's value by the multiplier.
    Value is treated as an float, and converted to a string for storage.

    * precision
      - Int, can set the number of decimal places, or None for unlimited.
      - Defaults to 4.
    '''
    XML_Modify_Float_Attribute(node, attr, multiplier, '*', precision)




###############################################################################
# Binary patching support, brought over from X3 Customizer.
# Originally this was for obj files, but naming is tweaked for general binary.

class Binary_Patch:
    '''
    Patch to apply to a binary file.

    Attributes:
    * file
      - String, name of the binary file being edited.
    * ref_code
      - String, the code starting at the offset which is being replaced.
      - Used for verification and for offset searching.
      - Use '.' for any wildcard match.
      - Spaces allowed for visual alignment; ignored during parsing.
      - Will be converted to a regex pattern, though the string should
        not be formatted as a regex pattern.
    * new_code
      - Byte string, the replacement code.
      - Length of this doesn't need to match ref_code.
      - Replacements will be on a 1:1 basis with existing bytes, starting
        at a matched offset and continuing until the end of the new_code.
      - Overall binary code will remain the same length.
      - Spaces allowed, as with ref_code.
      - Also supports byte deletions and insertions, to aid in moving
        code sections.  A '-' removes 1 byte, a '+' inserts one byte
        with a default 0 value.  Replacements continue after deletions
        points, and overwrite insertion points, eg. '++0607' will insert
        two bytes of values '0607'. The number of '-' and '+' must
        always match.
    * expected_matches
      - Int, number of places in code a match should be found.
      - Normally 1, but may be more in some cases of repeated code that
        should all be patched the same way.
    '''
    def __init__(self, file, ref_code, new_code, expected_matches = 1):
        self.file = file
        # Prune off spacing, newlines.
        self.ref_code = ref_code.replace(' ','').replace('\n','')
        self.new_code = new_code.replace(' ','').replace('\n','')
        self.expected_matches = expected_matches


def _String_To_Bytes(string, add_escapes = False):
    '''
    Converts the given string into bytes.
    Strings should either be hex representations (2 characters at a time)
    or wildcards given as '.' (also in pairs, where .. matches a single
    wildcard byte). Byte values that match special regex control
    chars will be escaped.

    * add_escapes
      - Bool, if True then re.escape will be called on the non-wildcard
        entries.
      - This should be applied if the bytes will be used as a regex pattern.
    '''
    # Replace the spaces.
    # To make striding more convenient, double all + and - so that they take
    #  up 2 chars each.
    string = string.replace('-','--').replace('+','++')

    # Make sure the input is even length, since hex conversions
    #  require 2 chars at a time (to make up a full byte).
    assert len(string) % 2 == 0

    new_bytes = b''

    # Loop over the pairs, using even indices.
    for even_index in range(0, len(string), 2):
        char_pair = string[even_index : even_index + 2]
        
        # Special chars will be handled directly.
        if char_pair == '..':
            # Encode as a single '.' so this matches one byte.
            new_bytes += str.encode('.')
        # Everything else should be strings representing hex values.
        else:
            this_byte = hex2bin(char_pair)
            # Note: for low values, this tends to produce a special
            #  string in the form '\x##', but for values that can map
            #  to normal characters, it uses that character instead.
            # However, that character could also be a special regex
            #  character, and hence direct mapping is not safe.
            # As a workaround, aim to always put an escape character
            #  prior to the encoded byte; however, this requires that
            #  the escape be a byte also (a normal python escape will
            #  escape the / in /x## and blows up). Hopefully regex
            #  will unpack the byte escape and work fine.
            # Use re.escape for this, since trying to do it manually
            #  is way too much effort (get 'bad escape' style errors
            #  easily).
            # Note: re.escape does something weird with \x00, converting
            #  it to \\000, but this appears to be okay in practice.
            if add_escapes:
                this_byte = re.escape(this_byte)
            new_bytes += this_byte

    return new_bytes


def Int_To_Hex_String(value, byte_count, byteorder = 'big'):
    '''
    Converts an int into a hex string, with the given byte_count
    for encoding. Always uses big endian.
    Eg. Int_To_Hex_String(62, 2) -> '003e'

    * byteorder
      - String, either 'big' or 'little', where 'big' puts the MSB first,
        little puts the MSB last.
    '''
    # Get the highest amount represented by this byte count, plus 1.
    max_plus_1 = 1 << (byte_count*8)

    # If a negative value given, treat as wanting negative signed hex.
    # Python doesn't handle this well, so convert manually.
    if value < 0:
        # Example: given -1, 1 byte, so 256 - 1 = 255.
        value = max_plus_1 + value
        
    # Size check.
    if value > max_plus_1:
        raise Exception(f"value {value} does not fit in {byte_count} bytes")

    # Convert this into a byte string, hex, then back to string.
    # Always big endian.
    # Kinda messy: need to encode the int to bytes, then go from the
    #  byte string to a hex string, then decode that back to unicode.
    return bin2hex(value.to_bytes(byte_count, byteorder = byteorder)).decode()
    

def _Get_Matches(patch):
    '''
    Find locations in the binary code where a patch can be applied.
    Returns a list of re match objects.

    This will search for the ref_code, using regex, and applies
    the patch where a match is found.
    Error if the number of matches is not what the patch expects, or if
    the match location doesn't match the reference code.
    '''
    file_contents = File_Manager.Load_File(patch.file)

    # Get a match pattern from the ref_code, using a bytes pattern.
    # This needs to convert the given ref_code into a suitable
    #  regex pattern that will match bytes.
    ref_bytes = _String_To_Bytes(patch.ref_code, add_escapes = True)
    pattern = re.compile(
        ref_bytes,
        # Need to set . to match newline, just in case a newline character
        #  is in the wildcard region (which came up for hired TLs).
        flags = re.DOTALL)

    # Get all match points.
    # Need to use finditer for this, as it is the only one that will
    #  return multiple matches.
    # Note: does not capture overlapped matches; this is not expected
    #  to be a problem.
    matches = [x for x in re.finditer(
        pattern, 
        file_contents.binary
        )]
    
    # Look up the calling transform's name for any debug printout.
    try:
        caller_name = inspect.stack()[1][3]
    except:
        caller_name = '?'

    # Do the error check if a non-expected number of matches found.
    if len(matches) != patch.expected_matches:
        # Can raise a hard or soft error depending on mode.
        # Message will be customized based on error type.
        if Settings.developer:
            Print('Error: Binary patch reference code found {} matches,'
                 ' expected {}, in {}.'.format(
                     len(matches),
                     patch.expected_matches,
                     caller_name,
                     ))
            Print('Pattern in use:')
            Print(pattern)
        else:
            raise Binary_Patch_Exception()
        return
    

    # Loop over the matches to check each of them.
    for match in matches:

        # Grab the offset of the match.
        offset = match.start()
        #print(hex(offset))

        # Get the wildcard char, as an int (since the loop below unpacks
        #  the byte string into ints automatically, and also pulls ints
        #  from the original binary).
        wildcard = str.encode('.')[0]

        # Quick verification of the ref_code, to ensure re was used correctly.
        # This will not add escapes, since they confuse the values.
        for index, ref_byte in enumerate(_String_To_Bytes(patch.ref_code)):

            # Don't check wildcards.
            if ref_byte == wildcard:
                continue

            # Check mismatch.
            # This exists as a redundant verification added during
            #  code development to make sure the regex match location was
            #  correct.
            original_byte = file_contents.binary[offset + index]
            if ref_byte != original_byte:
                if Settings.developer:
                    Print('Error: Binary patch regex verification mismatch')
                    return
                else:
                    raise Binary_Patch_Exception()

    return matches


def Apply_Binary_Patch(patch):
    'Applies a single patch. Redirects to Apply_Binary_Patch_Group.'
    Apply_Binary_Patch_Group([patch])


def Apply_Binary_Patch_Group(patch_list):
    '''
    Applies a group of patches as a single unit.
    If any patch runs into an error, no patch in the group will be applied.
    '''
    # Start with a search for matches.
    # These calls may raise an exception on error, or could return None
    #  in dev mode.
    matches_list = []
    for patch in patch_list:
        matches_list.append(_Get_Matches(patch))

    # Return early on a None was returned.
    if None in matches_list:

        # Get the indices of the patches that had errors or no errors.
        correct_patches = []
        failed_patches  = []
        for index, matches in enumerate(matches_list):
            if matches == None:
                failed_patches.append(index)
            else:
                correct_patches.append(index)

        # Print them.
        if Settings.developer:
            Print('Correct patches : {}.'.format(
                     correct_patches ))
            Print('Failed patches  : {}.'.format(
                     failed_patches ))
        return


    # It should now be safe to apply all patches in the group.
    file_contents = File_Manager.Load_File(patch.file)
    file_contents.Set_Modified()

    for patch, matches in zip(patch_list, matches_list):

        # Loop over the matches to apply each of them.
        for match in matches:

            # Grab the offset of the match.
            offset = match.start()

            # Verify there are a matched number of insertions and
            #  deletions in the new_code.
            if patch.new_code.count('+') != patch.new_code.count('-'):
                raise Exception('Error: Binary patch changes code size.')
                        
            #-Removed; old style before insert/delete characters were
            #  added in. Was this unsafe on the wildcards anyway, which
            #  could take the same value as normal bytes? May have just
            #  gotten lucky that this case didn't come up.
            ## Get the wildcard char, as an int (since the loop below unpacks
            ##  the byte string into ints automatically, and also pulls ints
            ##  from the original binary).
            #wildcard = str.encode('.')[0]
            ## Apply the patch, leaving wildcard entries unchanged.
            ## This will edit in place on the bytearray.
            #new_bytes = _String_To_Bytes(patch.new_code)
            #for index, new_byte in enumerate(new_bytes):
            #    if new_byte == wildcard:
            #        continue
            #    file_contents.binary[offset + index] = new_byte

            # Stride through the new code.
            # For convenience, this will work on char pairs (for byte
            #  conversion when needed), and so a pre-pass will duplicate
            #  all control characters (+-) accordingly. '.' is not
            #  duplicated since it is already doubled in the original
            #  string.
            new_code = patch.new_code
            for control_char in ['+','-']:
                new_code = new_code.replace(control_char, control_char*2)

            # Note the code length before starting, for error check later.
            start_length = len(file_contents.binary)

            # Loop over the pairs, using even indices.
            for even_index in range(0, len(new_code), 2):
                char_pair = new_code[even_index : even_index + 2]
                
                # If this is a wildcard, advance the offset with no change.
                if char_pair == '..':
                    offset += 1

                # If this is a deletion, remove the byte from the 
                #  file_contents and do not advance the offset (which will
                #  then be pointing at the post-deletion byte automatically).
                elif char_pair == '--':
                    file_contents.binary.pop(offset)
                    
                # If this is an addition, insert a 0.
                elif char_pair == '++':
                    file_contents.binary.insert(offset, 0)

                else:
                    # This is a replacement byte.
                    # Convert it, insert, and inc the offset.
                    # Note: bytearray requires an int version of this value,
                    #  and hex2bin returns a byte string version.
                    #  Indexing into a bytearray of byte strings
                    #  returns an int, not a string.
                    new_byte = hex2bin(char_pair)[0]
                    file_contents.binary[offset] = new_byte
                    offset += 1

            # Error check.
            assert len(file_contents.binary) == start_length
    return

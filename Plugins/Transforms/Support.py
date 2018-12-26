'''
Various shared support functions for the transforms.
'''

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


def XML_Multiply_Float_Attribute(node, attr, multiplier):
    '''
    Multiplies the given node attribute's value by the multiplier.
    Value is treated as an float, and stored with up to 2 decimal
    places.
    '''
    value = float(node.get(attr))
    # Multiply.
    new_value = value * multiplier
    # Limit string precision to a couple decimals.
    # For the sake of printouts, trim off trailing 0s; kinda ugly
    #  to do this in python, sadly.
    new_value_str = '{:.2f}'.format(new_value).rstrip('0').rstrip('.')
    node.set(attr, new_value_str)
    return
'''
Weapon transforms.
'''

# Fill in the default documentation category for the transforms.
# Use a dict copy, since this adds new locals.
for _attr_name, _attr in dict(locals()).items():
    if hasattr(_attr, '_category'):
        _attr._category = 'Weapons'
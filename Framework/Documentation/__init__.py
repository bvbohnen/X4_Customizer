'''
Support for documentation generation, both high level for general
users and low level for developers.
'''
from .Sphinx_Doc_Gen import Make_Sphinx_Doc
from .Sphinx_Doc_Gen import Doc_Category, Doc_Category_Default

__all__ = [
    'Make_Sphinx_Doc',
    'Doc_Category',
    'Doc_Category_Default',
    ]
'''
Generate documentation for a python package, currently aiming at
using Sphinx to generate html.

The package should be annotated using Doc_Category_Default, and Doc_Category,
to classify modules or individual functions and classes with their
documentation category. Uncategorized objects will be skipped.
'''
#from typing import Dict, List, Object, Tuple, Type
from types import ModuleType, FunctionType
from pathlib import Path
this_dir = Path(__file__).resolve().parent

# Note: only modules or classes/functions annotated with a doc category
# will be included in the generated docs.
def Doc_Category(category : str = None):
    '''
    Function and class decorator, allow specification of a
    documentation category it belongs to. This overrides any
    module level default.
    '''

    # Make the inner decorator function, capturing the wrapped
    #  function or class.
    def inner_decorator(func_or_class):

        # Attach the override category to the callable.
        func_or_class._doc_category = category
        
        # Return the callable.
        return func_or_class

    # Return the decorator.
    return inner_decorator


class Doc_Category_Default:
    '''
    Sets the default category for a module.
    One of these should be instantiated within the module in global
    scope, given any convenient name beginning with an underscore
    (to avoid it getting imported into other modules accidentally).
     
    Example:
        from .Sphinx_Doc_Gen import Doc_Category_Default
        _doc_category = Doc_Category_Default('Transforms')
    '''
    def __init__(self, category : str):
        assert isinstance(category, str)
        self.category = category
                
# Support documenting this doc gen package.
_doc_category = Doc_Category_Default('Documentation')

import os
import sys
import inspect
import importlib
from collections import defaultdict

def Make_Sphinx_Doc(
        start_folder : Path,
        extra_folders : list[Path] = None,
        work_folder : Path   = None,
        output_folder : Path = None,
        include_search : bool = False,
        title : str = None,
        copyright : str = None,
        version : str = None,
    ):
    '''
    Generate documentation for all python packages within a given folder,
    including any subpackages.

    * start_folder
      - Path, path from the working directory to the folder holding
        the package to create documentation for.
    * extra_folders
      - List of Paths, optional, for any extra packages to include in the
        documentation. All extras should share the same parent folder
        as the start_folder.
    * work_folder
      - Path, path to a folder to place temporary files in, such as
        any generated or copied sphinx input files.
      - Optional; default is to place the files in a 'sphinx' folder
        underneath the current working directory.
      - Must be a folder underneath the start_folder for now, since the
        sphinx relative path is set to 2 folders up for imports.
      - Due to sphinx bugs, this cannot have spaces in the path.
      - Any .rst files in the work folder will be deleted prior to new
        ones being generated.
      - Currently, such files are not deleted when done, to preserve them
        for debug purposes.
    * output_folder
      - Path, path to where the generated documentation should be
        written.
      - Optional; default is to place it in 'documentation' under the
        start_folder, with an additional nested folder for the documentation
        type,  eg. 'html' by default.
      - Due to sphinx bugs, this cannot have spaces in the path.
    * include_search
      - Bool, if True a search bar will be added to the html.
      - The searchindex file generated is rather large and clutters git,
        so the search bar will generally be left disabled for the html
        copy in the repository.
    * title
      - String, high level title of the documentation.
    * copyright
      - String, copyright to add to the documentation.
    * version
      - String, version of the documentation.
    '''
    # Return early if sphinx not found.
    try:
        from sphinx.cmd.build import main as sphinx_main
    except ImportError:
        # TODO: maybe an error message.
        return

    # Set default work and output folders.
    if work_folder == None:
        work_folder = start_folder / 'sphinx'
    if output_folder == None:
        output_folder = start_folder / 'documentation'

    # If the work or output folders don't exist, make them.
    if not work_folder.exists():
        work_folder.mkdir(parents=True)
    if not output_folder.exists():
        output_folder.mkdir(parents=True)

    # Isolate the name of the main package being documented.
    package_name = start_folder.name
    
    # Fill some default fields.
    if extra_folders is None:
        extra_folders = []
    if title is None:
        title = f'{package_name} Documentation'
    if copyright is None:
        copyright = ''
    if version is None:
        version = ''
    
    '''
    The included auto-setup for autodoc in sphinx will place all modules in
    a package onto the same html page, with headers on a per-module basis.
    The goal here is to do something more custom, where each module will
    be its own page, and headers are provided for major classes and functions
    within a module.

    Sphinx works on nested .rst files, which are written in its custom
    restructuredtext markup format.
    A special 'toctree' directive will define child rst files underneath
    the current file.
    Each rst file will generate its own html page.

    The approach here will be to:
        1)  Scan through the package for modules.
        2)  Create an rst for the module.
        3)  Scan the module for classes/functions of interest.
        4)  Add to the rst headers and autodoc calls to insert the docstrings
            for these items.
        5)  Collect all generated module rst files, and add them to a top
            level rst's toc tree.
        6)  Place high level summary info (docstring from __init__) into
            the top level rst.
    '''

    # Find all modules in the directory, and sub directories for
    #  package children.
    module_dict = Get_Modules(start_folder, extra_folders)
    
    # Module contents should be annotated with documentation categories,
    #  which allows doc pages to be set independent of module file
    #  organization.
    # Categorize the functions and classes here, skipping everything
    #  that does not have a category set.
    categorized_objects_dict = Categorize_Module_Contents(module_dict)

    # Clean out old rst files; this should be safe.
    for dir_path, folder_names, file_names in os.walk(work_folder):
        dir_path = Path(dir_path)
        for file_name in file_names:
            # Skip non-rst files.
            if not file_name.endswith('rst'):
                continue
            file_path = dir_path/file_name
            if file_path.exists():
                file_path.unlink()
        # Don't continue to subdirectories, if any.
        break

    # Note:
    # Setting sticky sidebar (in conf.py) will break the sidebar into its own
    # pane with scroll bar, but has an issue with the footer, which stretches
    # across both panes, being placed according to the text section bottom,
    # which will interrupt the sidebar if the text pane is shorter than
    # the sidebar itself.
    # The only found fix for this is just to pad out short modules to be
    # as long as the sidebar, using the '|' character on such lines to
    # prevent their removal.
    # (This will still have overlap problems if scrolled all the way down,
    # but removes the need to scroll all the way down.)
    # Actual sidebar length seems to vary, with the text size even changing
    # depending on page (for some reason), plus it expands based on how
    # many items are in a given module.
    # Determine a base length here, and let the module pad it out based
    # on member count.
    # Base is the category count, plus some extra to cover the header.
    sidebar_base_length = len(categorized_objects_dict) + 10

    # Loop over the categories to make their files.
    # TODO: given an option to join all categories in a single file.
    for category, subdict in categorized_objects_dict.items():

        # Get the rst lines.
        rst_lines = Get_Sphinx_Category_Lines(
            category, subdict, sidebar_base_length)

        # Select the file name.
        # This needs to match up with whatever is inside the index file's
        # toc tree.
        # Stick the package path with the module name.
        file_name = category + '.rst'

        with open(work_folder / file_name,'w') as file:
            file.write('\n'.join(rst_lines))

                
    # Get the index file rst.
    rst_lines = Get_Sphinx_Index_Lines(
        package_name, module_dict, categorized_objects_dict, include_search )
    with open(work_folder / 'index.rst','w') as file:
        file.write('\n'.join(rst_lines))


    # With all rst files generated, the only thing left of concern
    #  is the conf.py file.
    # Create the setup file, a python file sphinx will import.
    setup_lines = Get_Sphinx_Config_Lines(
        package_name, 
        start_folder, 
        include_search,
        title = title,
        copyright = copyright,
        version = version)
    # This has to be named 'conf.py'.
    with open(work_folder / 'conf.py','w') as file:
        file.write('\n'.join(setup_lines))
            
    # Call sphinx to build everything.
    # Note: using the sphinx main function with args parsing instead of
    # creating a Sphinx object directly, to make use of convenient arg
    # defaults (which the Sphinx class lacks).    

    try:
        sphinx_main([
            '-M',
            # Type of build to do.
            # TODO: make a parameter of the make_documentation call.
            # For now, just basic html.
            'html',
            # Source and dest folders.
            # Note: sphinx appends this path to the working directory,
            #  so these need to be made relative if they are not already.
            # Note: spaces in folder names may be unsupported, since sphinx
            #  appears to string append instead of a path join, and spaced
            #  names need quotes on the command line, which ends up with
            #  quotes in the middle of the full path. TODO: a workaround for
            #  this if needed.
            # Using os relpath to support upward pathing.
            '{}'.format(os.path.relpath(work_folder, '.')),
            '{}'.format(os.path.relpath(output_folder, '.')),

            # Add -E -a to make this recompile files during development, 
            # since sometimes the development method will change (and not
            # the python module), which sphinx doesn't pick up on, causing 
            # it to reuse cached results.
            '-E','-a',
            # Add -N to decolor the output, eg. avoid deep red on black 
            # for warnings.
            '-N',
            ])
    except Exception as ex:
        print(f'sphinx build failed with error: {ex}')
        
    return



'''
Note on sections/subsections/etc.:

    The autogenerated sidebar will tier out the sections and subsections,
    which are implied by the use of section underlines, with the outermost
    underline character being the main section, and so on.

    Documentation suggests this order of characters:

    "
        # with overline, for parts
        * with overline, for chapters
        =, for sections
        -, for subsections
        ^, for subsubsections
        ", for paragraphs
    "

    For the moment, this code will just do sections and below.
    
'''

def Get_Modules(
        main_directory : Path, 
        extra_folders : list[Path]
        ) -> dict[str,dict[str,ModuleType]]:
    '''
    Returns a dict of imported modules in packages in the
    target directory.  Key is package path in the python
    style, eg. 'package' or 'package.subpackage', while the value
    is a subdict keyed by module name, holding the imported
    module object.
    '''
    module_dict = defaultdict(dict)
    # Isolate the path to the package folder.
    containing_folder = main_directory.parent

    # Ensure the containing_folder is in the sys search path, so that
    #  the package will be found on import.
    if containing_folder not in sys.path:
        sys.path.append(containing_folder)
        
    # Collect a list of package folders to pull from.
    pkg_folders = [main_directory] + extra_folders
    # Verify all packages share the same containing folder.
    assert all(x.parent == containing_folder for x in pkg_folders)

    # Walk through the target dir, as well as child dirs.
    # Note: this may include any sphinx subfolders and such, so those
    #  should be skipped (eg. by an __init__ check).
    for directory in pkg_folders:
        # TODO: maybe swap to main_directory.walk for python 3.12.
        for dir_path, dir_names, file_names in os.walk(directory):
            dir_path = Path(dir_path)
        
            # Verify the top directory is a package, which is a basic
            #  code assumption.
            if dir_path == main_directory and '__init__.py' not in file_names:
                raise Exception('The target folder does not have a python package')

            # Skip directories without an __init__ file, so that this
            #  only touches packages.
            if '__init__.py' not in file_names:
                continue
        
            # Handle files at this level.
            for file_name in file_names:

                # Skip non-py files.
                if not file_name.endswith('.py'):
                    continue

                # Import it.
                # Using this style of import, provide the python style of
                # module name, eg. with no .py, and add the package path in
                # the python style (dots between package levels).
                # Note: relpath takes the base directory as second arg.
                # A direct relpath from the main_directory when already in that
                # directory will return '.', which is awkward to work around if
                # it potentially varies across systems.
                # To get the package path: discard the containing_folder portion,
                # which should always leave at least the package folder, plus
                # and subpackage path.
                offset_path = dir_path.relative_to(containing_folder)

                # Convert the offset_path to a python style module import path,
                # eg. with '.' to separate package levels.
                package = '.'.join([str(x) for x in offset_path.parts])
                module_name = file_name.replace('.py','')

                # Importlib requires a package to already be imported
                # before importing modules from it.
                # If these fail, skip.
                try:
                    importlib.import_module(package)
                    module = importlib.import_module('.' + module_name,
                                                     package = package)
                    # Store it.
                    module_dict[package][module_name] = module
                except (ModuleNotFoundError, ImportError) as ex:
                    print(f'Skipping documentation "{package}.{module_name}"'
                          +f'due to import error {ex}')

    return module_dict


def Categorize_Module_Contents(
        module_dict : dict[str,dict[str,ModuleType]]
        ) -> dict[str,dict[str,list[tuple[str,object,Path]]]]:
    '''
    Pulls functions and classes from a group of modules, and categorizes
     them according to annotation strings.
    Returns a dict, keyed by category strings, holding a subdict
     keyed by 'function' or 'class', holding a list of tuples of
     (object name, object, module_path) holding the matching objects
     sorted by name and with the path to their module file as a
     python style path string.
    '''
    # Set the overall dict of dicts of lists structure.
    # Empty entries (eg. when a category has no functions) will still
    #  have a list present, for easier coding elsewhere.
    categorized_objects_dict = defaultdict(
        lambda: {'classes':[],'functions':[]})

    for package_path, subdict in module_dict.items():
        for module_name, module in subdict.items():
            
            # Get the path to the module.
            module_path = package_path + '.' + module_name

            # Get the default category, skipping the module if none
            #  found. This is set as a global Doc_Category_Default
            #  object at the module level.
            # TODO: find alternative to this that doesn't get confused
            #  by modules importing other modules with defaults set.
            default_category = None
            for name in dir(module):
                object = getattr(module, name)
                if isinstance(object, Doc_Category_Default):
                    default_category = object.category
            
            # Collect all loose functions.
            # These are tuples of (name, function).
            function_tuples = Get_Module_Functions(module)
            # Collect all classes.
            class_tuples = Get_Module_Classes(module)
            
            # Loop over these groups to collect into categories.
            for func_or_class, object_tuples in zip(
                ['functions','classes'],
                [function_tuples, class_tuples],
                ):
                for object_name, object in object_tuples:

                    # Check if this has an override category, else use
                    #  the default.
                    this_cat = getattr(object, '_doc_category', default_category)
                    # If no category found (from the object or the default),
                    #  skip this.
                    if not this_cat:
                        continue

                    # Store it.
                    categorized_objects_dict[this_cat][func_or_class].append(
                        (object_name, object, module_path))

    # With everything gathered, can now sort by name.
    for cat, subdict in categorized_objects_dict.items():
        for func_or_class, sublist in subdict.items():
            # Only use the name to sort; tiebreakers shouldn't fall back
            #  on the function/class objects, which cannot be sorted.
            subdict[func_or_class] = sorted(sublist, key = lambda x : x[0])

    return categorized_objects_dict



def Get_Module_Classes(module : ModuleType) -> list[tuple[str,type]]:
    '''
    Returns a list of (name, class) tuples for a module.
    This will skip any classes imported into the module.
    '''
    # Inspect's getmembers, filtered by isclass, will get all classes,
    #  including imports. Filter again by the __module__ field, which
    #  should match the input module.
    # Note: there may be an issue with __module__ and package paths,
    #  but don't worry about it unless there is a problem with
    #  some classes not getting documented.
    ret_list = [x for x in inspect.getmembers(
        module, 
        predicate = inspect.isclass)
        if x[1].__module__ == module.__name__
        ]
    return ret_list


def Get_Module_Functions(module : ModuleType) -> list[tuple[str,FunctionType]]:
    '''
    Returns a list of (name, function) tuples for a module.
    This will skip any functions imported into the module.
    '''
    # As above, but filtering by isfunction.
    ret_list = [x for x in inspect.getmembers(
        module, 
        predicate = inspect.isfunction)
        if x[1].__module__ == module.__name__
        ]
    return ret_list


def Get_Sphinx_Index_Lines(
    package_name : str,
    module_dict : dict[str,dict[str,ModuleType]], 
    categorized_objects_dict : dict[str,dict[str,list[tuple[str,object,Path]]]],
    include_search : bool
    ) -> list[str]:
    '''
    Returns a list of strings, lines for the main index.rst file that
    acts as the top level of any html.
    '''

    #-Removed; switching to categories instead of modules.
    # This will have the toctree with a list of names of child rst files
    #  (without rst extension) that have the different category docs.
    ## Child files will have their module path included, in full.
    #module_file_names = []
    #for package_path, subdict in module_dict.items():
    #    for module_name, module in subdict.items():
    #        # Skip init files.
    #        if module_name == '__init__':
    #            continue
    #        # Stick the package path with the module name.
    #        module_file_names.append( package_path + '.' +module_name )
    #
    ## Put the names in alphabetical order.
    #module_file_names = sorted(module_file_names)

    # Sort the category names.
    category_names = sorted(categorized_objects_dict.keys())

    # This will grab the top level init for summary info, and print some
    #  common items from the examples viewed.
    line_list = [        
        '{} Documentation'.format(package_name),
        '==========================================',
        '',
        'Indices and tables',
        '------------------',
        '',
        '* :ref:`genindex`',
        '* :ref:`modindex`',
        '* :ref:`search`' if include_search else '',
        '',
        # High level description will come from the init file of the
        # main package, using autodoc's module loader.
        # Assume the main package has the start folder name.
        'Project Description',
        '-------------------',
        '',
        '.. automodule:: {}'.format(package_name),
        '    :members:                  ',
        '    :undoc-members:            ',
        '    :show-inheritance:         ',
        '',

        # TODO: maybe link out submodules here, but can probably rely
        # on the automated menu and index page instead.
        #'Submodules',
        #'----------',
        #'',

        # Put the toctree at the end, since it is mostly fluff.
        '.. toctree::',
        # Set how many layers of depth it goes down, in term of sections,
        #  subsections, etc.
        # Set to 3 to dig down to modules, function/class category, and
        #   individualfunctions/classes.
        '   :maxdepth: 3',
        '   :caption: Content:',
        # Hide the link list.
        # Note: this also omits the toctree from the sidebar (though the
        #  documentation indicates otherwise), so the ugly list of
        #  pages needs to be left in for now.
        # Possible solution at:
        #  https://stackoverflow.com/questions/17194400/sphinx-toctree-either-displays-a-toc-in-sidebar-with-bulleted-list-in-body-or-n
        #'   :hidden:',
        # Toctree needs an extra newline before listing
        # out child rst files.
        '',
        # Splat out the module names, with indentation.
        *['   '+x for x in category_names],
        '',

        # TODO:
        # Include a separate toctree for subpackages, maybe.
        # This can just be placed before/after the main one, given a
        #  different caption, and it will show up on the sidebar.
        # For now, subpackages just get placed with everything else,
        #  having their subpackage name as prefix.
        ]

    return line_list


def Get_Sphinx_Category_Lines(
    category : str, 
    subcategory_dict : dict[str,list[tuple[str,object,Path]]],
    sidebar_base_length : int
    ) -> list[str]:
    '''
    Returns a list of strings, lines for a module's rst file.
    This will insert any wanted class and function headers, skip
    unwanted items, etc.
    '''

    # Start with the main title.
    # This section title gets used in the sidebar, so keep it short.
    # Note: autodoc's rst file generator escapes all underscores, but
    #  in practice that does not appear to be needed, so do nothing
    #  special with them here.
    title = '{}'.format(category)
    line_list = [
        title,
        # The markup for a title requires some repeated characters of
        #  the same length as the title.
        # Use '=' for a major section.
        '=' * len(title),
        '',
        ]

    # Give the top level module description.
    # When not providing options, this will not include module members.
    #-Removed for now; only classes/functions documented, and modules
    # are ignored. TODO: category descriptions.
    #line_list += [
    #    '.. automodule:: {}'.format(full_path),
    #    '',
    #    ]
    
    # Handle functions first.
    if subcategory_dict['functions']:
        line_list += [
            'Functions',
            # Use '-' for a minor section.
            '---------',
            '',
            ]
        # Handle individual functions.
        for function_name, _, module_path in subcategory_dict['functions']:
            # Put a subsection indicator here, so the functions expand
            # in the sidebar.
            title = '{} function'.format(function_name)
            line_list += [
                title,
                # Use '^' for subsubsection.
                '^'*len(title),
                '',

                # Add no extra options to this; none apply.
                # Autofunction needs the path to the module, and the
                #  function inside it.
                '.. autofunction:: {}.{}'.format(module_path, function_name),
                '',
                ]

    # Handle classes similarly.
    # Do not combine code, since classes have significant differences
    #  in the autodoc command.
    if subcategory_dict['classes']:
        line_list += [
            'Classes',
            # Use '-' for a minor section.
            '---------',
            '',
            ]
        for class_name, _, module_path in subcategory_dict['classes']:
            title = '{} class'.format(class_name)
            line_list += [
                title,
                '^'*len(title),
                '',
                '.. autoclass:: {}.{}'.format(module_path, class_name),
                # Give options to include class methods, with and without
                # docstrings.
                '    :members:',
                '    :undoc-members:',
                # Show the class inheritance path.
                '    :show-inheritance:',
                # Private members are those with underscores.
                # TODO: include in developer documentation only, if at all.
                #'    :private-members:',
                # Special members are those with double underscores.
                # Set this only for __init__ for now, so that initializers
                #  can have their arg list printed (with any documentation
                #  on the args).
                # -Removed; the init call args are included in the class
                #  definition line, so this is redundant as long as any
                #  special parameters are explained in the class docstring.
                #'    :special-members: __init__',
                # Maybe add inherited methods, hopefully only limiting to those
                #  from project classes, and not from python base classes.
                # TODO: test this.
                #'    :inherited-members:',
                '',
                ]

    # Pad out the file with extra space until the expected sidebar length
    #  is reached, due to problems with the footer.
    # Can calculate this from the sidebar base length, plus the number
    #  of functions and classes here.
    pad_length = (sidebar_base_length 
                  + len(subcategory_dict['functions']) 
                  + len(subcategory_dict['classes']))

    # Note: it is unknown just how long the text will be once autodoc
    #  expand it out, since it depends on the source object doc strings.
    # A rough estimate could be made (summing up docstring lines), though
    #  even that would be innaccurate to how the text appears after formatting
    #  is applied, and gathering class methods is bothersome.
    # For now, ere on the side of too much padding, and always pad out fully.
    # Use the vertical bar '|' to get a line that will not be combined with
    #  prior lines.
    line_list += ['|' for x in range(pad_length)]

    return line_list


def Get_Sphinx_Config_Lines(
        package_name : str,
        start_folder : Path,
        include_search : bool,
        title : str,
        copyright : str,
        version : str,
    ) -> list[str]:
    '''
    Returns a list of lines holding python code which sphinx will run
    on startup, configuring its options. This includes adding any
    neccessary inclusion paths.
    '''
    lines = [

        # See http://www.sphinx-doc.org/en/stable/config.html for extra details.

        # Get the import path for this package, as well as for the doc package
        #  so its extension is found.
        'from pathlib import Path',
        'import sys',
        # Level above the package, so the package is found.
        # Note: make these raw strings, since the path will have slashes in it
        #  which confuses the python path (which causes a silent error
        #  the way sphinx runs it).
        f"sys.path.insert(0, r'{start_folder.parent}')",
        # Level above this doc package.
        f"sys.path.insert(0, r'{this_dir.parent}')",
        
        # Extensions.
        "extensions = [",
        "'sphinx.ext.autodoc',", 
        "'Framework.Documentation.Sphinx_Doc_Gen'",
        "]",

        # Source file suffixes.
        "source_suffix = ['.rst']",

        # The main doc level.
        "master_doc = 'index'",

        # Header info. TODO: Is this needed?
        f"project = '{title}'",
        f"copyright = '{copyright}'",
        #f"author = '{author}'",

        # Version stuff.  Fill in whatever for now, though could potentially
        #  read from a package if knowing where it is found.
        f"version = '{version}'",
        "release = ''",
        
        # html theme to use.
        # Alabaster is default, but the font is all italics and hard to read;
        #  classic works better, and has an option for a separate sidebar
        #  area.
        #html_theme = 'alabaster'
        "html_theme = 'classic'",

        # Options for the theme.
        "html_theme_options = {",

        # Setting sticky sidebar will break the sidebar into its own pane with
        #  scroll bar, but has an issue with the footer, which stretches across
        #  both panes, being placed according to the text section bottom,
        #  which will interrupt the sidebar if the text pane is shorter than
        #  the sidebar itself.
        # This is fixed in the python setup, by padding out short files.
        "'stickysidebar' : 'true',",

        # Default 230 pixel sidebar is generally not wide enough.
        # TODO: maybe refine this, based on category name length.
        # Update: sphinx 1.7.9 (or maybe earlier) broke support for
        # giving an expression here, so precompute the value.
        # Also, this must be given as an integer, not a float, else
        # the sidebar breaks (maybe related to the precompute issue).
        f"'sidebarwidth'  : {int(230 * 1.5)},",
        "}",

        # Set the menu to use the global tree and not local (which greatly
        #  limits usefulness).
        # Also keep the searchbox for fun.
        "html_sidebars = {",
           "'**': [",
               "'globaltoc.html', ",
               "'searchbox.html', " if include_search else '',
           "],",
        "}",
        # Blank line, else sphinx claims a syntax error on import.
        '',
    ]

    return lines


'''
Below is an extension for sphinx which will perform some formatting of
doc strings to get them ready to be interpretted as restructuredtext.

Problem:
    Sphinx relies on a custom markup format, restructuredtext, which has many
    aspects aimed at the sphinx api itself, but is also used for basic
    text markup. This language is awkward, notably requiring excessive
    newlines, and is not desirable for writing python docstrings.
    (Eg. don't want a 30-line docstring to stretch to 60 lines just to 
    make sphinx display it nice in html.)
    
Solution:
    Sphinx does have support for user defined transforms, which can be fed
    in as python modules to perform some edits at a stage of the document
    generation.

    This project has example code of a plugin (which calls another package
    for doing a markdown->rest conversion):
    https://github.com/jxltom/sphinx-markdown-extension

    Something similar will be done here. Though to avoid the need to install
    an external package (since a user might be annoyed installing sphinx
    already), only some very simple text edits will be done based on the
    expected markdown characters used in this project.

    For some sphinx api info for creating plugings, see:
    http://www.sphinx-doc.org/en/stable/extdev/appapi.html
    For autodoc specific details:
    http://www.sphinx-doc.org/en/stable/ext/autodoc.html

    For more details on the markup language:
    docutils.sourceforge.net/docs/ref/rst/restructuredtext.html

'''

# Define the "setup" function which sphinx will call directly; it must
# have this name to be found.
def setup(app):
    '''
    Setup function for Sphinx to call, used to attach custom extension code.
    '''
    # Unclear on what the point of the default is, or even the
    # config value at all. Leave in place for now.
    app.add_config_value(
        name = 'custom_doc_preparser', 
        default = '?', 
        rebuild = 'html')

    # Set the transform to call on the given event string occurring,
    # which will be autodoc reading a docstring.
    app.connect(
        event = 'autodoc-process-docstring', 
        callback = Autodoc_Markdown_To_Rest)

    # TODO: maybe also attach to autodoc-skip-member to add some generic
    # matching rules to find which functions/classes/members to skip,
    # if needed.
    return


def Autodoc_Markdown_To_Rest(
    # Note: comments on arg names taken from the sphinx doc page, except
    #  cleaned up a bit.

    # Sphinx application object
    app, 
    # Type of the object which the docstring belongs to (one of "module",
    #  "class", "exception", "function", "method", "attribute").
    what, 
    # Fully qualified name of the object.
    name, 
    # The object itself.
    obj, 
    # The options given to the directive: an object with attributes
    #  inherited_members, undoc_members, show_inheritance and noindex
    #  that are true if the flag option of same name was given to the
    #  auto directive.
    options, 
    # The lines of the docstring, see above.
    lines, 
    ):
    '''
    Convert some limited subset of markdown syntax into restructuredtext syntax
    for python docstrings.
    This will also do some misc formatting to avoid unwanted restructuredtext
    formatting, eg. stopping single space indents from creating large
    post-format indents.
    '''

    '''
    The syntax of interest is for bullet lists, which have a form like:

    * point
      - subpoint
      - subpoint
    * next point

    Newlines need to be inserted before each list, while newlines between
    list items are optional.

    New form (may be a little overkill on newlines):

    * point

      - subpoint

      - subpoint

    * next point

    The easiest way to handle this is to find the bulleted items, prefix
    with a newline, and convert to *, which hopefully handles all cases.
    '''
    # Note: the example package earlier says lines should maybe end
    #  in \r\n, but it is unclear on if that is important for what
    #  is being done here.
    # Leave this note for now in case it becomes important.
    #line_end = '\r\n'
    
    # Start by merging the lines together, as otherwise the habit of using
    #  a single indent to continue paragraphs causes excessive indentation
    #  in the generated output.
    merged_lines = Merge_Lines(lines)
    
    # Get a list of line numbers matching code lines.
    code_line_numbers = Get_Code_Line_Numbers(merged_lines)

    # Make a line list.
    new_lines = []
    print_results = False # Test code.
    for line_number, line in enumerate(merged_lines):

        # Test code.
        if 'PRINT_ME' in line:
            print_results = True

        # Find bullets of any type and prefix with a newline.
        # Don't do this on code lines.
        if not line_number in code_line_numbers:
            if line.strip().startswith('*') or line.strip().startswith('-'):
                new_lines.append('')

        # Add this possibly edited line to the new list.
        new_lines.append(line)

    # Test code.
    if print_results:
        with open('text_in.txt','w') as file:
            file.write('\n'.join(lines))
        with open('text_out.txt','w') as file:
            file.write('\n'.join(new_lines))

    # Clear out the old lines and update with the new ones.
    lines.clear()
    lines.extend(new_lines)

    
def Get_Code_Line_Numbers(line_list):
    '''
    Finds and returns a list of line numbers, for lines which appears
    to be part of code blocks.

    * line_list:
      - List of strings, text lines to parse.
    '''
    line_numbers = []
    # Note if a code block appears active.
    code_block_active = False
    # Note if the code block is from restructuretext style of notation.
    restruct_code_active = False

    for line_number, line in enumerate(line_list):
        # Get rid of indent spacing.
        strip_line = line.strip()

        # If this is a <code> tag, start a code block.
        if strip_line == '<code>':
            code_block_active = True
            
        elif strip_line == '</code>':
            code_block_active = False
            
        # Look for restructuretext's :: marker, though it is
        #  a little clumsy to handle (can end a paragraph, and code
        #  section implicitly runs until a shallower indent than
        #  the line with the ::).
        elif strip_line.endswith('::'):
            code_block_active = True
            restruct_code_active = True
            # Record the indent here, to start searching for it or a
            #  shallower indent to stop the code block.
            code_block_end_indent = len(line) - len(line.lstrip())

        # When a code block is active, record the line number.
        # This does not trigger on the same line that started the
        #  code block, and should omit the line that ends it.
        elif code_block_active:

            # Look for termination of the code block based on indent
            #  getting small enough.
            # Do not consider empty lines, only those with text, for
            #  stopping code blocks.
            if restruct_code_active and strip_line:
                this_indent = len(line) - len(line.lstrip())
                if this_indent <= code_block_end_indent:
                    restruct_code_active = False
                    code_block_active = False
                    
            # If still in the code block, record the line number.
            if code_block_active:
                line_numbers.append(line_number)

    return line_numbers


# Note: the following function copied from the X3_Customizer open source
# project ( MIT license) and modified somewhat for use here.
def Merge_Lines(text_block_or_lines : list[str]|str) -> str:
    '''
    To get a better text file from the python docstrings, with proper
     full lines and wordwrap, do a pass over the text block and
     do some line joins.
    General idea is that two lines can merge if:
    -Both have normal text characters (eg. not '---').
    -Not in a code block (4+ space indent series of lines outside of
     a list).
    -Second line does not start a sublist (starts with -,*,etc.).
    Note: markdown merge rules are more complicated, but this should be
    sufficient for the expected text formats.
    This should not be called on code blocks.
    This will also look for and remove <code></code> tags, a temporary
    way to specify in docstrings sections not to be line merged.
    '''
    # Figure out if lines or raw text were given.
    # The return format will match.
    input_was_list = False
    if isinstance(text_block_or_lines, list):
        input_was_list = True

    # List of lines to merge with previous.
    merge_line_list = []
    # Note if the prior line had text.
    prior_line_had_text = False
    # Note if a code block appears active.
    code_block_active = False
    # Note if the code block is from restructuretext style of notation.
    restruct_code_active = False

    # Convert the input to a list if needed, else use it directly.
    if input_was_list:
        line_list = text_block_or_lines
    else:
        line_list = [x for x in text_block_or_lines.splitlines()]

    # Get a list of line numbers matching code lines.
    code_line_numbers = Get_Code_Line_Numbers(line_list)

    for line_number, line in enumerate(line_list):
        # Get rid of indent spacing.
        strip_line = line.strip()
        merge = True

        # If this is a <code> tag, remove the tag.
        if strip_line == '<code>':
            merge = False
            line_list[line_number] = ''
            strip_line = ''
            
        elif strip_line == '</code>':
            merge = False
            line_list[line_number] = ''
            strip_line = ''
            
        # Look for restructuretext's :: marker.
        elif strip_line.endswith('::'):
            # Can allow this line to merge with previous in general,
            #  though disable it when the :: is alone, since it may not
            #  have matched indent to the prior line.
            if strip_line == '::':
                merge = False

        # When a code block is active, don't merge.
        elif line_number in code_line_numbers:
            merge = False

        # Skip the first line; nothing prior to merge with.
        elif line_number == 0:
            merge = False
        
        # If the line is empty, leave empty.
        elif not strip_line:
            merge = False

        # If the line starts with a sublist character, don't merge.
        # This should also catch horizontal bars and similar.
        elif strip_line[0] in ['*','-','=']:
            merge = False

        # If the prior line didn't have text, don't merge.
        elif not prior_line_had_text:
            merge = False


        # If merging, record the line.
        if merge:
            merge_line_list.append(line_number)

        # Update the prior line status.
        prior_line_had_text = len(strip_line) > 0


    # Second pass will do the merges.
    # This will aim to remove indentation, and replace with a single space.
    # This will delete lines as it goes, requiring the merge_line numbers to be
    #  adjusted by the lines removed prior. This can be captured with an
    #  enumerate effectively.
    for lines_removed, merge_line in enumerate(merge_line_list):

        # Adjust the merge_line based on the current line list.
        this_merge_line = merge_line - lines_removed

        # Get the lines.
        prior_line = line_list[this_merge_line-1]
        this_line = line_list[this_merge_line]

        # Remove spacing at the end of the first, beginning of the second.
        prior_line = prior_line.rstrip()
        this_line = this_line.lstrip()

        # Join and put back.
        line_list[this_merge_line-1] = prior_line + ' ' + this_line

        # Delete the unused line.
        line_list.pop(this_merge_line)
        
    # Return as a raw text block if needed, else as lines.
    if input_was_list:
        return line_list
    else:
        return '\n'.join(line_list)


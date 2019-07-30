from pyflakes.checker import Checker, _MAGIC_GLOBALS, ModuleScope
from pyflakes.messages import ImportStarUsage, ImportStarUsed

# quit and exit are not included in old versions of pyflakes
MAGIC_GLOBALS = set(_MAGIC_GLOBALS).union({'quit', 'exit'})

import sys
import ast
import os
import re
import builtins
from pathlib import Path

def names_to_replace(checker):
    names = []
    for message in checker.messages:
        if isinstance(message, ImportStarUsage):
            name, *modules = message.message_args
            names.append(name)
    return names

def star_imports(checker):
    stars = []
    for message in checker.messages:
        if isinstance(message, ImportStarUsed):
            stars.append(message.message_args[0])
    return stars

def fix_code(file, *, max_line_length=100, verbose=False, quiet=False):
    """
    Return a fixed version of the code in `file`, or raise RuntimeError if it is is not valid Python.

    If verbose=True (default is False), info about every replaced import is
    printed.

    If quiet=True (default is False), no warning messages are printed.
    """
    if not os.path.isfile(file):
        raise RuntimeError(f"{file} is not a file.")

    directory, filename = os.path.split(file)
    with open(file) as f:
        code = f.read()

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise RuntimeError(f"SyntaxError: {e}")

    checker = Checker(tree)

    stars = star_imports(checker)
    names = names_to_replace(checker)

    mod_names = {}
    repls = {i: [] for i in stars}
    for mod in stars:
        mod_names[mod] = get_names_from_dir(mod, directory)
    for name in names:
        mods = [mod for mod in mod_names if name in mod_names[mod]]
        if not mods:
            if not quiet:
                print(f"Warning: {file}: could not find import for '{name}'", file=sys.stderr)
            continue
        if len(mods) > 1:
            if not quiet:
                print(f"Warning: {file}: '{name}' comes from multiple modules: {', '.join(map(repr, mods))}. Using '{mods[-1]}'.",
                  file=sys.stderr)

        repls[mods[-1]].append(name)

    code = replace_imports(code, repls, filename=filename, verbose=verbose, quiet=quiet)

    return code

def replace_imports(code, repls, *, max_line_length=100, filename=None, verbose=False, quiet=False):
    """
    Replace the star imports in code

    repls should be a dictionary mapping module names to a list of names to be
    imported.

    max_line_length (default: 100) is the maximum number of characters for a
    line. Added imports that are longer than this are wrapped.

    If a filename is provided it is only used for the verbose messages.

    If verbose=True (default: True), a message is printed for each import that is replaced.

    If quiet=True (default: False), a warning is printed if no replacements
    are made. The quiet flag does not affect the messages from verbose=True.

    Example:

    >>> code = '''
    ... from mod import *
    ... print(a + b)
    ... '''
    >>> repls = {'mod': ['a', 'b']}
    >>> print(replace_imports(code, repls, verbose=False))
    from mod import a, b
    print(a + b)
    >>> code = '''
    ... from .module.submodule import *
    ... '''
    >>> repls = {'.module.submodule': ['name1', 'name2', 'name3']}
    >>> print(replace_imports(code, repls, max_line_length=40, verbose=False))
    from .module.submodule import (name1, name2,
                                  name3)

    """
    for mod in repls:
        names = sorted(repls[mod])

        STAR_IMPORT = re.compile(rf'from +{re.escape(mod)} +import +\*')
        if not names:
            new_import = ""
        else:
            new_import = f"from {mod} import " + ', '.join(names)
            if len(new_import) - len(names[-1]) > max_line_length:
                lines = []
                line = f"from {mod} import ("
                indent = ' '*len(line)
                for name in names:
                    line += name + ', '
                    if len(line) > max_line_length:
                        lines.append(line.rstrip())
                        line = indent
                lines.append(line[:-2] + ')') # Remove last trailing comma
                new_import = '\n'.join(lines)

        new_code = STAR_IMPORT.sub(new_import, code)
        if new_code == code:
            if not quiet:
                print("Warning: Could not find the star imports for '{mod}'", file=sys.stderr)
        elif verbose:
            msg = f"Replacing 'from {mod} import *' with '{new_import}'"
            if filename:
                msg = f"{filename}: {msg}"
            print(msg)
        code = new_code

    return code

def get_mod_filename(mod, directory):
    """
    Get the filename for `mod` relative to a file in `directory`.
    """
    # TODO: Use the import machinery to do this.
    directory = Path(directory)

    dots = re.compile(r'(\.+)(.*)')
    m = dots.match(mod)
    if m:
        # Relative import
        loc = directory.joinpath(*['..']*(len(m.group(1))-1), *m.group(2).split('.'))
        filename = Path(str(loc) + '.py')
        if not filename.is_file():
            filename = loc/'__init__.py'
        if not filename.is_file():
            raise RuntimeError(f"Could not find the file for the module '{mod}'")
    else:
        top, *rest = mod.split('.')

        # Try to find an absolute import from the same module as the file
        head, tail = directory.parent, directory.name
        while True:
            # If directory is relative assume we
            # don't need to go higher than .
            if tail == top:
                loc = os.path.join(head, tail, *rest)
                if os.path.isfile(loc + '.py'):
                    filename = loc + '.py'
                    break
                elif os.path.isfile(os.path.join(loc, '__init__.py')):
                    filename = os.path.join(loc, '__init__.py')
                    break
            if head in [Path('.'), Path('/')]:
                raise NotImplementedError("Imports from external modules are not yet supported.")
            head, tail = head.parent, head.name

    return filename

def get_names_from_dir(mod, directory):
    filename = get_mod_filename(mod, directory)

    with open(filename) as f:
        code = f.read()

    try:
        return get_names(code)
    except SyntaxError as e:
        raise RuntimeError(f"Could not parse {filename}: {e}")
    except RuntimeError:
        raise RuntimeError(f"Could not parse the names from {filename}")

def get_names(code):
    # TODO: Make the doctests work
    """
    Get a set of defined top-level names from code

    Example:

    >>> get_names('''
    ... import mod
    ... a = 1
    ... def func():
    ...     b = 2
    ... ''') # doctest: +SKIP
    {'a', 'func', 'mod'}

    Star imports in code are returned like

    >>> get_names('''
    ... from .mod1 import *
    ... from module.mod2 import *
    ... ''') # doctest: +SKIP
    {'.mod1.*', 'module.mod2.*'}

    Returns a set of names, or raises SyntaxError if the code is not valid
    syntax.
    """
    tree = ast.parse(code)

    checker = Checker(tree)
    for scope in checker.deadScopes:
        if isinstance(scope, ModuleScope):
            return scope.keys() - set(dir(builtins)) - set(MAGIC_GLOBALS)

    raise RuntimeError(f"Could not parse the names")

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
from functools import lru_cache

def names_to_replace(checker):
    names = set()
    for message in checker.messages:
        if isinstance(message, ImportStarUsage):
            name, *modules = message.message_args
            names.add(name)
    return names

def star_imports(checker):
    stars = []
    for message in checker.messages:
        if isinstance(message, ImportStarUsed):
            stars.append(message.message_args[0])
    return stars

def fix_code(code, *, file, max_line_length=100, verbose=False, quiet=False, allow_dynamic=True):
    """
    Return a fixed version of the code `code` from the file `file`

    Raises RuntimeError if it is is not valid Python.

    See the docstring of replace_imports() for the meaning of the keyword
    arguments to this function.

    If allow_dynamic=True, then external modules will be dynamically imported.
    """
    directory, filename = os.path.split(file)

    try:
        tree = ast.parse(code, filename=file)
    except SyntaxError as e:
        raise RuntimeError(f"SyntaxError: {e}")

    checker = Checker(tree)

    stars = star_imports(checker)
    names = names_to_replace(checker)

    mod_names = {}
    for mod in stars:
        mod_names[mod] = get_module_names(mod, directory, allow_dynamic=allow_dynamic)

    repls = {i: [] for i in stars}
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

    new_code = replace_imports(code, repls, file=file, verbose=verbose,
                               quiet=quiet, max_line_length=max_line_length)

    return new_code

def replace_imports(code, repls, *, max_line_length=100, file=None, verbose=False, quiet=False):
    """
    Replace the star imports in code

    repls should be a dictionary mapping module names to a list of names to be
    imported.

    max_line_length (default: 100) is the maximum number of characters for a
    line. Added imports that are longer than this are wrapped. Set to
    float('inf') to disable wrapping. Note that only the names being imported
    are line wrapped. If the "from module import" part of the import is longer
    than the max_line_length, it is not line wrapped.

    If file is provided it is only used for the verbose messages.

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

        STAR_IMPORT = re.compile(rf'from +{re.escape(mod)} +import +\*\n')
        if not names:
            new_import = ""
        else:
            new_import = f"from {mod} import " + ', '.join(names) + '\n'
            if len(new_import) - len(names[-1]) > max_line_length:
                lines = []
                line = f"from {mod} import ("
                indent = ' '*len(line)
                for name in names:
                    if len(line + name + ',') > max_line_length and line[-1] != '(':
                        lines.append(line.rstrip())
                        line = indent
                    line += name + ', '
                lines.append(line[:-2] + ')') # Remove last trailing comma
                new_import = '\n'.join(lines) + '\n'

        new_code = STAR_IMPORT.sub(new_import, code)
        if new_code == code:
            if not quiet:
                prefix = f"Warning: {file}:" if file else "Warning:"
                print(f"{prefix} Could not find the star imports for '{mod}'", file=sys.stderr)
        elif verbose:
            msg = f"Replacing 'from {mod} import *' with '{new_import.strip()}'"
            if file:
                msg = f"{file}: {msg}"
            print(msg, file=sys.stderr)
        code = new_code

    return code

class ExternalModuleError(Exception):
    pass

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
        same_module = False
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
                else:
                    same_module = True
            if head in [Path('.'), Path('/')]:
                if same_module:
                    raise RuntimeError(f"Could not find the file for the module '{mod}'")
                raise ExternalModuleError
            head, tail = head.parent, head.name

    return filename

@lru_cache()
def get_module_names(mod, directory, *, allow_dynamic=True, _found=()):
    """
    Get the names defined in the module 'mod'

    'directory' should be the directory where the file with the import is.
    This is only used for static import determination.

    If allow_dynamic=True, then external module names are found by importing
    the module directly.
    """
    try:
        names = get_names_from_dir(mod, directory, allow_dynamic=allow_dynamic, _found=_found)
    except ExternalModuleError:
        if allow_dynamic:
            names = get_names_dynamically(mod)
        else:
            raise NotImplementedError("Static determination of external module imports is not supported.")
    return names

def get_names_dynamically(mod):
    d = {}
    try:
        exec(f'from {mod} import *', d)
    except ImportError:
        raise RuntimeError(f"Could not import {mod}")
    except Exception as e:
        raise RuntimeError(f"Error importing {mod}: {e}")
    return d.keys() - set(MAGIC_GLOBALS)

def get_names_from_dir(mod, directory, *, allow_dynamic=True, _found=()):
    filename = Path(get_mod_filename(mod, directory))

    with open(filename) as f:
        code = f.read()

    try:
        names = get_names(code, filename)
    except SyntaxError as e:
        raise RuntimeError(f"Could not parse {filename}: {e}")
    except RuntimeError:
        raise RuntimeError(f"Could not parse the names from {filename}")

    for name in names.copy():
        if name.endswith('.*'):
            names.remove(name)
            rec_mod = name[:-2]
            if rec_mod not in _found:
                _found += (rec_mod,)
                names = names.union(get_module_names(rec_mod, filename.parent,
                    allow_dynamic=allow_dynamic, _found=_found))
    return names


def get_names(code, filename='<unknown>'):
    # TODO: Make the doctests work
    """
    Get a set of defined top-level names from code.

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

    __all__ is respected. Constructs supported by pyflakes like __all__ += [...] work.

    >>> get_names('''
    ... a = 1
    ... b = 2
    ... c = 3
    ... __all__ = ['a']
    ... __all__ += ['b']
    ... ''') # doctest: +SKIP
    {'a', 'b'}

    Returns a set of names, or raises SyntaxError if the code is not valid
    syntax.
    """
    tree = ast.parse(code, filename=filename)

    checker = Checker(tree)
    for scope in checker.deadScopes:
        if isinstance(scope, ModuleScope):
            names = scope.keys() - set(dir(builtins)) - set(MAGIC_GLOBALS)
            break
    else:
        raise RuntimeError("Could not parse the names")

    if '__all__' in names:
        return set(scope['__all__'].names)
    return names

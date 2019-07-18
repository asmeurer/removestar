#!/usr/bin/env python
"""
Tool to automatically replace "import *" imports with explicit imports

Requires pyflakes. Somewhat inspired by autoflake.
"""

from pyflakes.checker import Checker, _MAGIC_GLOBALS, ModuleScope
from pyflakes.messages import ImportStarUsage, ImportStarUsed

import sys
import argparse
import ast
import os
import re
import builtins
import glob

from collections import defaultdict

def names_to_replace(checker):
    names = {}
    for message in checker.messages:
        if isinstance(message, ImportStarUsage):
            name, *modules = message.message_args
            names[name] = modules
    return names

def star_imports(checker):
    stars = []
    for message in checker.messages:
        if isinstance(message, ImportStarUsed):
            stars.append(message.message_args[0])
    return stars

def fix_code(code, directory):
    """
    Return a fixed version of code, or raise SyntaxError if code is not valid Python
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise RuntimeError(f"SyntaxError: {e}")

    checker = Checker(tree)

    stars = star_imports(checker)
    names = names_to_replace(checker)

    mod_names = {}
    repls = defaultdict(list)
    for mod in stars:
        mod_names[mod] = get_names(mod, directory)
    for name in names:
        mods = [mod for mod in mod_names if name in mod_names[mod]]
        if not mods:
            print(f"Warning: could not find import for {name}", file=sys.stderr)
            continue
        if len(mods) > 1:
            print(f"Warning: '{name}' comes from multiple modules: {', '.join(mods)}. Using {mods[-1]}.", file=sys.stderr)

        repls[mod].append(name)

    code = replace_imports(code, repls)

def replace_imports(code, repls):
    for mod in repls:
        names = sorted(repls[mod])

        STAR_IMPORT = re.compile(rf'from +{re.escape(mod)} +import +\*')
        new_import = f"from {mod} import" + ', '.join(repls[mod])
        if len(new_import) > 100: #TODO: make this configurable
            new_import = line = f"from {mod} import ("
            indent = ' '*len(line)
            while names:
                while len(line) < 100:
                    line += 'name' + ','
                new_import += line
                line = indent
            new_import = ')'

        new_code = STAR_IMPORT.sub(new_import, code)
        if new_code == code:
            print("Warning: Could not find the star imports for {mod}.", file=sys.stderr)
        code = new_code

    return code

def get_names(mod, directory):
    # TODO: Use the import machinery to do this.
    dots = re.compile(r'(\.+)([^\.].+)')
    m = dots.match(mod)
    if m:
        # Relative import
        loc = os.path.join(directory, m.group(0), *m.group(1).split('.'))
        if os.path.isfile(loc + '.py'):
            file = loc + '.py'
        else:
            file = os.path.join(loc, '__init__.py')
        if not os.path.isfile(file):
            raise RuntimeError(f"Could not fine the file for the module {mod}")
    else:
        raise NotImplementedError("Non-relative imports are not supported yet")

    with open(file) as f:
        code = f.read()

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise RuntimeError(f"Could not parse {file}: {e}")

    checker = Checker(tree)
    for scope in checker.deadScopes:
        if isinstance(scope, ModuleScope):
            return scope - set(dir(builtins)) - set(_MAGIC_GLOBALS)

    raise RuntimeError(f"Could not parse the names from {file}")

def main():
    parser = argparse.ArgumentParser(description=__doc__, prog='removestar')
    parser.add_argument('paths', nargs='+', help="files or directories to fix")
    args = parser.parse_args()

    for path in args.paths:
        for file in glob.iglob(path, recursive=True):
            directory, filename = os.path.split(file)
            with open(file, 'rw') as f:
                code = f.read()
                try:
                    new_code = fix_code(code, directory)
                except RuntimeError as e:
                    sys.exit(f"Error with {file}: {e}")
                f.write(new_code)

if __name__ == '__main__':
    main()

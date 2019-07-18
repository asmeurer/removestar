#!/usr/bin/env python
"""
Tool to automatically replace "import *" imports with explicit imports

Requires pyflakes. Somewhat inspired by autoflake.

Limitations:

- Only works with relative imports at the moment
- Does not work correctly with recursive star imports
- Assumes only names in the current file are used by star imports
"""
from . import __version__

from pyflakes.checker import Checker, _MAGIC_GLOBALS, ModuleScope
from pyflakes.messages import ImportStarUsage, ImportStarUsed

import sys
import argparse
import ast
import os
import re
import builtins
import glob
import difflib
import io

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

def fix_code(code, directory, filename):
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
    repls = {i: [] for i in stars}
    for mod in stars:
        mod_names[mod] = get_names(mod, directory)
    for name in names:
        mods = [mod for mod in mod_names if name in mod_names[mod]]
        if not mods:
            print(f"Warning: {filename}: could not find import for '{name}'", file=sys.stderr)
            continue
        if len(mods) > 1:
            print(f"Warning: {filename}: '{name}' comes from multiple modules: {', '.join(map(repr, mods))}. Using '{mods[-1]}'.",
    file=sys.stderr)

        repls[mods[-1]].append(name)

    code = replace_imports(code, repls)

    return code

def replace_imports(code, repls):
    for mod in repls:
        names = sorted(repls[mod])

        STAR_IMPORT = re.compile(rf'from +{re.escape(mod)} +import +\*')
        if not names:
            new_import = ""
        else:
            new_import = f"from {mod} import " + ', '.join(repls[mod])
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
            print("Warning: Could not find the star imports for '{mod}'", file=sys.stderr)
        code = new_code

    return code

def get_names(mod, directory):
    # TODO: Use the import machinery to do this.
    dots = re.compile(r'(\.+)([^\.].+)')
    m = dots.match(mod)
    if m:
        # Relative import
        loc = os.path.join(directory, m.group(1), *m.group(2).split('.'))
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
            return scope.keys() - set(dir(builtins)) - set(_MAGIC_GLOBALS)

    raise RuntimeError(f"Could not parse the names from {file}")

def get_diff_text(old, new, filename):
    # Taken from https://github.com/myint/autoflake/blob/master/autoflake.py
    # Copyright (C) 2012-2018 Steven Myint
    #
    # Permission is hereby granted, free of charge, to any person obtaining
    # a copy of this software and associated documentation files (the
    # "Software"), to deal in the Software without restriction, including
    # without limitation the rights to use, copy, modify, merge, publish,
    # distribute, sublicense, and/or sell copies of the Software, and to
    # permit persons to whom the Software is furnished to do so, subject to
    # the following conditions:
    #
    # The above copyright notice and this permission notice shall be included
    # in all copies or substantial portions of the Software.
    #
    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    # EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    # MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
    # IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
    # CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
    # TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
    # SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
    """Return text of unified diff between old and new."""
    newline = '\n'
    diff = difflib.unified_diff(
        old, new,
        'original/' + filename,
        'fixed/' + filename,
        lineterm=newline)

    text = ''
    for line in diff:
        text += line

        # Work around missing newline (http://bugs.python.org/issue2142).
        if not line.endswith(newline):
            text += newline + r'\ No newline at end of file' + newline

    return text

def main():
    parser = argparse.ArgumentParser(description=__doc__, prog='removestar')
    parser.add_argument('paths', nargs='+', help="Files or directories to fix")
    parser.add_argument('-i', '--in-place', action='store_true', help="Edit the files in-place")
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    args = parser.parse_args()

    for path in args.paths:
        for file in glob.iglob(path, recursive=True):
            directory, filename = os.path.split(file)
            with open(file, 'r') as f:
                code = f.read()
                try:
                    new_code = fix_code(code, directory, file)
                except (RuntimeError, NotImplementedError) as e:
                    sys.exit(f"Error with {file}: {e}")

            if args.in_place:
                with open(file, 'w') as f:
                    f.write(new_code)
            else:
                print(get_diff_text(io.StringIO(code).readlines(),
                    io.StringIO(new_code).readlines(), file))

if __name__ == '__main__':
    main()

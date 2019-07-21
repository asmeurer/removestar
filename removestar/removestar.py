from pyflakes.checker import Checker, _MAGIC_GLOBALS, ModuleScope
from pyflakes.messages import ImportStarUsage, ImportStarUsed

import sys
import ast
import os
import re
import builtins

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
    Return a fixed version of code, or raise RuntimeError if code is not valid Python
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
            new_import = f"from {mod} import " + ', '.join(names)
            if len(new_import) - len(names[-1]) > 100: #TODO: make this configurable
                lines = []
                line = f"from {mod} import ("
                indent = ' '*len(line)
                for name in names:
                    line += name + ', '
                    if len(line) > 100:
                        lines.append(line.rstrip())
                        line = indent
                lines.append(line[:-2] + ')') # Remove last trailing comma
                new_import = '\n'.join(lines)

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

import ast
import builtins
import contextlib
import os
import re
import sys
from functools import lru_cache
from pathlib import Path

from pyflakes.checker import _MAGIC_GLOBALS, Checker, ModuleScope
from pyflakes.messages import ImportStarUsage, ImportStarUsed

with contextlib.suppress(ImportError):
    from nbconvert import NotebookExporter

from .output import green, yellow

# quit and exit are not included in old versions of pyflakes
MAGIC_GLOBALS = set(_MAGIC_GLOBALS).union({"quit", "exit"})


def names_to_replace(checker):
    names = set()
    for message in checker.messages:
        if isinstance(message, ImportStarUsage):
            name, *modules = message.message_args
            names.add(name)
    return names


def star_imports(checker):
    return [
        message.message_args[0]
        for message in checker.messages
        if isinstance(message, ImportStarUsed)
    ]


def fix_code(
    code,
    *,
    file,
    max_line_length=100,
    verbose=False,
    quiet=False,
    allow_dynamic=True,
    **kws_replace_imports,
):
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
        raise RuntimeError(f"SyntaxError: {e}") from e

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
                print(
                    yellow(f"Warning: {file}: could not find import for '{name}'"),
                    file=sys.stderr,
                )
            continue
        if len(mods) > 1 and not quiet:
            print(
                yellow(
                    f"Warning: {file}: '{name}' comes from multiple modules: {', '.join(map(repr, mods))}. Using '{mods[-1]}'."  # noqa: E501
                ),
                file=sys.stderr,
            )

        repls[mods[-1]].append(name)

    new_code = replace_imports(
        code,
        repls,
        file=file,
        verbose=verbose,
        quiet=quiet,
        max_line_length=max_line_length,
        **kws_replace_imports,
    )

    return new_code


def replace_imports(  # noqa: C901,PLR0913
    code,
    repls,
    *,
    max_line_length=100,
    file=None,
    verbose=False,
    quiet=False,
    return_replacements=False,
):
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
    warning_prefix = f"Warning: {file}: " if file else "Warning: "
    verbose_prefix = f"{file}: " if file else ""

    if return_replacements:
        repls_strings = {}
    for mod in repls:
        names = sorted(repls[mod])

        if not names:
            new_import = ""
        else:
            new_import = f"from {mod} import " + ", ".join(names)
            if len(new_import) > max_line_length:
                lines = []
                line = f"from {mod} import ("
                indent = " " * len(line)
                for name in names:
                    if len(line + name + ",") > max_line_length and line[-1] != "(":
                        lines.append(line.rstrip())
                        line = indent
                    line += name + ", "
                lines.append(line[:-2] + ")")  # Remove last trailing comma
                new_import = "\n".join(lines)

        def star_import_replacement(match, verbose=verbose, quiet=quiet):
            original_import, after_import, comment = match.group(0, 1, 2)
            if comment and is_noqa_comment_allowing_star_import(comment):
                if verbose:
                    print(
                        green(
                            f"{verbose_prefix}Retaining 'from {mod} import *' due to noqa comment"
                        ),
                        file=sys.stderr,
                    )
                return original_import

            if verbose:
                print(
                    green(
                        f"{verbose_prefix}Replacing 'from {mod} import *' with '{new_import.strip()}'"  # noqa: E501
                    ),
                    file=sys.stderr,
                )

            if not new_import and comment:
                if not quiet:
                    print(
                        yellow(
                            f"{warning_prefix}The removed star import statement for '{mod}' "
                            f"had an inline comment which may not make sense without the import"
                        ),
                        file=sys.stderr,
                    )
                return f"{comment}\n"
            if not (new_import or after_import):
                return ""
            return f'{new_import}{after_import or ""}\n'

        star_import = re.compile(rf"from +{re.escape(mod)} +import +\*( *(#.*))?\n")
        new_code, subs_made = star_import.subn(star_import_replacement, code)
        if subs_made == 0 and not quiet:
            print(
                yellow(f"{warning_prefix}Could not find the star imports for '{mod}'"),
                file=sys.stderr,
            )

        if return_replacements:
            for match in star_import.finditer(code):
                repls_strings[f"from {mod} import *"] = star_import_replacement(
                    match,
                    verbose=False,
                    quiet=True,
                ).strip()
                break

        code = new_code

    return repls_strings if return_replacements else code


# This regex is based on Flake8's noqa regex:
#   https://github.com/PyCQA/flake8/blob/9815f4/src/flake8/defaults.py#L27
# Our version is tweaked to prevent malformed comments being interpreted as bare
# "noqa" comments (ignore everything). The original version has strict
# requirements for spaces, while also allowing anything to follow a bare
# "# noqa" comment, which can result in unintuitive behaviour.
#
# The Flake8 version treats these as bare noqa comments, silencing all warnings
# instead of just E2:
#
#   "# E2"    (colon is missing)
#   "# "  (two spaces after colon)
#   "# noqa:\tE2"  (tab instead of space after colon)
INLINE_NOQA_COMMENT_PATTERN = re.compile(
    r"""
^[#][ \t]* noqa
(?::[ \t]*
    (?P<codes>
        (?:[A-Z]+[0-9]+ (?:[, \t]+)?)+
    )
)?
[ \t]*$
""",
    flags=re.IGNORECASE | re.VERBOSE,
)
NOQA_STAR_IMPORT_CODES = frozenset(["F401", "F403"])


def is_noqa_comment_allowing_star_import(comment):
    """
    Check if a comment string is a Flake8 noqa comment that permits star imports

    The codes F401 and F403 are taken to permit star imports, as is a noqa
    comment without codes.

    Example:

    >>> is_noqa_comment_allowing_star_import('# noqa')
    True
    >>> is_noqa_comment_allowing_star_import('# noqa: FOO12,F403,BAR12')
    True
    >>> is_noqa_comment_allowing_star_import('# generic comment')
    False
    """
    match = INLINE_NOQA_COMMENT_PATTERN.match(comment)
    return bool(
        match
        and (
            match.group("codes") is None
            or any(
                code.upper() in NOQA_STAR_IMPORT_CODES
                for code in re.split(r"[, \t]+", match.group("codes"))
            )
        )
    )


class ExternalModuleError(Exception):
    pass


def get_mod_filename(mod, directory):
    """
    Get the filename for `mod` relative to a file in `directory`.
    """
    # TODO: Use the import machinery to do this.
    directory = Path(directory)

    dots = re.compile(r"(\.+)(.*)")
    m = dots.match(mod)
    if m:
        # Relative import
        loc = directory.joinpath(*[".."] * (len(m.group(1)) - 1), *m.group(2).split("."))
        filename = Path(str(loc) + ".py")
        if not filename.is_file():
            filename = loc / "__init__.py"
        if not filename.is_file():
            raise RuntimeError(f"Could not find the file for the module '{mod}'")
    else:
        top, *rest = mod.split(".")

        # Try to find an absolute import from the same module as the file
        head, tail = directory.parent, directory.name
        same_module = False
        while True:
            # If directory is relative assume we
            # don't need to go higher than .
            if tail == top:
                loc = os.path.join(head, tail, *rest)
                if os.path.isfile(loc + ".py"):
                    filename = loc + ".py"
                    break
                elif os.path.isfile(os.path.join(loc, "__init__.py")):
                    filename = os.path.join(loc, "__init__.py")
                    break
                else:
                    same_module = True
            if head in [Path("."), Path("/")]:
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
    except ExternalModuleError as e:
        if allow_dynamic:
            names = get_names_dynamically(mod)
        else:
            raise NotImplementedError(
                "Static determination of external module imports is not supported."
            ) from e
    return names


def get_names_dynamically(mod):
    d = {}
    try:
        exec(f"from {mod} import *", d)
    except ImportError as import_e:
        raise RuntimeError(f"Could not import {mod}") from import_e
    except Exception as e:
        raise RuntimeError(f"Error importing {mod}: {e}") from e
    return d.keys() - set(MAGIC_GLOBALS)


def get_names_from_dir(mod, directory, *, allow_dynamic=True, _found=()):
    filename = Path(get_mod_filename(mod, directory))

    with open(filename) as f:
        code = f.read()

    try:
        names = get_names(code, filename)
    except SyntaxError as e:
        raise RuntimeError(f"Could not parse {filename}: {e}") from e
    except RuntimeError as runtime_e:
        raise RuntimeError(f"Could not parse the names from {filename}") from runtime_e

    for name in names.copy():
        if name.endswith(".*"):
            names.remove(name)
            rec_mod = name[:-2]
            if rec_mod not in _found:
                _found += (rec_mod,)
                names = names.union(
                    get_module_names(
                        rec_mod,
                        filename.parent,
                        allow_dynamic=allow_dynamic,
                        _found=_found,
                    )
                )
    return names


def get_names(code, filename="<unknown>"):
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

    if "__all__" in names:
        return set(scope["__all__"].names)
    return names


## for jupyter notebooks with .ipynb extension
def replace_in_nb(
    nb,
    replaces: dict,
    cell_type: str = "code",
):
    """
    Replace text in a jupyter notebook.

    Parameters
        nb: notebook object obtained from `nbformat.reads`.
        replaces (dict): mapping of text to 'replace from' to the one to 'replace with'.
        cell_type (str): the type of the cell.

    Returns:
        source_nb: Fixed code.
    """
    new_nb = nb.copy()
    for replace_from, replace_to in replaces.items():
        break_early = str(nb).count(replace_from) == 1
        for i, d in enumerate(new_nb["cells"]):
            if d["cell_type"] == cell_type and replace_from in d["source"]:
                d["source"] = d["source"].replace(replace_from, replace_to)
                new_nb["cells"][i] = d
                if break_early:
                    break

    ## save new nb
    to_nb = NotebookExporter()
    source_nb, _ = to_nb.from_notebook_node(new_nb)

    return source_nb

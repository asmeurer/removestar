# removestar

[![Actions Status][actions-badge]][actions-link]
[![PyPI version][pypi-version]][pypi-link]
[![Anaconda-Server Badge][conda-version]][conda-link]
[![PyPI platforms][pypi-platforms]][pypi-link]
[![Downloads][pypi-downloads]][pypi-link]
[![Conda Downloads][conda-downloads]][conda-link]
[![Ruff][ruff-badge]][ruff-link]

<!-- TODO:
[![pre-commit.ci status][pre-commit-badge]][pre-commit-link]
[![codecov percentage][codecov-badge]][codecov-link]
[![GitHub Discussion][github-discussions-badge]][github-discussions-link]
-->

Tool to automatically replace `import *` imports in Python files with explicit imports

## Installation

Install `removestar` globally to use it through CLI using `pypi` -

```bash
pip install removestar
pip install "removestar[nb]"  # notebook support
```

or `conda` -

```bash
conda install -c conda-forge removestar
```

or add `removestar` in `.pre-commit-config.yaml` -

```yaml
- repo: https://github.com/asmeurer/removestar
  rev: "1.5"
  hooks:
    - id: removestar
      args: [-i] # See docs for all args (-i edits file in-place)
      additional_dependencies: # The libraries or packages your code imports
        - ... # Add . if running inside a library (to install the library itself in the environment)
        - ... # Add nbformat and nbconvert for notebook support
```

## Usage

### pre-commit hook

Once `removestar` is added in `.pre-commit-config.yaml`, executing the following
will always run it (and other pre-commits) before every commit -

```bash
pre-commit install
```

Optionally, the pre-commits (including `removestar`) can be manually triggered for
all the files using -

```bash
pre-commit run --all-files
```

### CLI

```bash

# scripts

$ removestar file.py # Shows diff but does not edit file.py

$ removestar -i file.py # Edits file.py in-place

$ removestar -i module/ # Modifies every Python file in module/ recursively

# notebooks (make sure nbformat and nbconvert are installed)

$ removestar file.ipynb # Shows diff but does not edit file.ipynb

$ removestar -i file.ipynb # Edits file.ipynb in-place
```

## Why is `import *` so bad?

Doing `from module import *` is generally frowned upon in Python. It is
considered acceptable when working interactively at a `python` prompt, or in
`__init__.py` files (removestar skips `__init__.py` files by default).

Some reasons why `import *` is bad:

- It hides which names are actually imported.
- It is difficult both for human readers and static analyzers such as
  pyflakes to tell where a given name comes from when `import *` is used. For
  example, pyflakes cannot detect unused names (for instance, from typos) in
  the presence of `import *`.
- If there are multiple `import *` statements, it may not be clear which names
  come from which module. In some cases, both modules may have a given name,
  but only the second import will end up being used. This can break people's
  intuition that the order of imports in a Python file generally does not
  matter.
- `import *` often imports more names than you would expect. Unless the module
  you import defines `__all__` or carefully `del`s unused names at the module
  level, `import *` will import every public (doesn't start with an
  underscore) name defined in the module file. This can often include things
  like standard library imports or loop variables defined at the top-level of
  the file. For imports from modules (from `__init__.py`), `from module import
*` will include every submodule defined in that module. Using `__all__` in
  modules and `__init__.py` files is also good practice, as these things are
  also often confusing even for interactive use where `import *` is
  acceptable.
- In Python 3, `import *` is syntactically not allowed inside of a function.

Here are some official Python references stating not to use `import *` in
files:

- [The official Python
  FAQ](https://docs.python.org/3/faq/programming.html?highlight=faq#what-are-the-best-practices-for-using-import-in-a-module):

  > In general, don’t use `from modulename import *`. Doing so clutters the
  > importer’s namespace, and makes it much harder for linters to detect
  > undefined names.

- [PEP 8](https://www.python.org/dev/peps/pep-0008/#imports) (the official
  Python style guide):

  > Wildcard imports (`from <module> import *`) should be avoided, as they
  > make it unclear which names are present in the namespace, confusing both
  > readers and many automated tools.

Unfortunately, if you come across a file in the wild that uses `import *`, it
can be hard to fix it, because you need to find every name in the file that is
imported from the `*`. Removestar makes this easy by finding which names come
from `*` imports and replacing the import lines in the file automatically.

One exception where `import *` can be bneficial:
At the early stages of code development, a definite set of required
functions can be difficult to determine. In such a context, wildcard imports could be
beneficial by avoiding constantly curating the set of required functions. For example,
at the development stage usage of `from os.path import *` can save time from curating
required functions. Post-development, the wld card imports could be determined using
`removestar`. Having said that, because of the multiple said reasons, wildcard imports
should be avoided.

## Example

Suppose you have a module `mymod` like

```bash
mymod/
  | __init__.py
  | a.py
  | b.py
```

With

```py
# mymod/a.py
from .b import *


def func(x):
    return x + y
```

```py
# mymod/b.py
x = 1
y = 2
```

Then `removestar` works like:

```bash
$ removestar mymod/

--- original/mymod/a.py
+++ fixed/mymod/a.py
@@ -1,5 +1,5 @@
 # mymod/a.py
-from .b import *
+from .b import y

 def func(x):
     return x + y

```

This does not edit `a.py` by default. The `-i` flag causes it to edit `a.py` in-place:

```bash
$ removestar -i mymod/
$ cat mymod/a.py
# mymod/a.py
from .b import y

def func(x):
    return x + y
```

## Command line options

<!-- TODO: Autogenerate this somehow -->

```bash
$ removestar --help
usage: removestar [-h] [-i] [--version] [--no-skip-init]
                  [--no-dynamic-importing] [-v] [-q]
                  [--max-line-length MAX_LINE_LENGTH]
                  PATH [PATH ...]

Tool to automatically replace "import *" imports with explicit imports

Requires pyflakes.

Usage:

$ removestar file.py # Shows diff but does not edit file.py

$ removestar -i file.py # Edits file.py in-place

$ removestar -i module/ # Modifies every Python file in module/ recursively

positional arguments:
  PATH                  Files or directories to fix

optional arguments:
  -h, --help            show this help message and exit
  -i, --in-place        Edit the files in-place. (default: False)
  --version             Show removestar version number and exit.
  --no-skip-init        Don't skip __init__.py files (they are skipped by
                        default) (default: True)
  --no-dynamic-importing
                        Don't dynamically import modules to determine the list
                        of names. This is required for star imports from
                        external modules and modules in the standard library.
                        (default: True)
  -v, --verbose         Print information about every imported name that is
                        replaced. (default: False)
  -q, --quiet           Don't print any warning messages. (default: False)
  --max-line-length MAX_LINE_LENGTH
                        The maximum line length for replaced imports before
                        they are wrapped. Set to 0 to disable line wrapping.
                        (default: 100)
```

## Whitelisting star imports

`removestar` does not replace star import lines that are marked with
[Flake8 `noqa` comments][noqa-comments] that permit star imports (`F401` or
`F403`).

[noqa-comments]: https://flake8.pycqa.org/en/3.1.1/user/ignoring-errors.html#in-line-ignoring-errors

For example, the star imports in this module would be kept:

```py
from os import *  # noqa: F401
from .b import *  # noqa


def func(x):
    return x + y
```

## Current limitations

- Assumes only names in the current file are used by star imports (e.g., it
  won't work to replace star imports in `__init__.py`).

- For files within the same module, removestar determines missing imported names
  statically. For external library imports, including imports of standard
  library modules, it dynamically imports the module to determine the names.
  This can be disabled with the `--no-dynamic-importing` flag.

## Contributing

See the [issue tracker](https://github.com/asmeurer/removestar/issues). Pull
requests are welcome.

## Changelog

See the [CHANGELOG](CHANGELOG.md) file.

## License

[MIT](LICENSE)

[actions-badge]: https://github.com/asmeurer/removestar/workflows/CI/badge.svg
[actions-link]: https://github.com/asmeurer/removestar/actions
[codecov-badge]: https://codecov.io/gh/asmeurer/removestar/branch/main/graph/badge.svg?token=YBv60ueORQ
[codecov-link]: https://codecov.io/gh/asmeurer/removestar
[conda-downloads]: https://img.shields.io/conda/dn/conda-forge/removestar?color=green
[conda-link]: https://anaconda.org/conda-forge/removestar
[conda-version]: https://anaconda.org/conda-forge/removestar/badges/version.svg
[github-discussions-badge]: https://img.shields.io/static/v1?label=Discussions&message=Ask&color=blue&logo=github
[github-discussions-link]: https://github.com/asmeurer/removestar/discussions
[license-badge]: https://img.shields.io/badge/MIT-blue.svg
[license-link]: https://opensource.org/licenses/MIT
[pypi-downloads]: https://static.pepy.tech/badge/removestar
[pre-commit-badge]: https://results.pre-commit.ci/badge/github/asmeurer/removestar/develop.svg
[pre-commit-link]: https://results.pre-commit.ci/repo/github/asmeurer/removestar
[pypi-link]: https://pypi.org/project/removestar/
[pypi-platforms]: https://img.shields.io/pypi/pyversions/removestar
[pypi-version]: https://img.shields.io/pypi/v/removestar?color=blue
[ruff-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
[ruff-link]: https://github.com/astral-sh/ruff

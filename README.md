# removestar

[![Build Status](https://travis-ci.com/asmeurer/removestar.svg?branch=master)](https://travis-ci.com/asmeurer/removestar)

Tool to automatically replace `import *` imports with explicit imports

Requires pyflakes.

Current limitations:

- Does not work correctly with recursive star imports.
- Assumes only names in the current file are used by star imports (e.g., it
  won't work to replace star imports in `__init__.py`).

For files within the same module, removestar determines missing imported names
statically. For external library imports, including imports of standard
library modules, it dynamically imports the module to determine the names.
This can be disabled with the `--no-dynamic-importing` flag.

See the [issue tracker](https://github.com/asmeurer/removestar/issues). Pull
requests are welcome.

## Usage

```
$ removestar file.py # Shows diff but does not edit file.py

$ removestar -i file.py # Edits file.py in-place

$ removestar module/ # Modifies every Python file in module recursively
```

## Example

Suppose you have a module `mymod` like

```
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

```
$ removestar mymod

--- original/mymod/a.py
+++ fixed/mymod/a.py
@@ -1,5 +1,5 @@
 # mymod/a.py
-from .b import *
+from .b import y

 def func(x):
     return x + y

```

This does not edit `a.py`. The `-i` flag causes it to edit `a.py` in-place:

```
$ removestar -i mymod
$ cat mymod/a.py
# mymod/a.py
from .b import y

def func(x):
    return x + y
```

## Command line options

<!-- TODO: Autogenerate this somehow -->

```
$ removestar --help
usage: removestar [-h] [-i] [--version] [--no-skip-init]
                  [--no-dynamic-importing] [-v] [-q]
                  [--max-line-length MAX_LINE_LENGTH]
                  paths [paths ...]

Tool to automatically replace "import *" imports with explicit imports

Requires pyflakes.

Usage:

$ removestar file.py # Shows diff but does not edit file.py

$ removestar -i file.py # Edits file.py in-place

$ removestar module/ # Modifies every Python file in module recursively

positional arguments:
  paths                 Files or directories to fix

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

## Changelog

See the [CHANGELOG](CHANGELOG) file.

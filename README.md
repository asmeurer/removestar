# removestar

[![Build Status](https://travis-ci.com/asmeurer/removestar.svg?branch=master)](https://travis-ci.com/asmeurer/removestar)

Tool to automatically replace `import *` imports with explicit imports

Requires pyflakes. Somewhat inspired by autoflake.

Limitations:

- Only works with relative imports at the moment
- Does not work correctly with recursive star imports
- Assumes only names in the current file are used by star imports

See the [issue tracker](https://github.com/asmeurer/removestar/issues). Pull
requests are welcome.

## Usage

```
$ removestar file.py # Shows diff but does not edit file.py

$ removestar -i file.py # Edits file.py in-place

$ removestar module/ # Modifies every Python file in module recursively
```

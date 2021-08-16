# 1.2.4 (2021-08-16)
## Bug fixes
- Fix an incorrectly done release from 1.2.3.

# 1.2.3 (2021-08-16)
## Bug fixes
- Fix unformatted module name placeholder in "Could not find the star imports"
  warning (thanks to [@h4l](https://github.com/h4l)).

# 1.2.2 (2019-08-22)
## Bug fixes
- Names that are used more than once no longer produce duplicate imports.
- Files are no longer read redundantly.
- Files are no longer written into if the code does not change.
- A blank line is no longer printed for empty diffs.

# 1.2.1 (2019-08-17)
## Bug fixes
- Imports that are completely removed are no longer replaced with a blank line.

# 1.2 (2019-08-16)
## New Features
- removestar now works correctly with recursive star imports. In particular,
  `from .submod import *` now works when submod is a submodule whose
  `__init__.py` itself uses `import *` (removestar still skips `__init__.py`
  files by default).
- `__all__` is now respected.
- The full path to the file is printed for `--verbose` messages.
- Catch all errors when importing external modules dynamically.
- Better error message for same-module absolute imports that don't exist.

## Bug fixes
- Don't consider `__builtins__` to be imported from external modules (even
  though it technically is).
- Make sure pytest-doctestplus is installed when running the tests.

## Other
- Include the LICENSE file in the distribution and the setup.py metadata.

# 1.1 (2019-08-05)
## New Features
- Add `--verbose` and `--quiet` flags. `--verbose` prints about every name that an
  import is added for. `--quiet` hides all warning output.
- Add support for absolute imports. Absolute imports from the same module are
  scanned statically, the same as relative imports. Absolute imports from
  external modules are imported dynamically to get the list of names. This can
  be disabled with the flag `--no-dynamic-importing`.
- Add `--max-line-length` to control the line length at which imports are
  wrapped. The default is 100. It can be disabled with `remoevstar
  --max-line-length 0`.
- No longer stop traversing a directory when encountering a file with invalid
  syntax.

## Bug Fixes
- Fix logic for wrapping long imports
- Fix the filename in some error messages.

## Other
- Add tests.
- Move all TODOs to the GitHub issue tracker.

# 1.0.1 (2019-07-18)
## New Features
- Automatically skip non-.py files
- Automatically skip `__init__.py`
- Add flag `--no-skip-init` to not skip `__init__.py`

## Bug Fixes
- Fix directory recursion
- Fix multiline import logic

# 1.0 (2019-07-18)

Initial release

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

# 1.5.2 (2024-11-25)

## Features

- Python 3.13 support

## Maintenance

- Get rid of deprecated actions
- Add dependabot config
- pre-commit autoupdate

# 1.5.1 (2024-08-14)

## Fixes

- Make notebook support and dependencies optional

## Docs

- Valid pre-commit tag in README example

## Maintenance

- Pre commit updates
- pre-commit autoupdate
- Fix pytest config to run doctests

# 1.5.0 (2023-09-18)

## Features

- removestar can now be used to get rid of \* imports in jupyter
  notebooks (`.ipynb` files)

## Docs

- Fix typos in `README.md`

## Maintenance

- GitHub Actions: Add Python 3.12 release candidate to the testing
- Ruff: Set upper limits on code complexity
- Pre-commit autoupdate

# 1.4.0 (2023-09-06)

## Features

- removestar can now be used as a pre-commit hook.
- removestar now outputs colored text.

## Bug fixes

- Turn off verbose output for pre-commit hook.
- Add git archive support for auto versioning.
- Use utf-8 encoding in the command line interface.

## Maintenance

- Use trusted publisher deployment for PyPI uploads.
- Revamp the CI pipeline and create a CD pipeline.
- Enable pre-commit for formatting and linting.
- Migrate the build-backend to `hatch` and use `hatch-vcs` for versioning,
  getting rid of `setup.py`, `setup.cfg`, `MANIFEST.in`, `versioneer.py`,
  `conftest.py`, `pytest.ini`, and introducing `pyproject.toml`/
- Move the tests directory out of the removestar directory.
- Ruff: Ignore a new pylint rule.
- Upgrade linter from pyflakes to ruff.
- Upgrade GitHub Actions.
- Add `project_urls` to the metadata.

# 1.3.1 (2021-09-02)

## Bug Fixes

- Fix the line wrapping logic to always wrap import lines if they are greater
  than the max line length (previously it would not account for the last
  imported name in the line).

# 1.3 (2021-08-24)

## New Features

- Lines with star imports can now contain comments.
- Star imports can be whitelisted using `# noqa` comments.
- Replaced Travis CI with GitHub Actions.

Thanks to [@h4l](https://github.com/h4l) for these improvements.

# 1.2.4 (2021-08-16)

## Bug Fixes

- Fix an incorrectly done release from 1.2.3.

# 1.2.3 (2021-08-16)

## Bug Fixes

- Fix unformatted module name placeholder in "Could not find the star imports"
  warning (thanks to [@h4l](https://github.com/h4l)).

# 1.2.2 (2019-08-22)

## Bug Fixes

- Names that are used more than once no longer produce duplicate imports.
- Files are no longer read redundantly.
- Files are no longer written into if the code does not change.
- A blank line is no longer printed for empty diffs.

# 1.2.1 (2019-08-17)

## Bug Fixes

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

## Bug Fixes

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

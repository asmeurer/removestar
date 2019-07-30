#!/usr/bin/env python
"""
Tool to automatically replace "import *" imports with explicit imports

Requires pyflakes. Somewhat inspired by autoflake.

Limitations:

- Only works with relative imports at the moment
- Does not work correctly with recursive star imports
- Assumes only names in the current file are used by star imports

Usage:

$ removestar file.py # Shows diff but does not edit file.py

$ removestar -i file.py # Edits file.py in-place

$ removestar module/ # Modifies every Python file in module recursively

"""
from . import __version__

import argparse
import glob
import io
import os
import sys

from .removestar import fix_code
from .helper import get_diff_text

def main():
    parser = argparse.ArgumentParser(description=__doc__, prog='removestar', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('paths', nargs='+', help="Files or directories to fix")
    parser.add_argument('-i', '--in-place', action='store_true', help="Edit the files in-place")
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    parser.add_argument('--no-skip-init', action='store_false',
                        dest='skip_init', help="Don't skip __init__.py files (they are skipped by default)")
    parser.add_argument('-v', '--verbose', action='store_true', help="""Print information about every imported name that is replaced.""")
    parser.add_argument('-q', '--quiet', action='store_true', help="""Don't print any warning messages.""")

    args = parser.parse_args()

    for path in args.paths:
        if os.path.isdir(path):
            path = path + '/**'
        for file in glob.iglob(path, recursive=True):
            directory, filename = os.path.split(file)
            if path.endswith('*') and not filename.endswith('.py'):
                continue
            if args.skip_init and filename == '__init__.py':
                continue
            try:
                new_code = fix_code(file,
                                    verbose=args.verbose, quiet=args.quiet)
            except (RuntimeError, NotImplementedError) as e:
                sys.exit(f"Error with {file}: {e}")

            if args.in_place:
                with open(file, 'w') as f:
                    f.write(new_code)
            else:
                with open(file) as f:
                    code = f.read()

                print(get_diff_text(io.StringIO(code).readlines(),
                    io.StringIO(new_code).readlines(), file))

if __name__ == '__main__':
    main()

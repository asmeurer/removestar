#!/usr/bin/env python
"""
Tool to automatically replace "import *" imports with explicit imports

Requires pyflakes.

Usage:

$ removestar file.py # Shows diff but does not edit file.py

$ removestar -i file.py # Edits file.py in-place

$ removestar -i module/ # Modifies every Python file in module/ recursively

"""
from . import __version__

import argparse
import glob
import io
import os
import sys

from .removestar import fix_code
from .helper import get_diff_text

class RawDescriptionHelpArgumentDefaultsHelpFormatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    pass

def main():
    parser = argparse.ArgumentParser(description=__doc__, prog='removestar', formatter_class=RawDescriptionHelpArgumentDefaultsHelpFormatter)
    parser.add_argument('paths', nargs='+',
                        help="Files or directories to fix", metavar="PATH")
    parser.add_argument('-i', '--in-place', action='store_true', help="Edit the files in-place.")
    parser.add_argument('--version', action='version', version='%(prog)s ' +
    __version__, help="Show removestar version number and exit.")
    parser.add_argument('--no-skip-init', action='store_false',
                        dest='skip_init', help="Don't skip __init__.py files (they are skipped by default)")
    parser.add_argument('--no-dynamic-importing', action='store_false', dest='allow_dynamic', help="""Don't dynamically import modules to determine the list of names. This is required for star imports from external modules and modules in the standard library.""")
    parser.add_argument('-v', '--verbose', action='store_true', help="""Print information about every imported name that is replaced.""")
    parser.add_argument('-q', '--quiet', action='store_true', help="""Don't print any warning messages.""")
    parser.add_argument('--max-line-length', type=int, default=100,
    help="""The maximum line length for replaced imports before they are wrapped. Set to 0 to disable line wrapping.""")
    # For testing
    parser.add_argument('--_this-file', action='store_true', help=argparse.SUPPRESS)

    args = parser.parse_args()

    if args._this_file:
        print(__file__, end='')
        return

    if args.max_line_length == 0:
        args.max_line_length = float('inf')

    for file in _iter_paths(args.paths):
        directory, filename = os.path.split(file)
        if args.skip_init and filename == '__init__.py':
            continue

        if not os.path.isfile(file):
            print(f"Error: {file}: no such file or directory", file=sys.stderr)
            continue

        with open(file) as f:
            code = f.read()

        try:
            new_code = fix_code(code, file=file, max_line_length=args.max_line_length,
                                verbose=args.verbose, quiet=args.quiet, allow_dynamic=args.allow_dynamic)
        except (RuntimeError, NotImplementedError) as e:
            if not args.quiet:
                print(f"Error with {file}: {e}", file=sys.stderr)
            continue

        if new_code != code:
            if args.in_place:
                with open(file, 'w') as f:
                    f.write(new_code)
            else:

                print(get_diff_text(io.StringIO(code).readlines(),
                    io.StringIO(new_code).readlines(), file))

def _iter_paths(paths):
    for path in paths:
        if os.path.isdir(path):
            for file in glob.iglob(path + '/**', recursive=True):
                if not file.endswith('.py'):
                    continue
                yield file
        else:
            yield path

if __name__ == '__main__':
    main()

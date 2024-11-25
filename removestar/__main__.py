#!/usr/bin/env python
"""
Tool to automatically replace "import *" imports with explicit imports

Requires pyflakes.

Usage:

$ removestar file.py # Shows diff but does not edit file.py

$ removestar -i file.py # Edits file.py in-place

$ removestar -i module/ # Modifies every Python file in module/ recursively

"""

import argparse
import glob
import importlib.util
import io
import os
import sys
import tempfile

from . import __version__
from .helper import get_diff_text
from .output import get_colored_diff, red
from .removestar import fix_code


class RawDescriptionHelpArgumentDefaultsHelpFormatter(
    argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter
):
    pass


def main():  # noqa: PLR0912, C901
    parser = argparse.ArgumentParser(
        description=__doc__,
        prog="removestar",
        formatter_class=RawDescriptionHelpArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("paths", nargs="*", help="Files or directories to fix", metavar="PATH")
    parser.add_argument("-i", "--in-place", action="store_true", help="Edit the files in-place.")
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s " + __version__,
        help="Show removestar version number and exit.",
    )
    parser.add_argument(
        "--no-skip-init",
        action="store_false",
        dest="skip_init",
        help="Don't skip __init__.py files (they are skipped by default)",
    )
    parser.add_argument(
        "--no-dynamic-importing",
        action="store_false",
        dest="allow_dynamic",
        help="""Don't dynamically import modules to determine the list of names. This is required for star imports from external modules and modules in the standard library.""",  # noqa: E501
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="""Print information about every imported name that is replaced.""",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="""Don't print any warning messages.""",
    )
    parser.add_argument(
        "--max-line-length",
        type=int,
        default=100,
        help="""The maximum line length for replaced imports before they are wrapped. Set to 0 to disable line wrapping.""",  # noqa: E501
    )
    # For testing
    parser.add_argument("--_this-file", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args()

    if args._this_file:
        print(__file__, end="")
        return

    if args.max_line_length == 0:
        args.max_line_length = float("inf")

    try:
        import nbformat
        from nbconvert import PythonExporter

        from .removestar import replace_in_nb
    except ImportError:
        pass

    exit_1 = False
    for file in _iter_paths(args.paths):
        _, filename = os.path.split(file)
        if args.skip_init and filename == "__init__.py":
            continue

        if not os.path.isfile(file):
            print(red(f"Error: {file}: no such file or directory"), file=sys.stderr)
            continue
        if file.endswith(".py"):
            with open(file, encoding="utf-8") as f:
                code = f.read()

            try:
                new_code = fix_code(
                    code,
                    file=file,
                    max_line_length=args.max_line_length,
                    verbose=args.verbose,
                    quiet=args.quiet,
                    allow_dynamic=args.allow_dynamic,
                )
            except (RuntimeError, NotImplementedError) as e:
                if not args.quiet:
                    print(red(f"Error with {file}: {e}"), file=sys.stderr)
                continue

            if new_code != code:
                exit_1 = True
                if args.in_place:
                    with open(file, "w", encoding="utf-8") as f:
                        f.write(new_code)
                    if not args.quiet:
                        print(
                            get_colored_diff(
                                get_diff_text(
                                    io.StringIO(code).readlines(),
                                    io.StringIO(new_code).readlines(),
                                    file,
                                )
                            )
                        )
                else:
                    print(
                        get_colored_diff(
                            get_diff_text(
                                io.StringIO(code).readlines(),
                                io.StringIO(new_code).readlines(),
                                file,
                            )
                        )
                    )
        elif (
            file.endswith(".ipynb")
            and importlib.util.find_spec("nbconvert") is not None
            and importlib.util.find_spec("nbformat") is not None
        ):
            tmp_file = tempfile.NamedTemporaryFile()  # noqa: SIM115
            tmp_path = tmp_file.name

            with open(file) as f:
                nb = nbformat.reads(f.read(), nbformat.NO_CONVERT)

            ## save as py
            exporter = PythonExporter()
            code, _ = exporter.from_notebook_node(nb)
            tmp_file.write(code.encode("utf-8"))

            try:
                new_code = fix_code(
                    code=code,
                    file=tmp_path,
                    max_line_length=args.max_line_length,
                    verbose=args.verbose,
                    quiet=args.quiet,
                    allow_dynamic=args.allow_dynamic,
                    return_replacements=True,
                )
                new_code_not_dict = fix_code(
                    code=code,
                    file=tmp_path,
                    max_line_length=args.max_line_length,
                    verbose=False,
                    quiet=True,
                    allow_dynamic=args.allow_dynamic,
                    return_replacements=False,
                )
            except (RuntimeError, NotImplementedError) as e:
                if not args.quiet:
                    print(red(f"Error with {file}: {e}"), file=sys.stderr)
                continue

            tmp_file.close()

            if new_code_not_dict != code:
                exit_1 = True
                if args.in_place:
                    with open(file) as f:
                        nb = nbformat.reads(f.read(), nbformat.NO_CONVERT)
                        fixed_code = replace_in_nb(
                            nb,
                            new_code,
                            cell_type="code",
                        )

                    with open(file, "w+") as f:
                        f.writelines(fixed_code)

                    if not args.quiet:
                        print(
                            get_colored_diff(
                                get_diff_text(
                                    io.StringIO(code).readlines(),
                                    io.StringIO(new_code_not_dict).readlines(),
                                    file,
                                )
                            )
                        )
                else:
                    print(
                        get_colored_diff(
                            get_diff_text(
                                io.StringIO(code).readlines(),
                                io.StringIO(new_code_not_dict).readlines(),
                                file,
                            )
                        )
                    )

    if exit_1:
        sys.exit(1)


def _iter_paths(paths):
    for path in paths:
        if os.path.isdir(path):
            for file in glob.iglob(path + "/**", recursive=True):
                if not file.endswith(".py") and not file.endswith(".ipynb"):
                    continue
                yield file
        else:
            yield path


if __name__ == "__main__":
    main()

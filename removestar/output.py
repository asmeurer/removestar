def bold(line):
    return "\033[1m" + line + "\033[0m"  # bold, reset


def red(line):
    return "\033[31m" + line + "\033[0m"  # red, reset


def yellow(line):
    return "\033[33m" + line + "\033[0m"  # yellow, reset


def cyan(line):
    return "\033[36m" + line + "\033[0m"  # cyan, reset


def green(line):
    return "\033[32m" + line + "\033[0m"  # green, reset


def get_colored_diff(contents):
    """Inject the ANSI color codes to the diff."""
    # taken from https://github.com/psf/black/blob/main/src/black/output.py
    # Copyright (c) 2018 Łukasz Langa

    # Permission is hereby granted, free of charge, to any person obtaining a copy
    # of this software and associated documentation files (the "Software"), to deal
    # in the Software without restriction, including without limitation the rights
    # to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    # copies of the Software, and to permit persons to whom the Software is
    # furnished to do so, subject to the following conditions:

    # The above copyright notice and this permission notice shall be included in all
    # copies or substantial portions of the Software.

    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    # FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    # LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    # OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    # SOFTWARE.
    lines = contents.split("\n")
    for i, line in enumerate(lines):
        if line.startswith(("+++", "---")):
            line = bold(line)  # bold, reset  # noqa: PLW2901
        elif line.startswith("@@"):
            line = cyan(line)  # cyan, reset  # noqa: PLW2901
        elif line.startswith("+"):
            line = green(line)  # green, reset  # noqa: PLW2901
        elif line.startswith("-"):
            line = red(line)  # red, reset  # noqa: PLW2901
        lines[i] = line
    return "\n".join(lines)

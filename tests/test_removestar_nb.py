import os
import tempfile

import pytest

from removestar.removestar import fix_code, replace_in_nb

nbf = pytest.importorskip("nbformat")
nbc = pytest.importorskip("nbconvert")

fixed_code = """#!/usr/bin/env python
# coding: utf-8
# # Notebook for testing.
# In[ ]:
## import
from os.path import exists
# In[ ]:
## use of imported function
exists('_test.ipynb')"""


def prepare_nb(output_path="_test.ipynb"):
    """Make a demo notebook."""

    nb = nbf.v4.new_notebook()
    nb["cells"] = [
        nbf.v4.new_markdown_cell("# Notebook for testing."),
        nbf.v4.new_code_cell("## import\nfrom os.path import *"),
        nbf.v4.new_code_cell(f"## use of imported function\nexists('{output_path}')"),
    ]
    with open(output_path, "w") as f:
        nbf.write(nb, f)

    tmp_file = tempfile.NamedTemporaryFile()  # noqa: SIM115
    tmp_path = tmp_file.name

    with open(output_path) as f:
        nb = nbf.reads(f.read(), nbf.NO_CONVERT)

    exporter = nbc.PythonExporter()
    code, _ = exporter.from_notebook_node(nb)
    tmp_file.write(code.encode("utf-8"))

    return code, tmp_path


def test_fix_code_for_nb():
    code, tmp_path = prepare_nb(output_path="_test.ipynb")
    assert os.path.exists("_test.ipynb")

    new_code = fix_code(
        code=code,
        file=tmp_path,
        return_replacements=True,
    )
    assert new_code == {"from os.path import *": "from os.path import exists"}

    new_code_not_dict = fix_code(
        code=code,
        file=tmp_path,
        return_replacements=False,
    )
    assert "\n".join([s for s in new_code_not_dict.split("\n") if s]) == fixed_code

    os.remove("_test.ipynb")


def test_replace_nb():
    prepare_nb(output_path="_test.ipynb")
    assert os.path.exists("_test.ipynb")
    new_code = {"from os.path import *": "from os.path import exists"}
    with open("_test.ipynb") as f:
        nb = nbf.reads(f.read(), nbf.NO_CONVERT)
        fixed_code = replace_in_nb(
            nb,
            new_code,
            cell_type="code",
        )

    with open("_test.ipynb", "w+") as f:
        f.writelines(fixed_code)

    exporter = nbc.NotebookExporter()
    code, _ = exporter.from_filename("_test.ipynb")

    assert code == fixed_code

    os.remove("_test.ipynb")

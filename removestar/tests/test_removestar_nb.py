## test using pytest
def test_removestar_nb():
    def to_test_nb(output_path = '_test.ipynb'):
        """Make a demo notebook."""
        import nbformat as nbf
        nb = nbf.v4.new_notebook()
        nb['cells'] = [
            nbf.v4.new_markdown_cell("# Notebook for testing."),
            nbf.v4.new_code_cell("## import\nfrom os.path import *"),
            nbf.v4.new_code_cell(f"## use of imported function\nexists('{output_path}')"),
            ]
        with open(output_path, 'w') as f:
            nbf.write(nb, f)
        return output_path

    nb_path=to_test_nb(output_path = '_test.ipynb')
    from os.path import exists
    assert exists(nb_path), nb_path

    from ..removestar import removestar_nb
    removestar_nb(
        nb_path=nb_path,
        output_path=nb_path,
        py_path=None,
        in_place=True,
        verbose=True,
        # **kws_fix_code,
        )            

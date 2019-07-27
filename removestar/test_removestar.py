from pyflakes.checker import Checker

import ast
import os

from pytest import raises

from .removestar import (names_to_replace, star_imports, get_names,
                         get_names_from_file, fix_code)


code_mod1 = """
a = 1
aa = 2
b = 3
"""

code_mod2 = """
b = 1
c = 2
cc = 3
"""

code_mod3 = """
name = 0
"""

code_mod4 = """
from .mod1 import *
from .mod2 import *
from .mod3 import name

def func():
    return a + b + c + d + name
"""

code_mod4_fixed = """
from .mod1 import a
from .mod2 import b, c
from .mod3 import name

def func():
    return a + b + c + d + name
"""

code_submod1 = """
from ..mod1 import *
from ..mod2 import *
from ..mod3 import name

def func():
    return a + b + c + d + name
"""

code_submod1_fixed = """
from ..mod1 import a
from ..mod2 import b, c
from ..mod3 import name

def func():
    return a + b + c + d + name
"""

code_bad_syntax = """
from mod
"""

def create_module(directory):
    os.makedirs(directory)
    with open(directory/'mod1.py', 'w') as f:
        f.write(code_mod1)
    with open(directory/'mod2.py', 'w') as f:
        f.write(code_mod2)
    with open(directory/'mod3.py', 'w') as f:
        f.write(code_mod3)
    with open(directory/'mod4.py', 'w') as f:
        f.write(code_mod4)
    with open(directory/'__init__.py', 'w') as f:
        pass
    with open(directory/'mod_bad.py', 'w') as f:
        f.write(code_bad_syntax)
    submod = directory/'submod'
    os.makedirs(submod)
    with open(submod/'__init__.py', 'w') as f:
        pass
    with open(submod/'submod1.py', 'w') as f:
        f.write(code_submod1)

def test_names_to_replace():
    for code in [code_mod1, code_mod2, code_mod3]:
        names = names_to_replace(Checker(ast.parse(code)))
        assert names == []

    for code in [code_mod4, code_submod1]:
        names = names_to_replace(Checker(ast.parse(code)))
        assert names == ['a', 'b', 'c', 'd']

def test_star_imports():
    for code in [code_mod1, code_mod2, code_mod3]:
        stars = star_imports(Checker(ast.parse(code)))
        assert stars == []

    stars = star_imports(Checker(ast.parse(code_mod4)))
    assert stars == ['.mod1', '.mod2']

    stars = star_imports(Checker(ast.parse(code_submod1)))
    assert stars == ['..mod1', '..mod2']

def test_get_names():
    names = get_names(code_mod1)
    assert names == {'a', 'aa', 'b'}

    names = get_names(code_mod2)
    assert names == {'b', 'c', 'cc'}

    names = get_names(code_mod3)
    assert names == {'name'}

    names = get_names(code_mod4)
    # TODO: Remove the imported name 'name'
    assert names == {'.mod1.*', '.mod2.*', 'name', 'func'}

    names = get_names(code_submod1)
    # TODO: Remove the imported name 'name'
    assert names == {'..mod1.*', '..mod2.*', 'name', 'func'}

    raises(SyntaxError, lambda: get_names(code_bad_syntax))

def test_get_names_from_dir(tmpdir):
    directory = tmpdir/'module'
    create_module(directory)
    file = str(directory/'mod1.py')
    assert get_names_from_file('.mod1', file) == {'a', 'aa', 'b'}
    assert get_names_from_file('.mod2', file) == {'b', 'c', 'cc'}
    assert get_names_from_file('.mod3', file) == {'name'}
    assert get_names_from_file('.mod4', file) == {'.mod1.*', '.mod2.*', 'name', 'func'}
    raises(RuntimeError, lambda: get_names_from_file('.mod_bad', directory))

    submod = directory/'submod'
    file = str(submod/'submod1.py')
    assert get_names_from_file('.submod1', file) == {'..mod1.*', '..mod2.*', 'name', 'func'}
    assert get_names_from_file('..mod1', file) == {'a', 'aa', 'b'}
    assert get_names_from_file('..mod2', file) == {'b', 'c', 'cc'}
    assert get_names_from_file('..mod3', file) == {'name'}
    assert get_names_from_file('..mod4', file) == {'.mod1.*', '.mod2.*', 'name', 'func'}


def test_fix_code(tmpdir, capsys):
    directory = tmpdir/'module'
    create_module(directory)

    raises(RuntimeError, lambda: fix_code(directory/'notarealfile.py'))

    assert fix_code(str(directory/'mod1.py')) == code_mod1
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(str(directory/'mod2.py')) == code_mod2
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(str(directory/'mod3.py')) == code_mod3
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(str(directory/'mod4.py')) == code_mod4_fixed
    out, err = capsys.readouterr()
    assert not out
    assert 'Warning' in err
    assert str(directory/'mod4.py') in err
    assert "'b'" in err
    assert "'a'" not in err
    assert "'.mod1'" in err
    assert "'.mod2'" in err
    assert "Using '.mod2'" in err
    assert "could not find import for 'd'" in err

    submod = directory/'submod'
    raises(RuntimeError, lambda: fix_code(str(submod)))
    assert fix_code(str(submod/'submod1.py')) == code_submod1_fixed
    out, err = capsys.readouterr()
    assert not out
    assert 'Warning' in err
    assert str(submod/'submod1.py') in err
    assert "'b'" in err
    assert "'a'" not in err
    assert "'..mod1'" in err
    assert "'..mod2'" in err
    assert "'.mod1'" not in err
    assert "'.mod2'" not in err
    assert "Using '..mod2'" in err
    assert "could not find import for 'd'" in err

    raises(RuntimeError, lambda: fix_code(str(directory/'mod_bad.py')))
    out, err = capsys.readouterr()
    assert not out
    assert not err

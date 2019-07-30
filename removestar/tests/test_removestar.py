from pyflakes.checker import Checker

import ast
import os
from pathlib import Path

from pytest import raises
import pytest

from ..removestar import (names_to_replace, star_imports, get_names,
                          get_names_from_dir, fix_code, get_mod_filename, replace_imports)


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

code_mod5 = """
from module.mod1 import *
from module.mod2 import *
from module.mod3 import name

def func():
    return a + b + c + d + name
"""

code_mod5_fixed = """
from module.mod1 import a
from module.mod2 import b, c
from module.mod3 import name

def func():
    return a + b + c + d + name
"""

code_submod1 = """
from ..mod1 import *
from ..mod2 import *
from ..mod3 import name
from .submod3 import *

def func():
    return a + b + c + d + e + name
"""

code_submod1_fixed = """
from ..mod1 import a
from ..mod2 import b, c
from ..mod3 import name
from .submod3 import e

def func():
    return a + b + c + d + e + name
"""

code_submod2 = """
from module.mod1 import *
from module.mod2 import *
from module.mod3 import name
from module.submod.submod3 import *

def func():
    return a + b + c + d + e + name
"""

code_submod2_fixed = """
from module.mod1 import a
from module.mod2 import b, c
from module.mod3 import name
from module.submod.submod3 import e

def func():
    return a + b + c + d + e + name
"""

code_submod3 = """
e = 1
"""

code_submod4 = """
from . import *

func()
"""

code_submod4_fixed = """
from . import func

func()
"""

code_submod_init = """
from .submod1 import func
"""

code_bad_syntax = """
from mod
"""

def create_module(module):
    os.makedirs(module)
    with open(module/'mod1.py', 'w') as f:
        f.write(code_mod1)
    with open(module/'mod2.py', 'w') as f:
        f.write(code_mod2)
    with open(module/'mod3.py', 'w') as f:
        f.write(code_mod3)
    with open(module/'mod4.py', 'w') as f:
        f.write(code_mod4)
    with open(module/'mod5.py', 'w') as f:
        f.write(code_mod5)
    with open(module/'__init__.py', 'w') as f:
        pass
    with open(module/'mod_bad.py', 'w') as f:
        f.write(code_bad_syntax)
    submod = module/'submod'
    os.makedirs(submod)
    with open(submod/'__init__.py', 'w') as f:
        f.write(code_submod_init)
    with open(submod/'submod1.py', 'w') as f:
        f.write(code_submod1)
    with open(submod/'submod2.py', 'w') as f:
        f.write(code_submod2)
    with open(submod/'submod3.py', 'w') as f:
        f.write(code_submod3)
    with open(submod/'submod4.py', 'w') as f:
        f.write(code_submod4)

def test_names_to_replace():
    for code in [code_mod1, code_mod2, code_mod3, code_submod3, code_submod_init]:
        names = names_to_replace(Checker(ast.parse(code)))
        assert names == []

    for code in [code_mod4, code_mod5]:
        names = names_to_replace(Checker(ast.parse(code)))
        assert names == ['a', 'b', 'c', 'd']

    for code in [code_submod1, code_submod2]:
        names = names_to_replace(Checker(ast.parse(code)))
        assert names == ['a', 'b', 'c', 'd', 'e']

    names = names_to_replace(Checker(ast.parse(code_submod4)))
    assert names == ['func']

def test_star_imports():
    for code in [code_mod1, code_mod2, code_mod3, code_submod3, code_submod_init]:
        stars = star_imports(Checker(ast.parse(code)))
        assert stars == []

    stars = star_imports(Checker(ast.parse(code_mod4)))
    assert stars == ['.mod1', '.mod2']

    stars = star_imports(Checker(ast.parse(code_mod5)))
    assert stars == ['module.mod1', 'module.mod2']

    stars = star_imports(Checker(ast.parse(code_submod1)))
    assert stars == ['..mod1', '..mod2', '.submod3']

    stars = star_imports(Checker(ast.parse(code_submod2)))
    assert stars == ['module.mod1', 'module.mod2', 'module.submod.submod3']

    stars = star_imports(Checker(ast.parse(code_submod4)))
    assert stars == ['.']

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

    names = get_names(code_mod5)
    # TODO: Remove the imported name 'name'
    assert names == {'module.mod1.*', 'module.mod2.*', 'name', 'func'}

    names = get_names(code_submod_init)
    assert names == {'func'}

    names = get_names(code_submod1)
    # TODO: Remove the imported name 'name'
    assert names == {'..mod1.*', '..mod2.*', '.submod3.*', 'name', 'func'}

    names = get_names(code_submod2)
    # TODO: Remove the imported name 'name'
    assert names == {'module.mod1.*', 'module.mod2.*',
                     'module.submod.submod3.*', 'name', 'func'}

    names = get_names(code_submod3)
    assert names == {'e'}

    names = get_names(code_submod4)
    assert names == {'..*'}

    raises(SyntaxError, lambda: get_names(code_bad_syntax))

@pytest.mark.parametrize('relative', [True, False])
def test_get_names_from_dir(tmpdir, relative):
    directory = tmpdir/'module'
    create_module(directory)
    if relative:
        chdir = tmpdir
        directory = Path('module')
    else:
        chdir = '.'
    curdir = os.path.abspath('.')
    try:
        os.chdir(chdir)
        assert get_names_from_dir('.mod1', directory) == {'a', 'aa', 'b'}
        assert get_names_from_dir('.mod2', directory) == {'b', 'c', 'cc'}
        assert get_names_from_dir('.mod3', directory) == {'name'}
        assert get_names_from_dir('.mod4', directory) == {'.mod1.*', '.mod2.*', 'name', 'func'}
        assert get_names_from_dir('.submod', directory) == {'func'}
        assert get_names_from_dir('.submod.submod1', directory) == {'..mod1.*', '..mod2.*', '.submod3.*', 'name', 'func'}
        assert get_names_from_dir('.submod.submod2', directory) == {'module.mod1.*',
            'module.mod2.*', 'module.submod.submod3.*', 'name', 'func'}
        assert get_names_from_dir('.submod.submod3', directory) == {'e'}
        assert get_names_from_dir('.submod.submod4', directory) == {'..*'}

        assert get_names_from_dir('module.mod1', directory) == {'a', 'aa', 'b'}
        assert get_names_from_dir('module.mod2', directory) == {'b', 'c', 'cc'}
        assert get_names_from_dir('module.mod3', directory) == {'name'}
        assert get_names_from_dir('module.mod4', directory) == {'.mod1.*', '.mod2.*', 'name', 'func'}
        assert get_names_from_dir('module.submod', directory) == {'func'}
        assert get_names_from_dir('module.submod.submod1', directory) == {'..mod1.*', '..mod2.*', '.submod3.*', 'name', 'func'}
        assert get_names_from_dir('module.submod.submod2', directory) == {'module.mod1.*',
            'module.mod2.*', 'module.submod.submod3.*', 'name', 'func'}
        assert get_names_from_dir('module.submod.submod3', directory) == {'e'}
        assert get_names_from_dir('module.submod.submod4', directory) == {'..*'}

        submod = directory/'submod'
        assert get_names_from_dir('..submod', submod) == {'func'}
        assert get_names_from_dir('.', submod) == {'func'}
        assert get_names_from_dir('.submod1', submod) == {'..mod1.*', '..mod2.*', '.submod3.*', 'name', 'func'}
        assert get_names_from_dir('.submod2', submod) == {'module.mod1.*',
            'module.mod2.*', 'module.submod.submod3.*', 'name', 'func'}
        assert get_names_from_dir('.submod3', submod) == {'e'}
        assert get_names_from_dir('.submod4', submod) == {'..*'}
        assert get_names_from_dir('..mod1', submod) == {'a', 'aa', 'b'}
        assert get_names_from_dir('..mod2', submod) == {'b', 'c', 'cc'}
        assert get_names_from_dir('..mod3', submod) == {'name'}
        assert get_names_from_dir('..mod4', submod) == {'.mod1.*', '.mod2.*', 'name', 'func'}
        assert get_names_from_dir('..mod5', submod) == {'module.mod1.*', 'module.mod2.*', 'name', 'func'}

        assert get_names_from_dir('module.mod1', directory) == {'a', 'aa', 'b'}
        assert get_names_from_dir('module.mod2', directory) == {'b', 'c', 'cc'}
        assert get_names_from_dir('module.mod3', directory) == {'name'}
        assert get_names_from_dir('module.mod4', directory) == {'.mod1.*', '.mod2.*', 'name', 'func'}
        assert get_names_from_dir('module.submod', directory) == {'func'}
        assert get_names_from_dir('module.submod.submod1', directory) == {'..mod1.*', '..mod2.*', '.submod3.*', 'name', 'func'}
        assert get_names_from_dir('module.submod.submod2', directory) == {'module.mod1.*',
            'module.mod2.*', 'module.submod.submod3.*', 'name', 'func'}
        assert get_names_from_dir('module.submod.submod3', directory) == {'e'}
        assert get_names_from_dir('module.submod.submod4', directory) == {'..*'}

        raises(RuntimeError, lambda: get_names_from_dir('.mod_bad', directory))
        raises(RuntimeError, lambda: get_names_from_dir('module.mod_bad', directory))
    finally:
        os.chdir(curdir)

def test_fix_code(tmpdir, capsys):
    directory = tmpdir/'module'
    create_module(directory)

    raises(RuntimeError, lambda: fix_code(directory/'notarealfile.py'))

    assert fix_code(directory/'mod1.py') == code_mod1
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(directory/'mod2.py') == code_mod2
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(directory/'mod3.py') == code_mod3
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(directory/'mod4.py') == code_mod4_fixed
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

    assert fix_code(directory/'mod5.py') == code_mod5_fixed
    out, err = capsys.readouterr()
    assert not out
    assert 'Warning' in err
    assert str(directory/'mod5.py') in err
    assert "'b'" in err
    assert "'a'" not in err
    assert "'module.mod1'" in err
    assert "'module.mod2'" in err
    assert "Using 'module.mod2'" in err
    assert "could not find import for 'd'" in err

    submod = directory/'submod'
    raises(RuntimeError, lambda: fix_code(submod))
    assert fix_code(submod/'submod1.py') == code_submod1_fixed
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

    submod = directory/'submod'
    raises(RuntimeError, lambda: fix_code(submod))
    assert fix_code(submod/'submod2.py') == code_submod2_fixed
    out, err = capsys.readouterr()
    assert not out
    assert 'Warning' in err
    assert str(submod/'submod2.py') in err
    assert "'b'" in err
    assert "'a'" not in err
    assert "'module.mod1'" in err
    assert "'module.mod2'" in err
    assert "'module.submod.submod3'" not in err
    assert "'module.submod.mod1'" not in err
    assert "'module.submod.mod2'" not in err
    assert "Using 'module.mod2'" in err
    assert "could not find import for 'd'" in err

    assert fix_code(submod/'submod3.py') == code_submod3
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(submod/'submod4.py') == code_submod4_fixed
    out, err = capsys.readouterr()
    assert not out
    assert not err

    raises(RuntimeError, lambda: fix_code(directory/'mod_bad.py'))
    out, err = capsys.readouterr()
    assert not out
    assert not err

def touch(f):
    with open(f, 'w'):
        pass

@pytest.mark.parametrize('relative', [True, False])
def test_get_mod_filename(tmpdir, relative):
    if relative:
        chdir = tmpdir
        tmpdir = Path('.')
    else:
        chdir = '.'
    curdir = os.path.abspath('.')
    try:
        os.chdir(chdir)

        module = tmpdir/'module'
        os.makedirs(module)
        touch(module/'__init__.py')
        touch(module/'mod1.py')
        submod = module/'submod'
        os.makedirs(submod)
        touch(submod/'__init__.py')
        touch(submod/'mod1.py')
        subsubmod = submod/'submod'
        os.makedirs(subsubmod)
        touch(subsubmod/'__init__.py')
        touch(subsubmod/'mod1.py')

        def _test(mod, directory, expected):
            result = os.path.abspath(get_mod_filename(mod, directory))
            assert result == os.path.abspath(expected)

        _test('.', module, module/'__init__.py')
        _test('.mod1', module, module/'mod1.py')
        _test('.submod', module, submod/'__init__.py')
        _test('.submod.mod1', module, submod/'mod1.py')
        _test('.submod.submod', module, subsubmod/'__init__.py')
        _test('.submod.submod.mod1', module, subsubmod/'mod1.py')

        _test('module', module, module/'__init__.py')
        _test('module.mod1', module, module/'mod1.py')
        _test('module.submod', module, submod/'__init__.py')
        _test('module.submod.mod1', module, submod/'mod1.py')
        _test('module.submod.submod', module, subsubmod/'__init__.py')
        _test('module.submod.submod.mod1', module, subsubmod/'mod1.py')

        _test('..', submod, module/'__init__.py')
        _test('..mod1', submod, module/'mod1.py')
        _test('.', submod, submod/'__init__.py')
        _test('.mod1', submod, submod/'mod1.py')
        _test('..submod', submod, submod/'__init__.py')
        _test('..submod.mod1', submod, submod/'mod1.py')
        _test('.submod', submod, subsubmod/'__init__.py')
        _test('.submod.mod1', submod, subsubmod/'mod1.py')
        _test('..submod.submod', submod, subsubmod/'__init__.py')
        _test('..submod.submod.mod1', submod, subsubmod/'mod1.py')

        _test('module', submod, module/'__init__.py')
        _test('module.mod1', submod, module/'mod1.py')
        _test('module.submod', submod, submod/'__init__.py')
        _test('module.submod.mod1', submod, submod/'mod1.py')
        _test('module.submod.submod', submod, subsubmod/'__init__.py')
        _test('module.submod.submod.mod1', submod, subsubmod/'mod1.py')

        _test('...', subsubmod, module/'__init__.py')
        _test('...mod1', subsubmod, module/'mod1.py')
        _test('..', subsubmod, submod/'__init__.py')
        _test('..mod1', subsubmod, submod/'mod1.py')
        _test('...submod', subsubmod, submod/'__init__.py')
        _test('...submod.mod1', subsubmod, submod/'mod1.py')
        _test('.', subsubmod, subsubmod/'__init__.py')
        _test('.mod1', subsubmod, subsubmod/'mod1.py')
        _test('...submod.submod', subsubmod, subsubmod/'__init__.py')
        _test('...submod.submod.mod1', subsubmod, subsubmod/'mod1.py')
        _test('..submod', subsubmod, subsubmod/'__init__.py')
        _test('..submod.mod1', subsubmod, subsubmod/'mod1.py')

        _test('module', subsubmod, module/'__init__.py')
        _test('module.mod1', subsubmod, module/'mod1.py')
        _test('module.submod', subsubmod, submod/'__init__.py')
        _test('module.submod.mod1', subsubmod, submod/'mod1.py')
        _test('module.submod.submod', subsubmod, subsubmod/'__init__.py')
        _test('module.submod.submod.mod1', subsubmod, subsubmod/'mod1.py')
    finally:
        os.chdir(curdir)

def test_replace_imports():
    # The verbose and quiet flags are already tested in test_fix_code
    for code in [code_mod1, code_mod2, code_mod3, code_submod3, code_submod_init]:
        assert replace_imports(code, repls={}, verbose=False, quiet=True) == code

    assert replace_imports(code_mod4, repls={'.mod1': ['a'], '.mod2': ['b', 'c']}, verbose=False, quiet=True) == code_mod4_fixed

    assert replace_imports(code_mod5, repls={'module.mod1': ['a'],
    'module.mod2': ['b', 'c']}, verbose=False, quiet=True) == code_mod5_fixed

    assert replace_imports(code_submod1, repls={'..mod1': ['a'], '..mod2':
    ['b', 'c'], '.submod3': ['e']}, verbose=False, quiet=True) == code_submod1_fixed

    assert replace_imports(code_submod2, repls={'module.mod1': ['a'],
    'module.mod2': ['b', 'c'], 'module.submod.submod3': ['e']}, verbose=False, quiet=True) == code_submod2_fixed

    assert replace_imports(code_submod4, repls={'.': ['func']},
    verbose=False, quiet=True) == code_submod4_fixed

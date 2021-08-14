from pyflakes.checker import Checker

import sys
import ast
import os
from pathlib import Path
from filecmp import dircmp
import subprocess

from pytest import raises
import pytest

from ..removestar import (names_to_replace, star_imports, get_names,
                          get_names_from_dir, get_names_dynamically, fix_code,
                          get_mod_filename, replace_imports,
                          ExternalModuleError)


code_mod1 = """\
a = 1
aa = 2
b = 3
"""

mod1_names = {'a', 'aa', 'b'}

code_mod2 = """\
b = 1
c = 2
cc = 3
"""

mod2_names = {'b', 'c', 'cc'}

code_mod3 = """\
name = 0
"""

mod3_names = {'name'}

code_mod4 = """\
from .mod1 import *
from .mod2 import *
from .mod3 import name

def func():
    return a + b + c + d + d + name
"""

mod4_names = {'a', 'aa', 'b', 'c', 'cc', 'name', 'func'}

code_mod4_fixed = """\
from .mod1 import a
from .mod2 import b, c
from .mod3 import name

def func():
    return a + b + c + d + d + name
"""

code_mod5 = """\
from module.mod1 import *
from module.mod2 import *
from module.mod3 import name

def func():
    return a + b + c + d + d + name
"""

mod5_names = {'a', 'aa', 'b', 'c', 'cc', 'name', 'func'}

code_mod5_fixed = """\
from module.mod1 import a
from module.mod2 import b, c
from module.mod3 import name

def func():
    return a + b + c + d + d + name
"""

code_mod6 = """\
from os.path import *
isfile(join('a', 'b'))
"""

code_mod6_fixed = """\
from os.path import isfile, join
isfile(join('a', 'b'))
"""

code_mod7 = """\
from .mod6 import *
"""

code_mod7_fixed = ""

mod7_names = {'isfile', 'join'}

code_mod8 = """\
a = 1
b = 2
c = 3
__all__ = ['a']
__all__ += ['b']
"""

mod8_names = {'a', 'b'}

code_mod9 = """\
from .mod8 import *

def func():
    return a + b
"""

code_mod9_fixed = """\
from .mod8 import a, b

def func():
    return a + b
"""

mod9_names = {'a', 'b', 'func'}

code_submod1 = """\
from ..mod1 import *
from ..mod2 import *
from ..mod3 import name
from .submod3 import *

def func():
    return a + b + c + d + d + e + name
"""

submod1_names = {'a', 'aa', 'b', 'c', 'cc', 'e', 'name', 'func'}

code_submod1_fixed = """\
from ..mod1 import a
from ..mod2 import b, c
from ..mod3 import name
from .submod3 import e

def func():
    return a + b + c + d + d + e + name
"""

code_submod2 = """\
from module.mod1 import *
from module.mod2 import *
from module.mod3 import name
from module.submod.submod3 import *

def func():
    return a + b + c + d + d + e + name
"""

submod2_names = {'a', 'aa', 'b', 'c', 'cc', 'e', 'name', 'func'}

code_submod2_fixed = """\
from module.mod1 import a
from module.mod2 import b, c
from module.mod3 import name
from module.submod.submod3 import e

def func():
    return a + b + c + d + d + e + name
"""

code_submod3 = """\
e = 1
"""

submod3_names = {'e'}

code_submod4 = """\
from . import *

func()
"""

submod4_names = {'func'}

code_submod4_fixed = """\
from . import func

func()
"""

code_submod_init = """\
from .submod1 import func
"""

submod_names = {'func'}
# An actual import adds submod1 and submod3 to the submod namespace, since
# they are imported submodule names. The static code does not yet support
# these. If any other imports happen first, like 'import submod.submod2',
# those would be included as well.
submod_dynamic_names = {'submod1', 'submod3', 'func'}

code_bad_syntax = """\
from mod
"""

code_mod_unfixable = """\
from .mod1 import *  # noqa: SOMECODE
from .mod2 import *;
from .mod3 import\t*

def func():
    return a + c + name
"""

mod_unfixable_names = {'a', 'aa', 'b', 'c', 'cc', 'name', 'func'}

code_submod_recursive_init = """\
from .submod1 import *
"""

submod_recursive_names = {'a', 'b'}
submod_recursive_dynamic_names = {'submod1', 'a', 'b'}

code_submod_recursive_submod1 = """\
a = 1
b = 2
"""

submod_recursive_submod1_names = {'a', 'b'}

code_submod_recursive_submod2 = """\
from . import *

def func():
    return a + 1
"""

submod_recursive_submod2_names = {'a', 'b', 'func'}
submod_recursive_submod2_dynamic_names = {'a', 'b', 'func', 'submod1'}

code_submod_recursive_submod2_fixed = """\
from . import a

def func():
    return a + 1
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
    with open(module/'mod6.py', 'w') as f:
        f.write(code_mod6)
    with open(module/'mod7.py', 'w') as f:
        f.write(code_mod7)
    with open(module/'mod8.py', 'w') as f:
        f.write(code_mod8)
    with open(module/'mod9.py', 'w') as f:
        f.write(code_mod9)
    with open(module/'__init__.py', 'w') as f:
        pass
    with open(module/'mod_bad.py', 'w') as f:
        f.write(code_bad_syntax)
    with open(module/'mod_unfixable.py', 'w') as f:
        f.write(code_mod_unfixable)
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
    submod_recursive = module/'submod_recursive'
    os.makedirs(submod_recursive)
    with open(submod_recursive/'__init__.py', 'w') as f:
        f.write(code_submod_recursive_init)
    with open(submod_recursive/'submod1.py', 'w') as f:
        f.write(code_submod_recursive_submod1)
    with open(submod_recursive/'submod2.py', 'w') as f:
        f.write(code_submod_recursive_submod2)

def test_names_to_replace():
    for code in [code_mod1, code_mod2, code_mod3, code_mod7, code_mod8,
                 code_submod3, code_submod_init, code_submod_recursive_init,
                 code_submod_recursive_submod1]:
        names = names_to_replace(Checker(ast.parse(code)))
        assert names == set()

    for code in [code_mod4, code_mod5]:
        names = names_to_replace(Checker(ast.parse(code)))
        assert names == {'a', 'b', 'c', 'd'}

    for code in [code_submod1, code_submod2]:
        names = names_to_replace(Checker(ast.parse(code)))
        assert names == {'a', 'b', 'c', 'd', 'e'}

    names = names_to_replace(Checker(ast.parse(code_submod4)))
    assert names == {'func'}

    names = names_to_replace(Checker(ast.parse(code_mod6)))
    assert names == {'isfile', 'join'}

    names = names_to_replace(Checker(ast.parse(code_submod_recursive_submod2)))
    assert names == {'a'}

    names = names_to_replace(Checker(ast.parse(code_mod9)))
    assert names == {'a', 'b'}

    names = names_to_replace(Checker(ast.parse(code_mod_unfixable)))
    assert names == {'a', 'c', 'name'}

def test_star_imports():
    for code in [code_mod1, code_mod2, code_mod3, code_mod8, code_submod3,
                 code_submod_init, code_submod_recursive_submod1]:
        stars = star_imports(Checker(ast.parse(code)))
        assert stars == []

    stars = star_imports(Checker(ast.parse(code_mod4)))
    assert stars == ['.mod1', '.mod2']

    stars = star_imports(Checker(ast.parse(code_mod5)))
    assert stars == ['module.mod1', 'module.mod2']

    stars = star_imports(Checker(ast.parse(code_mod6)))
    assert stars == ['os.path']

    stars = star_imports(Checker(ast.parse(code_mod7)))
    assert stars == ['.mod6']

    stars = star_imports(Checker(ast.parse(code_mod9)))
    assert stars == ['.mod8']

    stars = star_imports(Checker(ast.parse(code_submod1)))
    assert stars == ['..mod1', '..mod2', '.submod3']

    stars = star_imports(Checker(ast.parse(code_submod2)))
    assert stars == ['module.mod1', 'module.mod2', 'module.submod.submod3']

    for code in [code_submod4, code_submod_recursive_submod2]:
        stars = star_imports(Checker(ast.parse(code)))
        assert stars == ['.']

    stars = star_imports(Checker(ast.parse(code_submod_recursive_init)))
    assert stars == ['.submod1']

    stars = star_imports(Checker(ast.parse(code_mod_unfixable)))
    assert stars == ['.mod1', '.mod2', '.mod3']

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

    names = get_names(code_mod6)
    assert names == {'os.path.*'}

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

    names = get_names(code_mod_unfixable)
    assert names == {'.mod1.*', '.mod2.*', '.mod3.*', 'func'}

    names = get_names(code_submod_recursive_init)
    assert names == {'.submod1.*'}

    names = get_names(code_submod_recursive_submod1)
    assert names == {'a', 'b'}

    names = get_names(code_submod_recursive_submod2)
    assert names == {'..*', 'func'}

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
        assert get_names_from_dir('.mod1', directory) == mod1_names
        assert get_names_from_dir('.mod2', directory) == mod2_names
        assert get_names_from_dir('.mod3', directory) == mod3_names
        assert get_names_from_dir('.mod4', directory) == mod4_names
        assert get_names_from_dir('.mod5', directory) == mod5_names
        assert get_names_from_dir('.mod6', directory) == get_names_dynamically('os.path')
        raises(NotImplementedError, lambda: get_names_from_dir('.mod6', directory, allow_dynamic=False))
        assert get_names_from_dir('.mod7', directory) == get_names_dynamically('os.path')
        raises(NotImplementedError, lambda: get_names_from_dir('.mod7', directory, allow_dynamic=False))
        assert get_names_from_dir('.mod8', directory) == mod8_names
        assert get_names_from_dir('.mod9', directory) == mod9_names
        assert get_names_from_dir('.mod_unfixable', directory) == mod_unfixable_names
        assert get_names_from_dir('.submod', directory) == submod_names
        assert get_names_from_dir('.submod.submod1', directory) == submod1_names
        assert get_names_from_dir('.submod.submod2', directory) == submod2_names
        assert get_names_from_dir('.submod.submod3', directory) == submod3_names
        assert get_names_from_dir('.submod.submod4', directory) == submod4_names
        assert get_names_from_dir('.submod_recursive', directory) == submod_recursive_names
        assert get_names_from_dir('.submod_recursive.submod1', directory) == submod_recursive_submod1_names
        assert get_names_from_dir('.submod_recursive.submod2', directory) == submod_recursive_submod2_names

        assert get_names_from_dir('module.mod1', directory) == mod1_names
        assert get_names_from_dir('module.mod2', directory) == mod2_names
        assert get_names_from_dir('module.mod3', directory) == mod3_names
        assert get_names_from_dir('module.mod4', directory) == mod4_names
        assert get_names_from_dir('module.mod5', directory) == mod5_names
        assert get_names_from_dir('module.mod6', directory) == get_names_dynamically('os.path')
        raises(NotImplementedError, lambda: get_names_from_dir('module.mod6', directory, allow_dynamic=False))
        assert get_names_from_dir('module.mod7', directory) == get_names_dynamically('os.path')
        raises(NotImplementedError, lambda: get_names_from_dir('module.mod7', directory, allow_dynamic=False))
        assert get_names_from_dir('module.mod8', directory) == mod8_names
        assert get_names_from_dir('module.mod9', directory) == mod9_names
        assert get_names_from_dir('module.mod_unfixable', directory) == mod_unfixable_names
        assert get_names_from_dir('module.submod', directory) == submod_names
        assert get_names_from_dir('module.submod.submod1', directory) == submod1_names
        assert get_names_from_dir('module.submod.submod2', directory) == submod2_names
        assert get_names_from_dir('module.submod.submod3', directory) == submod3_names
        assert get_names_from_dir('module.submod.submod4', directory) == submod4_names
        assert get_names_from_dir('module.submod_recursive', directory) == submod_recursive_names
        assert get_names_from_dir('module.submod_recursive.submod1', directory) == submod_recursive_submod1_names
        assert get_names_from_dir('module.submod_recursive.submod2', directory) == submod_recursive_submod2_names

        submod = directory/'submod'
        assert get_names_from_dir('..submod', submod) == submod_names
        assert get_names_from_dir('.', submod) == submod_names
        assert get_names_from_dir('.submod1', submod) == submod1_names
        assert get_names_from_dir('.submod2', submod) == submod2_names
        assert get_names_from_dir('.submod3', submod) == submod3_names
        assert get_names_from_dir('.submod4', submod) == submod4_names
        assert get_names_from_dir('..mod1', submod) == mod1_names
        assert get_names_from_dir('..mod2', submod) == mod2_names
        assert get_names_from_dir('..mod3', submod) == mod3_names
        assert get_names_from_dir('..mod4', submod) == mod4_names
        assert get_names_from_dir('..mod5', submod) == mod5_names
        assert get_names_from_dir('..mod6', submod) == get_names_dynamically('os.path')
        raises(NotImplementedError, lambda: get_names_from_dir('..mod6', submod, allow_dynamic=False))
        assert get_names_from_dir('..mod7', submod) == get_names_dynamically('os.path')
        raises(NotImplementedError, lambda: get_names_from_dir('..mod7', submod, allow_dynamic=False))
        assert get_names_from_dir('..mod8', submod) == mod8_names
        assert get_names_from_dir('..mod9', submod) == mod9_names
        assert get_names_from_dir('..mod_unfixable', submod) == mod_unfixable_names
        assert get_names_from_dir('..submod_recursive', submod) == submod_recursive_names
        assert get_names_from_dir('..submod_recursive.submod1', submod) == submod_recursive_submod1_names
        assert get_names_from_dir('..submod_recursive.submod2', submod) == submod_recursive_submod2_names

        assert get_names_from_dir('module.mod1', submod) == mod1_names
        assert get_names_from_dir('module.mod2', submod) == mod2_names
        assert get_names_from_dir('module.mod3', submod) == mod3_names
        assert get_names_from_dir('module.mod4', submod) == mod4_names
        assert get_names_from_dir('module.mod5', submod) == mod5_names
        assert get_names_from_dir('module.mod6', submod) == get_names_dynamically('os.path')
        raises(NotImplementedError, lambda: get_names_from_dir('module.mod6', submod, allow_dynamic=False))
        assert get_names_from_dir('module.mod7', submod) == get_names_dynamically('os.path')
        raises(NotImplementedError, lambda: get_names_from_dir('module.mod7', submod, allow_dynamic=False))
        assert get_names_from_dir('module.mod8', submod) == mod8_names
        assert get_names_from_dir('module.mod9', submod) == mod9_names
        assert get_names_from_dir('module.mod_unfixable', submod) == mod_unfixable_names
        assert get_names_from_dir('module.submod', submod) == submod_names
        assert get_names_from_dir('module.submod.submod1', submod) == submod1_names
        assert get_names_from_dir('module.submod.submod2', submod) == submod2_names
        assert get_names_from_dir('module.submod.submod3', submod) == submod3_names
        assert get_names_from_dir('module.submod.submod4', submod) == submod4_names
        assert get_names_from_dir('module.submod_recursive', submod) == submod_recursive_names
        assert get_names_from_dir('module.submod_recursive.submod1', submod) == submod_recursive_submod1_names
        assert get_names_from_dir('module.submod_recursive.submod2', submod) == submod_recursive_submod2_names

        submod_recursive = directory/'submod_recursive'
        assert get_names_from_dir('..submod', submod_recursive) == submod_names
        assert get_names_from_dir('..submod.submod1', submod_recursive) == submod1_names
        assert get_names_from_dir('..submod.submod2', submod_recursive) == submod2_names
        assert get_names_from_dir('..submod.submod3', submod_recursive) == submod3_names
        assert get_names_from_dir('..submod.submod4', submod_recursive) == submod4_names
        assert get_names_from_dir('..mod1', submod_recursive) == mod1_names
        assert get_names_from_dir('..mod2', submod_recursive) == mod2_names
        assert get_names_from_dir('..mod3', submod_recursive) == mod3_names
        assert get_names_from_dir('..mod4', submod_recursive) == mod4_names
        assert get_names_from_dir('..mod5', submod_recursive) == mod5_names
        assert get_names_from_dir('..mod6', submod_recursive) == get_names_dynamically('os.path')
        raises(NotImplementedError, lambda: get_names_from_dir('..mod6', submod_recursive, allow_dynamic=False))
        assert get_names_from_dir('..mod7', submod_recursive) == get_names_dynamically('os.path')
        raises(NotImplementedError, lambda: get_names_from_dir('..mod7', submod_recursive, allow_dynamic=False))
        assert get_names_from_dir('..mod8', submod_recursive) == mod8_names
        assert get_names_from_dir('..mod9', submod_recursive) == mod9_names
        assert get_names_from_dir('..mod_unfixable', submod_recursive) == mod_unfixable_names
        assert get_names_from_dir('.', submod_recursive) == submod_recursive_names
        assert get_names_from_dir('..submod_recursive', submod_recursive) == submod_recursive_names
        assert get_names_from_dir('.submod1', submod_recursive) == submod_recursive_submod1_names
        assert get_names_from_dir('.submod2', submod_recursive) == submod_recursive_submod2_names

        assert get_names_from_dir('module.mod1', submod_recursive) == mod1_names
        assert get_names_from_dir('module.mod2', submod_recursive) == mod2_names
        assert get_names_from_dir('module.mod3', submod_recursive) == mod3_names
        assert get_names_from_dir('module.mod4', submod_recursive) == mod4_names
        assert get_names_from_dir('module.mod5', submod_recursive) == mod5_names
        assert get_names_from_dir('module.mod6', submod_recursive) == get_names_dynamically('os.path')
        raises(NotImplementedError, lambda: get_names_from_dir('module.mod6', submod, allow_dynamic=False))
        assert get_names_from_dir('module.mod7', submod_recursive) == get_names_dynamically('os.path')
        raises(NotImplementedError, lambda: get_names_from_dir('module.mod7', submod, allow_dynamic=False))
        assert get_names_from_dir('module.mod8', submod_recursive) == mod8_names
        assert get_names_from_dir('module.mod9', submod_recursive) == mod9_names
        assert get_names_from_dir('module.mod_unfixable', submod_recursive) == mod_unfixable_names
        assert get_names_from_dir('module.submod', submod_recursive) == submod_names
        assert get_names_from_dir('module.submod.submod1', submod_recursive) == submod1_names
        assert get_names_from_dir('module.submod.submod2', submod_recursive) == submod2_names
        assert get_names_from_dir('module.submod.submod3', submod_recursive) == submod3_names
        assert get_names_from_dir('module.submod.submod4', submod_recursive) == submod4_names
        assert get_names_from_dir('module.submod_recursive', submod_recursive) == submod_recursive_names
        assert get_names_from_dir('module.submod_recursive.submod1', submod_recursive) == submod_recursive_submod1_names
        assert get_names_from_dir('module.submod_recursive.submod2', submod_recursive) == submod_recursive_submod2_names

        raises(ExternalModuleError, lambda: get_names_from_dir('os.path', directory))
        raises(ExternalModuleError, lambda: get_names_from_dir('os.path', submod))
        raises(RuntimeError, lambda: get_names_from_dir('.mod_bad', directory))
        raises(RuntimeError, lambda: get_names_from_dir('module.mod_bad', directory))
        raises(RuntimeError, lambda: get_names_from_dir('.mod_doesnt_exist', directory))
        raises(RuntimeError, lambda: get_names_from_dir('module.mod_doesnt_exist', directory))
    finally:
        os.chdir(curdir)

def test_get_names_dynamically(tmpdir):
    os_path = get_names_dynamically('os.path')
    assert 'isfile' in os_path
    assert 'join' in os_path

    directory = tmpdir/'module'
    create_module(directory)
    sys_path = sys.path

    try:
        sys.path.insert(0, str(tmpdir))
        assert get_names_dynamically('module.mod1') == mod1_names
        assert get_names_dynamically('module.mod2') == mod2_names
        assert get_names_dynamically('module.mod3') == mod3_names
        assert get_names_dynamically('module.mod4') == mod4_names
        assert get_names_dynamically('module.mod5') == mod5_names
        assert get_names_dynamically('module.mod6') == os_path
        assert get_names_dynamically('module.mod7') == os_path
        assert get_names_dynamically('module.mod8') == mod8_names
        assert get_names_dynamically('module.mod9') == mod9_names
        assert get_names_dynamically('module.mod_unfixable') == mod_unfixable_names
        assert get_names_dynamically('module.submod') == submod_dynamic_names
        assert get_names_dynamically('module.submod.submod1') == submod1_names
        assert get_names_dynamically('module.submod.submod2') == submod2_names
        assert get_names_dynamically('module.submod.submod3') == submod3_names
        raises(RuntimeError, lambda: get_names_dynamically('module.submod.submod4'))
        assert get_names_dynamically('module.submod_recursive') == submod_recursive_dynamic_names
        assert get_names_dynamically('module.submod_recursive.submod1') == submod_recursive_submod1_names
        assert get_names_dynamically('module.submod_recursive.submod2') == submod_recursive_submod2_dynamic_names
        # Doesn't actually import because of the undefined name 'd'
        # assert get_names_dynamically('module.submod.submod4') == submod4_names
    finally:
        sys.path = sys_path

    raises(RuntimeError, lambda: get_names_dynamically('notarealmodule'))

def test_fix_code(tmpdir, capsys):
    # TODO: Test the verbose and quiet flags
    directory = tmpdir/'module'
    create_module(directory)

    assert fix_code(code_mod1, file=directory/'mod1.py') == code_mod1
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(code_mod2, file=directory/'mod2.py') == code_mod2
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(code_mod3, file=directory/'mod3.py') == code_mod3
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(code_mod4, file=directory/'mod4.py') == code_mod4_fixed
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

    assert fix_code(code_mod5, file=directory/'mod5.py') == code_mod5_fixed
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

    assert fix_code(code_mod6, file=directory/'mod6.py') == code_mod6_fixed
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert raises(NotImplementedError, lambda: fix_code(code_mod6, file=directory/'mod6.py', allow_dynamic=False))

    assert fix_code(code_mod7, file=directory/'mod7.py') == code_mod7_fixed
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert raises(NotImplementedError, lambda: fix_code(code_mod7, file=directory/'mod7.py', allow_dynamic=False))

    assert fix_code(code_mod8, file=directory/'mod8.py') == code_mod8
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(code_mod9, file=directory/'mod9.py') == code_mod9_fixed
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(code_mod_unfixable, file=directory/'mod_unfixable.py') == code_mod_unfixable
    out, err = capsys.readouterr()
    assert not out
    assert 'Warning' in err
    assert 'Could not find the star imports for' in err
    for mod in ["'.mod1'", "'.mod2'", "'.mod3'"]:
        assert mod in err

    submod = directory/'submod'

    assert fix_code(code_submod_init, file=submod/'__init__.py') == code_submod_init
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(code_submod1, file=submod/'submod1.py') == code_submod1_fixed
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

    assert fix_code(code_submod2, file=submod/'submod2.py') == code_submod2_fixed
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

    assert fix_code(code_submod3, file=submod/'submod3.py') == code_submod3
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(code_submod4, file=submod/'submod4.py') == code_submod4_fixed
    out, err = capsys.readouterr()
    assert not out
    assert not err

    submod_recursive = directory/'submod_recursive'

    # TODO: It's not actually useful to test this
    assert fix_code(code_submod_recursive_init, file=submod_recursive/'__init__.py') == ""
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(code_submod_recursive_submod1, file=submod_recursive/'submod1.py') == code_submod_recursive_submod1
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert fix_code(code_submod_recursive_submod2, file=submod_recursive/'submod2.py') == code_submod_recursive_submod2_fixed
    out, err = capsys.readouterr()
    assert not out
    assert not err

    raises(RuntimeError, lambda: fix_code(code_bad_syntax, file=directory/'mod_bad.py'))
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
        raises(RuntimeError, lambda: get_mod_filename('.notreal', module))

        _test('module', module, module/'__init__.py')
        _test('module.mod1', module, module/'mod1.py')
        _test('module.submod', module, submod/'__init__.py')
        _test('module.submod.mod1', module, submod/'mod1.py')
        _test('module.submod.submod', module, subsubmod/'__init__.py')
        _test('module.submod.submod.mod1', module, subsubmod/'mod1.py')
        raises(RuntimeError, lambda: get_mod_filename('module.notreal', module))
        raises(RuntimeError, lambda: get_mod_filename('module.submod.notreal', module))
        raises(ExternalModuleError, lambda: get_mod_filename('notreal.notreal', module))

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
        raises(RuntimeError, lambda: get_mod_filename('.notreal', submod))
        raises(RuntimeError, lambda: get_mod_filename('..notreal', submod))

        _test('module', submod, module/'__init__.py')
        _test('module.mod1', submod, module/'mod1.py')
        _test('module.submod', submod, submod/'__init__.py')
        _test('module.submod.mod1', submod, submod/'mod1.py')
        _test('module.submod.submod', submod, subsubmod/'__init__.py')
        _test('module.submod.submod.mod1', submod, subsubmod/'mod1.py')
        raises(RuntimeError, lambda: get_mod_filename('module.notreal', submod))
        raises(RuntimeError, lambda: get_mod_filename('module.submod.notreal', submod))
        raises(ExternalModuleError, lambda: get_mod_filename('notreal.notreal', submod))

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
        raises(RuntimeError, lambda: get_mod_filename('.notreal', subsubmod))
        raises(RuntimeError, lambda: get_mod_filename('..notreal', subsubmod))
        raises(RuntimeError, lambda: get_mod_filename('..notreal', subsubmod))

        _test('module', subsubmod, module/'__init__.py')
        _test('module.mod1', subsubmod, module/'mod1.py')
        _test('module.submod', subsubmod, submod/'__init__.py')
        _test('module.submod.mod1', subsubmod, submod/'mod1.py')
        _test('module.submod.submod', subsubmod, subsubmod/'__init__.py')
        _test('module.submod.submod.mod1', subsubmod, subsubmod/'mod1.py')
        raises(RuntimeError, lambda: get_mod_filename('module.notreal', subsubmod))
        raises(RuntimeError, lambda: get_mod_filename('module.submod.notreal', subsubmod))
        raises(ExternalModuleError, lambda: get_mod_filename('notreal.notreal', subsubmod))
    finally:
        os.chdir(curdir)

def test_replace_imports():
    # The verbose and quiet flags are already tested in test_fix_code
    for code in [code_mod1, code_mod2, code_mod3, code_mod8, code_submod3,
                 code_submod_init, code_submod_recursive_submod1, code_mod_unfixable]:
        assert replace_imports(code, repls={}, verbose=False, quiet=True) == code

    assert replace_imports(code_mod4, repls={'.mod1': ['a'], '.mod2': ['b', 'c']}, verbose=False, quiet=True) == code_mod4_fixed

    assert replace_imports(code_mod5, repls={'module.mod1': ['a'], 'module.mod2': ['b', 'c']}, verbose=False, quiet=True) == code_mod5_fixed
    assert replace_imports(code_mod6, repls={'os.path': ['isfile', 'join']}, verbose=False, quiet=False) == code_mod6_fixed
    assert replace_imports(code_mod7, repls={'.mod6': []}, verbose=False, quiet=False) == code_mod7_fixed
    assert replace_imports(code_mod9, repls={'.mod8': ['a', 'b']}, verbose=False, quiet=False) == code_mod9_fixed

    assert replace_imports(code_submod1, repls={'..mod1': ['a'], '..mod2':
    ['b', 'c'], '.submod3': ['e']}, verbose=False, quiet=True) == code_submod1_fixed

    assert replace_imports(code_submod2, repls={'module.mod1': ['a'],
    'module.mod2': ['b', 'c'], 'module.submod.submod3': ['e']}, verbose=False, quiet=True) == code_submod2_fixed

    assert replace_imports(code_submod4, repls={'.': ['func']}, verbose=False, quiet=True) == code_submod4_fixed

    assert replace_imports(code_submod_recursive_submod2, repls={'.': ['a']}) == code_submod_recursive_submod2_fixed

    assert replace_imports(code_mod_unfixable, repls={'.mod1': ['a'], '.mod2': ['c'], '.mod3': ['name']}) == code_mod_unfixable


def test_replace_imports_warnings(capsys):
    assert replace_imports(code_mod_unfixable, file='module/mod_unfixable.py', repls={'.mod1': ['a'], '.mod2': ['c'], '.mod3': ['name']}) == code_mod_unfixable
    out, err = capsys.readouterr()
    assert set(err.splitlines()) == {
        "Warning: module/mod_unfixable.py: Could not find the star imports for '.mod1'",
        "Warning: module/mod_unfixable.py: Could not find the star imports for '.mod2'",
        "Warning: module/mod_unfixable.py: Could not find the star imports for '.mod3'"
    }

    assert replace_imports(code_mod_unfixable, file=None, repls={'.mod1': ['a'], '.mod2': ['c'], '.mod3': ['name']}) == code_mod_unfixable
    out, err = capsys.readouterr()
    assert set(err.splitlines()) == {
        "Warning: Could not find the star imports for '.mod1'",
        "Warning: Could not find the star imports for '.mod2'",
        "Warning: Could not find the star imports for '.mod3'"
    }

    assert replace_imports(code_mod_unfixable, quiet=True, repls={'.mod1': ['a'], '.mod2': ['c'], '.mod3': ['name']}) == code_mod_unfixable
    out, err = capsys.readouterr()
    assert err == ''


def test_replace_imports_line_wrapping():
    code = """\
from reallyreallylongmodulename import *

print(longname1, longname2, longname3, longname4, longname5, longname6,
    longname7, longname8, longname9)
"""
    code_fixed = """\
{imp}

print(longname1, longname2, longname3, longname4, longname5, longname6,
    longname7, longname8, longname9)
"""
    repls = {'reallyreallylongmodulename': ['longname1', 'longname2', 'longname3', 'longname4', 'longname5', 'longname6', 'longname7', 'longname8', 'longname9']}

    assert replace_imports(code, repls) == code_fixed.format(imp='''\
from reallyreallylongmodulename import (longname1, longname2, longname3, longname4, longname5,
                                        longname6, longname7, longname8, longname9)''')

    # Make sure the first line has at least one imported name.
    # There's no point to doing
    #
    # from mod import (
    #                  name,
    #
    # if we are aligning the names to the opening parenthesis anyway.
    assert replace_imports(code, repls, max_line_length=49) == code_fixed.format(imp='''\
from reallyreallylongmodulename import (longname1,
                                        longname2,
                                        longname3,
                                        longname4,
                                        longname5,
                                        longname6,
                                        longname7,
                                        longname8,
                                        longname9)''')


    assert replace_imports(code, repls, max_line_length=50) == code_fixed.format(imp='''\
from reallyreallylongmodulename import (longname1,
                                        longname2,
                                        longname3,
                                        longname4,
                                        longname5,
                                        longname6,
                                        longname7,
                                        longname8,
                                        longname9)''')



    assert replace_imports(code, repls, max_line_length=51) == code_fixed.format(imp='''\
from reallyreallylongmodulename import (longname1,
                                        longname2,
                                        longname3,
                                        longname4,
                                        longname5,
                                        longname6,
                                        longname7,
                                        longname8,
                                        longname9)''')



    assert replace_imports(code, repls, max_line_length=120) == code_fixed.format(imp='''\
from reallyreallylongmodulename import (longname1, longname2, longname3, longname4, longname5, longname6, longname7,
                                        longname8, longname9)''')


    assert replace_imports(code, repls, max_line_length=200) == code_fixed.format(imp='''\
from reallyreallylongmodulename import longname1, longname2, longname3, longname4, longname5, longname6, longname7, longname8, longname9''')

    assert replace_imports(code, repls, max_line_length=float('inf')) == code_fixed.format(imp='''\
from reallyreallylongmodulename import longname1, longname2, longname3, longname4, longname5, longname6, longname7, longname8, longname9''')

def _dirs_equal(cmp):
    if cmp.diff_files:
        return False
    if not cmp.subdirs:
        return True
    return all(_dirs_equal(c) for c in cmp.subdirs.values())

def test_cli(tmpdir):
    from ..__main__ import __file__

    # TODO: Test the verbose and quiet flags
    directory_orig = tmpdir/'orig'/'module'
    directory = tmpdir/'module'
    create_module(directory)
    create_module(directory_orig)

    cmp = dircmp(directory, directory_orig)
    assert _dirs_equal(cmp)

    # Make sure we are running the command for the right file
    p = subprocess.run([sys.executable, '-m', 'removestar', '--_this-file', 'none'],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    assert p.stderr == ''
    assert p.stdout == __file__

    p = subprocess.run([sys.executable, '-m', 'removestar', directory],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    warnings = set(f"""\
Warning: {directory}/submod/submod1.py: 'b' comes from multiple modules: '..mod1', '..mod2'. Using '..mod2'.
Warning: {directory}/submod/submod1.py: could not find import for 'd'
Warning: {directory}/submod/submod2.py: 'b' comes from multiple modules: 'module.mod1', 'module.mod2'. Using 'module.mod2'.
Warning: {directory}/submod/submod2.py: could not find import for 'd'
Warning: {directory}/mod4.py: 'b' comes from multiple modules: '.mod1', '.mod2'. Using '.mod2'.
Warning: {directory}/mod4.py: could not find import for 'd'
Warning: {directory}/mod5.py: 'b' comes from multiple modules: 'module.mod1', 'module.mod2'. Using 'module.mod2'.
Warning: {directory}/mod5.py: could not find import for 'd'
Warning: {directory}/mod_unfixable.py: Could not find the star imports for '.mod1'
Warning: {directory}/mod_unfixable.py: Could not find the star imports for '.mod2'
Warning: {directory}/mod_unfixable.py: Could not find the star imports for '.mod3'
""".splitlines())

    error = f"Error with {directory}/mod_bad.py: SyntaxError: invalid syntax (mod_bad.py, line 1)"
    assert set(p.stderr.splitlines()) == warnings.union({error})

    diffs = [
f"""\
--- original/{directory}/mod4.py
+++ fixed/{directory}/mod4.py
@@ -1,5 +1,5 @@
-from .mod1 import *
-from .mod2 import *
+from .mod1 import a
+from .mod2 import b, c
 from .mod3 import name
 \n\
 def func():\
""",

f"""\
--- original/{directory}/mod5.py
+++ fixed/{directory}/mod5.py
@@ -1,5 +1,5 @@
-from module.mod1 import *
-from module.mod2 import *
+from module.mod1 import a
+from module.mod2 import b, c
 from module.mod3 import name
 \n\
 def func():\
""",

f"""\
--- original/{directory}/mod6.py
+++ fixed/{directory}/mod6.py
@@ -1,2 +1,2 @@
-from os.path import *
+from os.path import isfile, join
 isfile(join('a', 'b'))\
""",

f"""\
--- original/{directory}/mod7.py
+++ fixed/{directory}/mod7.py
@@ -1 +0,0 @@
-from .mod6 import *\
""",

f"""\
--- original/{directory}/mod9.py
+++ fixed/{directory}/mod9.py
@@ -1,4 +1,4 @@
-from .mod8 import *
+from .mod8 import a, b
 \n\
 def func():
     return a + b\
""",

f"""\
--- original/{directory}/submod/submod1.py
+++ fixed/{directory}/submod/submod1.py
@@ -1,7 +1,7 @@
-from ..mod1 import *
-from ..mod2 import *
+from ..mod1 import a
+from ..mod2 import b, c
 from ..mod3 import name
-from .submod3 import *
+from .submod3 import e
 \n\
 def func():
     return a + b + c + d + d + e + name\
""",

f"""\
--- original/{directory}/submod/submod2.py
+++ fixed/{directory}/submod/submod2.py
@@ -1,7 +1,7 @@
-from module.mod1 import *
-from module.mod2 import *
+from module.mod1 import a
+from module.mod2 import b, c
 from module.mod3 import name
-from module.submod.submod3 import *
+from module.submod.submod3 import e
 \n\
 def func():
     return a + b + c + d + d + e + name\
""",

f"""\
--- original/{directory}/submod/submod4.py
+++ fixed/{directory}/submod/submod4.py
@@ -1,3 +1,3 @@
-from . import *
+from . import func
 \n\
 func()\
""",

f"""\
--- original/{directory}/submod_recursive/submod2.py
+++ fixed/{directory}/submod_recursive/submod2.py
@@ -1,4 +1,4 @@
-from . import *
+from . import a
 \n\
 def func():
     return a + 1\
""",
    ]
    unchanged = ['__init__.py', 'mod_bad.py', 'mod_unfixable.py']
    for d in diffs:
        assert d in p.stdout, p.stdout
    for mod_path in unchanged:
        assert '--- original/{directory}/{mod_path}' not in p.stdout
    cmp = dircmp(directory, directory_orig)
    assert _dirs_equal(cmp)

    p = subprocess.run([sys.executable, '-m', 'removestar', '--quiet', directory],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    assert p.stderr == ''
    for d in diffs:
        assert d in p.stdout
    cmp = dircmp(directory, directory_orig)
    assert _dirs_equal(cmp)

    p = subprocess.run([sys.executable, '-m', 'removestar', '--verbose', directory],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       encoding='utf-8')
    changes = set(f"""\
{directory}/mod4.py: Replacing 'from .mod1 import *' with 'from .mod1 import a'
{directory}/mod4.py: Replacing 'from .mod2 import *' with 'from .mod2 import b, c'
{directory}/mod5.py: Replacing 'from module.mod1 import *' with 'from module.mod1 import a'
{directory}/mod5.py: Replacing 'from module.mod2 import *' with 'from module.mod2 import b, c'
{directory}/mod6.py: Replacing 'from os.path import *' with 'from os.path import isfile, join'
{directory}/mod7.py: Replacing 'from .mod6 import *' with ''
{directory}/mod9.py: Replacing 'from .mod8 import *' with 'from .mod8 import a, b'
{directory}/submod/submod1.py: Replacing 'from ..mod1 import *' with 'from ..mod1 import a'
{directory}/submod/submod1.py: Replacing 'from ..mod2 import *' with 'from ..mod2 import b, c'
{directory}/submod/submod1.py: Replacing 'from .submod3 import *' with 'from .submod3 import e'
{directory}/submod/submod4.py: Replacing 'from . import *' with 'from . import func'
{directory}/submod/submod2.py: Replacing 'from module.mod1 import *' with 'from module.mod1 import a'
{directory}/submod/submod2.py: Replacing 'from module.mod2 import *' with 'from module.mod2 import b, c'
{directory}/submod/submod2.py: Replacing 'from module.submod.submod3 import *' with 'from module.submod.submod3 import e'
{directory}/submod_recursive/submod2.py: Replacing 'from . import *' with 'from . import a'
""".splitlines())

    assert set(p.stderr.splitlines()) == changes.union({error}).union(warnings)
    for d in diffs:
        assert d in p.stdout, p.stdout
    cmp = dircmp(directory, directory_orig)
    assert _dirs_equal(cmp)


    p = subprocess.run([sys.executable, '-m', 'removestar', '--no-dynamic-importing', directory],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       encoding='utf-8')
    static_error = set(f"""\
Error with {directory}/mod6.py: Static determination of external module imports is not supported.
Error with {directory}/mod7.py: Static determination of external module imports is not supported.
""".splitlines())
    assert set(p.stderr.splitlines()) == {error}.union(static_error).union(warnings)
    for d in diffs:
        if 'mod6' in d:
            assert d not in p.stdout
        else:
            assert d in p.stdout, p.stdout
    cmp = dircmp(directory, directory_orig)
    assert _dirs_equal(cmp)

    # Test --quiet hides both errors
    p = subprocess.run([sys.executable, '-m', 'removestar', '--quiet', '--no-dynamic-importing', directory],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       encoding='utf-8')
    assert p.stderr == ''
    for d in diffs:
        if 'mod6' in d:
            assert d not in p.stdout
        else:
            assert d in p.stdout, p.stdout
    cmp = dircmp(directory, directory_orig)
    assert _dirs_equal(cmp)

    # XXX: This modifies directory, so keep it at the end of the test
    p = subprocess.run([sys.executable, '-m', 'removestar', '--quiet', '-i', directory],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    assert p.stderr == ''
    assert p.stdout == ''
    cmp = dircmp(directory, directory_orig)
    assert not _dirs_equal(cmp)
    assert cmp.diff_files == ['mod4.py', 'mod5.py', 'mod6.py', 'mod7.py', 'mod9.py']
    assert cmp.subdirs['submod'].diff_files == ['submod1.py', 'submod2.py', 'submod4.py']
    assert cmp.subdirs['submod_recursive'].diff_files == ['submod2.py']
    with open(directory/'mod4.py') as f:
        assert f.read() == code_mod4_fixed
    with open(directory/'mod5.py') as f:
        assert f.read() == code_mod5_fixed
    with open(directory/'mod6.py') as f:
        assert f.read() == code_mod6_fixed
    with open(directory/'mod7.py') as f:
        assert f.read() == code_mod7_fixed
    with open(directory/'mod9.py') as f:
        assert f.read() == code_mod9_fixed
    with open(directory/'submod'/'submod1.py') as f:
        assert f.read() == code_submod1_fixed
    with open(directory/'submod'/'submod2.py') as f:
        assert f.read() == code_submod2_fixed
    with open(directory/'submod'/'submod4.py') as f:
        assert f.read() == code_submod4_fixed
    with open(directory/'submod_recursive'/'submod2.py') as f:
        assert f.read() == code_submod_recursive_submod2_fixed
    with open(directory/'mod_bad.py') as f:
        assert f.read() == code_bad_syntax
    with open(directory/'mod_unfixable.py') as f:
        assert f.read() == code_mod_unfixable

    # Test error on nonexistent file
    p = subprocess.run([sys.executable, '-m', 'removestar', directory/'notarealfile.py'],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       encoding='utf-8')
    assert p.stderr == f'Error: {directory}/notarealfile.py: no such file or directory\n'
    assert p.stdout == ''

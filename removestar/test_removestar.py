from pyflakes.checker import Checker

import ast

from .removestar import names_to_replace, star_imports


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

def test_names_to_replace():
    names = names_to_replace(Checker(ast.parse(code_mod4)))
    assert names == ['a', 'b', 'c', 'd']

    for code in [code_mod1, code_mod2, code_mod3]:
        names = names_to_replace(Checker(ast.parse(code)))
        assert names == []

def test_star_imports():
    stars = star_imports(Checker(ast.parse(code_mod4)))
    assert stars == ['.mod1', '.mod2']

    for code in [code_mod1, code_mod2, code_mod3]:
        stars = star_imports(Checker(ast.parse(code)))
        assert stars == []

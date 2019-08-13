try:
    import pytest_doctestplus.plugin
    pytest_doctestplus
except ImportError:
    raise ImportError("Install pytest-doctestplus to run the removestar tests")

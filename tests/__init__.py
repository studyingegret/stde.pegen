import os
from typing import Any
from test.support import load_package_tests #type:ignore[import-not-found]


# Load all tests in package
def load_tests(*args: Any) -> Any:
    return load_package_tests(os.path.dirname(__file__), *args)

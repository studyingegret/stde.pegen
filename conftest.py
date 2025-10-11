import os, pytest


def pytest_configure(config):
    source_root = os.path.dirname(os.path.abspath(__file__))
    if os.getcwd() != source_root:
        os.chdir(source_root)

def pytest_addoption(parser):
    parser.addoption("--cache-v2-python-parser", choices=["true", "false"],
                     type=lambda x: x == "true",
                     default=True,
                     dest="cache_v2_python_parser",
                     help="Cache the v2 Python parser (upon successful generation) to save time "
                          "(default true)")

@pytest.fixture(scope="session")
def cache_v2_python_parser(pytestconfig):
    return pytestconfig.option.cache_v2_python_parser
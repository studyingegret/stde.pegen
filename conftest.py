import os


def pytest_configure(config):
    source_root = os.path.dirname(os.path.abspath(__file__))
    if os.getcwd() != source_root:
        os.chdir(source_root)

def pytest_addoption(parser):
    parser.addoption("--cache-v2-python-parser", action="store_false",
                     help="Cache the v2 Python parser to save time")
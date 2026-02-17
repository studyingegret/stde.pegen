import os, pytest


def pytest_configure(config):
    source_root = os.path.dirname(os.path.abspath(__file__))
    if os.getcwd() != source_root:
        os.chdir(source_root)

def pytest_addoption(parser):
    parser.addoption("--v2-python-parser-cache",
                     choices=["true", "false"],
                     type=lambda x: x == "true",
                     default=True,
                     dest="cache_v2_python_parser",
                     help="Cache the v2 Python parser (upon successful generation) to save time "
                          "(default true)")
    parser.addoption("--v2-python-parser-verbose-tokenizer",
                     action="store_true",
                     default=False,
                     dest="v2_python_parser_verbose_tokenizer",
                     help="Enable verbose tokenizer output during v2 Python parser tests")
    parser.addoption("--v2-python-parser-no-verbose-parser",
                     action="store_false",
                     default=True,
                     dest="v2_python_parser_verbose_parser",
                     help="Disable verbose parser output during v2 Python parser tests")
    parser.addoption("--v2-python-parser-diff-ncontext",
                     type=int,
                     default=3,
                     dest="v2_python_parser_diff_ncontext",
                     help="Number of context lines to show in unified diff when v2 Python parser tests fail (default 3)")
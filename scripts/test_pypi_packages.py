#!/usr/bin/env python3.8

import argparse
import os
import glob
import tarfile
import zipfile
import shutil
import sys

from typing import Generator, Any, TYPE_CHECKING

sys.path.insert(0, ".")
from stde.pegen import build
from scripts import test_parse_directory

argparser = argparse.ArgumentParser(
    prog="test_pypi_packages",
    description="Helper program to test parsing PyPI packages",
)
argparser.add_argument(
    "-t", "--tree", action="count", help="Compare parse tree to official AST", default=0
)


def get_packages() -> Generator[str, None, None]:
    yield from glob.iglob("./data/pypi/*.tar.gz")
    yield from glob.iglob("./data/pypi/*.zip")
    yield from glob.iglob("./data/pypi/*.tgz")


def extract_files(filename: str) -> None:
    savedir = os.path.join("data", "pypi")
    if tarfile.is_tarfile(filename):
        tarfile.open(filename).extractall(savedir)
    elif zipfile.is_zipfile(filename):
        zipfile.ZipFile(filename).extractall(savedir)
    else:
        raise ValueError(f"Could not identify type of compressed file {filename}")


def find_dirname(package_name: str) -> str:
    for name in os.listdir(os.path.join("data", "pypi")):
        full_path = os.path.join("data", "pypi", name)
        if os.path.isdir(full_path) and name in package_name:
            return full_path
    if TYPE_CHECKING: assert False


def run_tests(dirname: str, tree: int) -> int:
    return test_parse_directory.parse_directory(
        dirname,
        "data/python.gram",
        verbose=False,
        excluded_files=[
            "*/failset/*",
            "*/failset/**",
            "*/failset/**/*",
            "*/test2to3/*",
            "*/test2to3/**/*",
            "*/bad*",
            "*/lib2to3/tests/data/*",
        ],
        skip_actions=False,
        tree_arg=tree,
        short=True,
        parser=None,
    )


def main() -> None:
    args = argparser.parse_args()
    tree = args.tree

    for package in get_packages():
        print(f"Extracting files from {package}... ", end="")
        try:
            extract_files(package)
            print("Done")
        except ValueError as e:
            print(e)
            continue

        print(f"Trying to parse all python files ... ")
        dirname = find_dirname(package)
        status = run_tests(dirname, tree)
        if status == 0:
            print("Done")
            shutil.rmtree(dirname)
        else:
            print(f"Failed to parse {dirname}")


if __name__ == "__main__":
    main()

# Contributing to this Pegen fork

[TODO: Outdated]

This project welcomes contributions in the form of Pull Requests.
For clear bug-fixes / typos etc. just submit a PR.
For new features or if there is any doubt in how to fix a bug, you might want
to open an issue prior to starting work to discuss it first.

## Before getting started

To ensure your workflow:

- You need to install black, flake8, mypy, pytest and tox.

  ```
  python -m pip -r dev_requirements.txt
  ```

  Note: pep517.build is present in Makefile but I cannot find usage of its belonging task.
- make is required. [A version of make for Windows](https://github.com/mbuilov/gnumake-windows).
- (Optional) [TODO: This item needs rewriting] For better typings for module `build`:
  Add `src/_typings_not_mypy` to your IDE's extra import paths (or whatever it is called).
  - If it can understand these type hints, ask it to ignore `src/_typings_mypy` and `src/pegen/build_types.py` (2).
  - If it cannot understand them, ask it to ignore `src/_typings_not_mypy` and `src/pegen/build_types.py` and not ignore `src/_typings_mypy` (3).

  For example, in VS Code this is done by "Python › Analysis: Extra Paths" and "Python › Analysis: Exclude".

  Note: If your IDE is configured to use Pyright, you might not need to do these
  because I [configured](https://github.com/microsoft/pyright/blob/main/docs/configuration.md) so
  in `pyproject.toml`.
- In case you are not used to it, this fork stores tool options in `pyproject.toml`.
  If you change an option, and consider it valuable to make the change persist,
  put it there.

  Note: flake8 options cannot be put in `pyproject.toml`.

## Known possibly broken aspects
- Support for different versions of Python. I can pass the tests with 3.13.2 but didn't
  test any other versions.
- 

## Installation type stubs
[TODO:?]

## Generating the grammar parser
Pegen's grammar parser (`grammar_parser.py`) is self-generated from `metagrammar.gram`.

```
python -m pegen src/pegen/metagrammar.gram -o src/pegen/grammar_parser.py
```

Add `-v` flag for verbose output and full traceback on errors.

The make `regen-metaparser` task does a similar thing.

## All checks (?)

```
python -m tox
```

This will check that all the tests pass but also will make several checks on the code style
and type annotations of the package. It also does some things I don't really understand.

## Test

To run the test suite:

```
python -m pytest tests
# Or
make check  # More verbose
```

New code should ideally have tests and not break existing tests.

## Test with coverage report

```
make pycoverage2
```

Or use the command:

```
python -m pytest --color=yes --cov=$(python -c "import pegen, os; print(os.path.dirname(pegen.__file__))") --cov-branch --cov-report=term --cov-report=html tests
```

There is also a `pycoverage` make task, but I don't know why it uses `--cov-append`.

## Type Checking

`pegen` uses type annotations throughout, and uses `mypy` to do the checking.
Run the following to type check all code:

```
python -m mypy
```

You can use [mypy's daemon server](https://mypy.readthedocs.io/en/stable/mypy_daemon.html) to
save time and computation over multiple runs:

```
dmypy run
```

> dmypy is used in this fork's tox.ini and Makefile.

mypy options are stored in `pyproject.toml`.

To only check some files, add the paths/filenames on the command line:
```
python -m mypy src
# Or
dmypy run -- src
```

## Lints

Checks code style with `black` and `flake8` (in folders `src`, `tests` only)
and type checks with `mypy`.

```
python -m tox -e lint
# Or
make lint
```

Please add type annotations for all new code.

## Code Formatting

`pegen` uses [`black`](https://github.com/psf/black) for code formatting.
I recommend setting up black in your editor to format on save.

[XXX: But flake8 is also present in Makefile?]

To run black from the command line, use `make format` to format and write to the files.

# Contributing to this fork of Pegen

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
- make is required. [A version of make for Windows](https://github.com/mbuilov/gnumake-windows).
- Add `src/_typings_not_mypy` to your IDE's extra import paths (or whatever it is called),
  to get better type hints for module build (1). If it can understand these type hints,
  ask it to ignore `src/_typings_mypy` (2). Otherwise revert (1) and (2).

  For example, in VS Code this is done by
  - adding `src/_typings_not_mypy` to "Python › Analysis: Extra Paths" (1)
  - adding `src/_typings_mypy` to "Python › Analysis: Exclude" (2)

  or, equivalently, adding the JSON key & value to settings.json:
  ```
  "python.analysis.extraPaths": ["src/_typings_not_mypy"], // (1)
  "python.analysis.exclude": ["src/pegen/build_types.py"], // (2)
  ```

  Note: If your IDE is configured to use Pyright, you might not need to do this
  because I [configured](https://github.com/microsoft/pyright/blob/main/docs/configuration.md) so
  in `pyproject.toml`.
- In case you are not used to it, this fork stores tool options in `pyproject.toml`.
  If you change an option, and consider it valuable to make the change persist,
  put it there.

## Installation type stubs
[XXX:?]

## All checks (?)

```
python -m tox
```

This will check that all the tests pass but also will make several checks on the code style
and type annotations of the package. It also does some things I don't really understand.

## Tests

To run the test suite:

```
python -m pytest tests
# Or
make check
```

New code should ideally have tests and not break existing tests.

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

[XXX: What about flake8?]

To run black from the command line, use `make format` to format and write to the files.

# Contributing to Pegen

This project welcomes contributions in the form of Pull Requests.
For clear bug-fixes / typos etc. just submit a PR.
For new features or if there is any doubt in how to fix a bug, you might want
to open an issue prior to starting work to discuss it first.

### Dev notes

Please exclude `src/pegen/build_types.py` from analysis in your IDE, for example
in VS Code:

```json
"python.analysis.exclude": ["src/pegen/build_types.py"]
```

### Tests

`pegen` uses [tox](https://pypi.org/project/tox/) to run the test suite. Make sure
you have `tox` installed and then you can run the tests with the following command:

```
python -m tox
```

This will check that all the tests pass but also will make several checks on the code style
and type annotations of the package.

Additionally, if you want to just run the tests and you have `pytest` installed, you can run
the tests directly by running:

```
python -m pytest tests
```

Or if you have `make`, run the following:

```
make check
```

New code should ideally have tests and not break existing tests.

### Type Checking

`pegen` uses type annotations throughout, and uses `mypy` to do the checking.
Run the following to type check `pegen` (excludes test code):

```
python -m mypy src/pegen --follow-imports=normal --always-true RUNNING_MYPY --exclude ".*not_mypy.*"
```

You may find [mypy's daemon server](https://mypy.readthedocs.io/en/stable/mypy_daemon.html) useful,
which saves time over multiple runs.

```
dmypy run -- src/pegen --follow-imports=normal --always-true RUNNING_MYPY --exclude ".*not_mypy.*"
```

dmypy is used in this fork by default.

> This fork adds some flags for mypy; they are in `lint` task in Makefile.

### All lints

Check code style with `black` and `flake8`. Type check with `mypy` (files in `src` only).

```
python -m tox -e lint
```

Or if you have `make` and `mypy` is installed in your current Python environment:

```
make lint
```

Please add type annotations for all new code.

### Code Formatting

`pegen` uses [`black`](https://github.com/psf/black) for code formatting.
I recommend setting up black in your editor to format on save.

[XXX: What about flake8?]

To run black from the command line, use `make format` to format and write to the files.

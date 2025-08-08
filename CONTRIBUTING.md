# Contributing to this Pegen fork

[TODO: Outdated]

This project welcomes contributions in the form of Pull Requests.
For clear bug-fixes / typos etc. just submit a PR.
For new features or if there is any doubt in how to fix a bug, you might want
to open an issue prior to starting work to discuss it first.

## Before getting started

To ensure your workflow:

- You need mypy and pytest.

  ```
  python -m pip mypy pytest
  ```

  Some old workflow files also use black and flake8, but I don't use them currently.

  ```
  python -m pip -r old_dev_requirements.txt
  ```

  Note: pep517.build is present in Makefile but the task that uses it is not used.
- If you want to change the documentation, install the requirements
  in the `docs` extras in pyproject.toml:

  ```
  pip install sphinx sphinx-copybutton furo
  ```
- make is required. [A version of make for Windows](https://github.com/mbuilov/gnumake-windows).
- In case you are not used to it, this fork stores tool options in `pyproject.toml`.
  If you change an option, and consider it valuable to make the change persist,
  put it there.

  Note: flake8 options cannot be put in `pyproject.toml`.

## Known possibly broken aspects
- Support for different versions of Python. I can pass the tests with 3.13.2 but didn't
  test any other versions.
- Workflow files are inconsistent with what I'm using. [TODO]
- ...

## PR requirements
Requirements for all PRs:
- Tests must all pass.
- PRs must add/adapt tests to cover all features that it provides/changes etc.
  This criteria is soft-judged: usually one test case for each feature is a minimum,
  but depending on the situation, I may accept PRs with near-complete test coverage.
  Use your common sense for this judgement.

  A reason for this is that tests make it ultimately clear what
  your feature/change is supposed to look like in usage.

Requirements for a PR to be merged into branch `main`:
- Type check must pass.
- Design that is okay in its own right but doesn't match my ideas of the library may be rejected to enter branch `main`.

If these requirements aren't satisfied, it is still okay to merge
the PR into a branch *other than* `main`. e.g. If you're not good at static typing,
I may be willing to do these (depending on the time I have, of course).

So I recommend starting a PR against branch `main`, then if I don't approve of
merging into `main`, I can create a new branch for you to re-submit the PR. (?)

## Building documentation

Generate HTML under directory `docbuild`:

```
make -C docs
```

The index file will be `docbuild/html/index.html`. If you're using Windows,
you can open it with `make -C docs open` (I don't know a Unix equivalent).

Use `make -C docs clean` to clean previously built files.

## Generating the grammar parser from metagrammar
Since the generated file will become broken if generation breaks halfway
(e.g. the grammar parser itself has a bug),
I recommend backing up `grammar_parser[_v2].py` before generating the grammar parser.
There is currently no automated utility to do that [TODO].

When changing the grammar generator or metagrammar, two generations of the grammar parser
are required to make sure the metagrammar & grammar generator are working
(because the generated parser is exercised starting from the second generation).

## Generating the v1 grammar parser

Pegen's grammar parser (`grammar_parser.py`) is self-generated from `metagrammar.gram`.

```
python -m pegen src/pegen/metagrammar.gram -o src/pegen/grammar_parser.py
```

Add `-v` flag for verbose output and full traceback on errors.

The make `regen-metaparser` task does a similar thing.

## Generating the v2 grammar parser

```
python -m pegen src/pegen/metagrammar_v2.gram -v2 -o src/pegen/grammar_parser_v2.py
```

No make task for it yet.

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
# Windows
dmypy start & dmypy run
# Linux
dmypy start & dmypy run
```

> dmypy is used in this fork's tox.ini and Makefile.

mypy options are stored in `pyproject.toml`.

To only check some files, add the paths/filenames on the command line:
```
python -m mypy src
# Or
dmypy run -- src
```

## Lints [Note: Not used]

Checks code style with `black` and `flake8` (in folders `src`, `tests` only)
and type checks with `mypy`.

```
python -m tox -e lint
# Or
make lint
```

Please add type annotations for all new code.

## Code Formatting [Note: Not used]

`pegen` uses [`black`](https://github.com/psf/black) for code formatting.
I recommend setting up black in your editor to format on save.

[XXX: But flake8 is also present in Makefile?]

To run black from the command line, use `make format` to format and write to the files.

## If one day you find this project dusted

Abandoned projects can be forked but forks may not get the same attention.
If this project's last commit time is < 6 months ago, feel free to
open an issue to point to an alternative project/fork.
Contributing to this Pegen fork
===============================

This project welcomes contributions in the form of Pull Requests.
For clear bug-fixes / typos etc. just submit a PR.

If there is any doubt in how to fix a bug etc., feel free to open an issue to discuss it.

Getting started
---------------

To ensure your workflow:

- You need mypy, pytest and rtoml.

  ```
  python -m pip install mypy pytest rtoml
  ```

  Some old workflow files also use black and flake8, but I don't use them currently.

  ```
  python -m pip -r old_dev_requirements.txt
  ```

  Note: pep517.build is present in Makefile but the task that uses it is not used.
- Requirements for building documentation are the `docs` extras in pyproject.toml:

  ```
  python -m pip install sphinx sphinx-copybutton furo
  ```
- make is required. [A version of make for Windows](https://github.com/mbuilov/gnumake-windows).
- In case you are not used to it, this fork stores tool options in `pyproject.toml`.
  If you change an option, and consider it valuable to make the change persist,
  put it there.

  Note: flake8 options cannot be put in `pyproject.toml`.

If you use VS Code, put vscode-tasks.json into .vscode/tasks.json,
and your VS Code will be equipped with tasks.

AI policy
---------
AI contributions are allowed provided that you understand the AI output and there is always a human in the loop. Contributions completely consisting of AI output without human review or being adjusted as needed, or that you cannot explain why AI wrote X and not Y (and why it should (not) be X/Y), are discouraged and may result in a ban. A notice that AI is used is okay but not neccessary; please note so in PR comments instead of in code. (Only big directions are stated here, since this project has yet to see contributions to learn from and refine these rules)

Known possibly broken aspects
-----------------------------
- Support for different versions of Python. I can pass the tests with 3.13.2 but didn't
  test any other versions.
- Workflow files are inconsistent with what I'm using. [TODO]
- ...

PR requirements
---------------
Requirements for all PRs:
- Tests must all pass.
- PRs must add/adapt tests to cover everything it changes.
  This criteria is soft-judged: usually one test case for each feature is a minimum (??),
  but depending on the situation, I may accept PRs with slightly less test coverage.
  Use your common sense for this judgement.

  A reason for this is that tests make it ultimately clear what
  your PR is supposed to look like in usage.
- Type check must pass. If you're not good at typing, I can help with it.

Requirements for a PR to be merged into branch `main`.
If these requirements aren't satisfied, it is still possible to merge
the PR into a branch other than `main`.
- If present, explain significant design changes from original code's:
  why you decided not to follow the original design;
  how the original design is blocking you / makes you dislike it; etc.

  Such design needs to be approved by me to enter branch `main`.

So I recommend starting a PR against branch `main`, then if I don't approve of
merging into `main`, I can create or select a new branch for you to re-submit the PR. (?)

Building documentation
----------------------
Install the documentation build requirements mentioned above.

Generates HTML under directory `docbuild`:

```
make -C docs
```

The index file will be `docbuild/html/index.html`. If you're using Windows,
you can open it with `make -C docs open` (I don't know a Unix equivalent).

Use `make -C docs clean` to clean previously built files.

Generating the grammar parser from metagrammar
----------------------------------------------
Since the generated file will become broken if generation breaks halfway
(e.g. the grammar parser itself has a bug),
we now have a utility script that automatically backs up the existing parser
before generation and restores it if generation fails.

When changing the grammar generator or metagrammar, two generations of the grammar parser
are required to make sure the metagrammar & grammar generator are working
(because the generated parser is exercised starting from the second generation).
The utility script does two generations by default
and the exact number can be changed with `--generations`.

### Generating parsers with the utility script

Use the `generate_parser.py` script for legacy and v2 parser generation:

```
python scripts/generate_parser.py legacy [--verbose] [--generations N]
python scripts/generate_parser.py v2 [--verbose] [--generations N]
```

Options:
- `--verbose`/`-v`: Increase verbosity (use `-v`, `-vv`, etc.)
- `--generations`/`-g`: Number of generations to run (default: 2)

Examples:
```
# Generate legacy parser with default settings
python scripts/generate_parser.py --version legacy

# Generate v2 parser with maximum verbosity and 2 generations
python scripts/generate_parser.py --version v2 -vv -g 2
```

The script will:
1. Create a backup of the existing parser file
2. Run the specified number of generations
3. Restore the backup if any generation fails

### Manual generation (deprecated)

Pegen's grammar parser (`grammar_parser.py`) is self-generated from `metagrammar.gram`.

Add `-v` flag for verbose output and full traceback on errors.

Legacy grammar parser: `make legacy-grammar-parser`

v2 grammar parser: `make v2-grammar-parser`

Test
----
To run the test suite:

```
python -m pytest tests
# Or
make check  # More verbose
```

New code should ideally have tests and not break existing tests.

Test with coverage report
-------------------------
```
make pycoverage2
```

Or use the command:

```
python -m pytest --color=yes --cov=$(python -c "import stde.pegen, os; print(os.path.dirname(stde.pegen.__file__))") --cov-branch --cov-report=term --cov-report=html tests
```

There is also a `pycoverage` make task, but I don't know why it uses `--cov-append`.

Type checking
-------------
`ResultFlag.NO_VALUE` and `ResultFlag.FAILURE` are always False.
Because the v2 grammar parser uses this fact, if you just run mypy ordinarily
it will give a lot of false positives like

```
error: Argument 2 to "ExternDecl" has incompatible type "str | Literal[ResultFlag.NO_MATCH] | None"; expected "str | None"
```

for this generated parser code:

```python
if (
    # Code matching `ann=annotation?`
    (r_ann := (_temp if (_temp := (self.annotation())) is not FAILURE else NO_MATCH)) is not FAILURE
    and
    ...
):
    ann = r_ann
    return ExternDecl(name.string, ann or None) # Error on this line
```

because `Literal[ResultFlag.NO_MATCH]` is considered possibly True by mypy,
and `ann` is of type `str | Literal[ResultFlag.NO_MATCH]`
so `ann or None` is considered to possibly be `Literal[ResultFlag.NO_MATCH]`.
Actually, `ann or None` will never be of type `Literal[ResultFlag.NO_MATCH]`
because if `ann` is `NO_MATCH` then `or` selects `None`. However, I don't know a way
to explain this fact to type checkers.

The typhical solution is adding `#type:ignore` but it is not convenient to do so
in v2 grammar parser due to the way it is generated.

Therefore, I designed `run_mypy.py`. It runs mypy and filters out errors containing
`FAILURE` and `NO_MATCH` that happen in v2 grammar parser, because they are likely
false positives.

Recommended method:

- Run with filtering v2 grammar parser enabled:
  ```
  python run_mypy.py
  ```
- Optionally, then run without filtering v2 grammar parser,
  to check for erroneously filtered errors, but this requires manual checking to tell
  which are false positives, and can be tiring, which is why it's optional:
  ```
  python run_mypy.py --third-only
  ```
- If the script outputs errors that should be filtered out (mentioned above), try
  running `dmypy stop` or `dmypy kill` and try again.

Please add type annotations for all new code.

All checks (?)
--------------

<details>
  <summary>Legacy, not used (click to expand)</summary>


```
python -m tox
```

This will check that all the tests pass but also will make several checks on the code style
and type annotations of the package. It also does some things I don't really understand.

</details>

Lints
-----

<details>
  <summary>Legacy, not used (click to expand)</summary>

Checks code style with `black` and `flake8` (in folders `src`, `tests` only)
and type checks with `mypy`.

```
python -m tox -e lint
# Or
make lint
```

</details>

Code Formatting
---------------

<details>
  <summary>Legacy, not used (click to expand)</summary>

`stde.pegen` uses [`black`](https://github.com/psf/black) for code formatting.
I recommend setting up black in your editor to format on save.

[XXX: But flake8 is also present in Makefile?]

To run black from the command line, use `make format` to format and write to the files.

</details>

Doc formatting
--------------
### Headings
Use the following characters for headings from high-level to low-level:
- `=`
- `-`
- `~`
- `*`
- (lower levels aren't used yet, so no style rule for them yet)

If one day you find this project dusted
---------------------------------------

Abandoned projects can be forked but forks may not get the same attention.
If this project's last commit time is >6 months ago, feel free to
open an issue to point to an alternative project/fork.
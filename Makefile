PYTHON ?= python
PIP_INSTALL=$(PYTHON) -m pip install
DOCSBUILDDIR := docs/_build
HTMLDIR := $(DOCSBUILDDIR)/html

# Use this to inject arbitrary commands before the make targets (e.g. docker)
ENV :=

.PHONY: dist
dist:  ## Generate Python distribution files
	$(PYTHON) -m pep517.build .

.PHONY: install-sdist
install-sdist: dist  ## Install from source distribution
	$(ENV) $(PIP_INSTALL) $(wildcard dist/*.tar.gz)

.PHONY: install
test-install:  ## Install with test dependencies
	$(ENV) $(PIP_INSTALL) -e .[test]

.PHONY: test
check:  ## Run the test suite
	$(PYTHON) -m pytest -vvv --log-cli-level=info -s --color=yes $(PYTEST_ARGS) tests

# Note: The $(shell) call makes it compatible with editable installs
#XXX: Why use --cov-append?
.PHONY: pycoverage
pycoverage:  ## Run the test suite, with Python code coverage
	$(PYTHON) -m pytest \
		-vvv \
		--log-cli-level=info \
		-s \
		--color=yes \
		--cov=$(shell python -c "import stde.pegen, os; print(os.path.dirname(stde.pegen.__file__))") \
		--cov-config=tox.ini \
		--cov-report=term \
		--cov-append $(PYTEST_ARGS) \
		tests

# Note: The $(shell) call makes it compatible with editable installs
# Coverage configuration is in pyproject.toml
.PHONY: pycoverage2
pycoverage2:  ## Run the test suite, with Python code coverage
	$(PYTHON) -m pytest \
		--color=yes \
		--cov=$(shell python -c "import stde.pegen, os; print(os.path.dirname(stde.pegen.__file__))") \
		--cov-branch \
		--cov-report=term \
		--cov-report=html \
		$(PYTEST_ARGS) \
		tests

.PHONY: format
format: ## Format all files
	$(PYTHON) -m black src tests

.PHONY: lint black flake8 dmypy mypy
lint: black flake8 dmypy ## Lint all files
black:
	$(PYTHON) -m black --check src tests
flake8:
	$(PYTHON) -m flake8 src tests
dmypy:
	dmypy run
mypy: dmypy # Backward compatibility

.PHONY: clean
clean:  ## Clean any built/generated artifacts
	find . | grep -E '(\.o|\.so|\.gcda|\.gcno|\.gcov\.json\.gz)' | xargs rm -rf
	find . | grep -E '(__pycache__|\.pyc|\.pyo)' | xargs rm -rf

.PHONY: regen-metaparser
regen-metaparser: src/stde/pegen/metagrammar.gram src/stde/pegen/*.py # Regenerate the metaparser
	$(PYTHON) -m stde.pegen -q src/stde/pegen/metagrammar.gram -o src/stde/pegen/grammar_parser.py
	$(PYTHON) -m black src/stde/pegen/grammar_parser.py

.PHONY: docs
docs:  ## Generate documentation
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

.PHONY: gh-pages
gh-pages:  ## Publish documentation on BBGitHub Pages
	$(eval GIT_REMOTE := $(shell git remote get-url $(UPSTREAM_GIT_REMOTE)))
	$(eval COMMIT_HASH := $(shell git rev-parse HEAD))
	touch $(HTMLDIR)/.nojekyll
	@echo -n "Documentation ready, push to $(GIT_REMOTE)? [Y/n] " && read ans && [ $${ans:-Y} == Y ]
	git init $(HTMLDIR)
	GIT_DIR=$(HTMLDIR)/.git GIT_WORK_TREE=$(HTMLDIR) git add -A
	GIT_DIR=$(HTMLDIR)/.git git commit -m "Documentation for commit $(COMMIT_HASH)"
	GIT_DIR=$(HTMLDIR)/.git git push $(GIT_REMOTE) HEAD:gh-pages --force
	rm -rf $(HTMLDIR)/.git

.PHONY: help
help:  ## Print this message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

demo:
	PYTHONPATH=$(shell pwd)/src:$(PYTHONPATH) $(PYTHON) -m stde.pegen data/python.gram -o data/python_parser.py
	PYTHONPATH=$(shell pwd)/src:$(PYTHONPATH) $(PYTHON) data/python_parser.py -r tests/legacy/demo.py


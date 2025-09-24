PYTHON ?= python
PIP_INSTALL=$(PYTHON) -m pip install
ENV :=
ROOT = src/stde/pegen

.PHONY: \
	default \
	legacy-grammar-parser \
	v2-grammar-parser \
	v2-grammar-parser-vv \
	editable-install \
	test \
	test-legacy \
	test-v2 \
	test-v2-vv \
	test-with-cov \
	tox-lint \
	lint \
	test-and-mypy \
	test-v2-and-mypy \
	black \
	flake8 \
	mypy \
	mypy-no-filter \
	build-docs \
	build-docs-force \
	open-docs \
	legacy-dist \
	legacy-install-sdist \
	legacy-test-install \
	legacy-pycoverage \
	legacy-format \
	legacy-clean \
	legacy-regen-metaparser \
	legacy-help \
	legacy-demo

default: test-and-mypy

# TODO: Currently Unix-only
help:
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Modern tasks from Makefile3

legacy-grammar-parser: $(ROOT)/* $(ROOT)/legacy/*
	$(PYTHON) -m stde.pegen $(ROOT)/legacy/metagrammar.gram -o $(ROOT)/legacy/grammar_parser.py -v

v2-grammar-parser: $(ROOT)/* $(ROOT)/v2/*
	$(PYTHON) -m stde.pegen $(ROOT)/v2/metagrammar.gram -v2 -o $(ROOT)/v2/grammar_parser.py -v

v2-grammar-parser-vv: $(ROOT)/* $(ROOT)/v2/*
	$(PYTHON) -m stde.pegen $(ROOT)/v2/metagrammar.gram -v2 -o $(ROOT)/v2/grammar_parser.py -vv

editably-install:
	pip install -e . -C editable_mode=strict

test: legacy-grammar-parser v2-grammar-parser
	$(PYTHON) -m pytest tests

test-legacy: legacy-grammar-parser
	$(PYTHON) -m pytest tests -vv

test-v2: v2-grammar-parser
	$(PYTHON) -m pytest tests -k v2

test-v2-vv: v2-grammar-parser-vv
	$(PYTHON) -m pytest tests -k v2 -vv

test-with-cov: legacy-grammar-parser v2-grammar-parser
	$(PYTHON) -m pytest \
		--color=yes \
		--cov=$(shell python -c "import stde.pegen, os; print(os.path.dirname(stde.pegen.__file__))") \
		--cov-branch \
		--cov-report=term \
		--cov-report=html \
		$(PYTEST_ARGS) \
		tests

black:
	$(PYTHON) -m black --check src tests

flake8:
	$(PYTHON) -m flake8 src tests

mypy:
	$(PYTHON) run_mypy.py

mypy-no-filter:
	$(PYTHON) run_mypy.py --third-only

test-and-mypy: test mypy

test-v2-and-mypy: test-v2 mypy

lint: black flake8 mypy

# Legacy tasks, might be cleaned in the future

legacy-tox-lint:
	$(PYTHON) -m tox -e lint

legacy-dist:
	$(PYTHON) -m pep517.build .

legacy-install-sdist: legacy-dist
	$(ENV) $(PIP_INSTALL) $(wildcard dist/*.tar.gz)

legacy-test-install:
	$(ENV) $(PIP_INSTALL) -e .[test]

# Note: Legacy pycoverage uses different flags than test-with-cov
legacy-pycoverage:
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

legacy-format:
	$(PYTHON) -m black src tests

legacy-clean:
	find . | grep -E '(\.o|\.so|\.gcda|\.gcno|\.gcov\.json\.gz)' | xargs rm -rf
	find . | grep -E '(__pycache__|\.pyc|\.pyo)' | xargs rm -rf

legacy-regen-metaparser: src/stde/pegen/metagrammar.gram src/stde/pegen/*.py
	$(PYTHON) -m stde.pegen -q src/stde/pegen/metagrammar.gram -o src/stde/pegen/grammar_parser.py
	$(PYTHON) -m black src/stde/pegen/grammar_parser.py

legacy-demo:
	PYTHONPATH=$(shell pwd)/src:$(PYTHONPATH) $(PYTHON) -m stde.pegen data/python.gram -o data/python_parser.py
	PYTHONPATH=$(shell pwd)/src:$(PYTHONPATH) $(PYTHON) data/python_parser.py -r tests/legacy/demo.py

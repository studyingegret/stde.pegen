# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = ../docbuild

RSTFILES = $(shell python -c "import glob, os; print(*glob.iglob(os.path.join(os.getcwd(), '**/*.rst'), recursive=True))")
DEPENDENCIES = subexpressions.svg grammar_1.svg

.PHONY: help Makefile html open default dependencies

# The first rule gets run when given no task name.
default: html

subexpressions.svg: subexpressions.gv
	dot -Tsvg subexpressions.gv > subexpressions.svg

grammar_1.svg: grammar_1.txt
	python ../scripts/grammar_grapher_2.py grammar_1.txt | dot -Tsvg > grammar_1.svg

html: $(BUILDDIR)/html/index.html

# Use $(BUILDDIR)/html/index.html's timestamp to decide if HTML pages are outdated
$(BUILDDIR)/html/index.html: $(DEPENDENCIES) $(RSTFILES)
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)
	python -c "import os; os.utime('$(BUILDDIR)/html/index.html', None)"

# Put it first so that "make" without argument is like "make help".
# ↑ Nope
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

open: # Only tested on Windows
	cmd /c start ../docbuild/html/index.html
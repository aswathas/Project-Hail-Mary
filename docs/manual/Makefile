# ChainSentinel manual build
#
# Usage:
#   make all          build all 7 .docx files
#   make d1..d7       build a single document
#   make diagrams     render Mermaid sources to PNG/SVG
#   make catalogs     regenerate signal/pattern/derived/ES catalog tables
#   make verify       run code -> doc coverage check
#   make clean        delete build/

SHELL      := /bin/bash
SRC        := src
BUILD      := build
DIAGRAMS   := diagrams
SCRIPTS    := scripts
PANDOC     := pandoc
PANDOC_OPTS:= --reference-doc=pandoc/reference.docx --resource-path=. --toc --toc-depth=3

DOCS := d1 d2 d3 d4 d5 d6 d7

# Map IDs to full names
NAME_d1 := ChainSentinel-D1-Executive-Overview
NAME_d2 := ChainSentinel-D2-Analyst-Handbook
NAME_d3 := ChainSentinel-D3-Architecture
NAME_d4 := ChainSentinel-D4-Detection-Reference
NAME_d5 := ChainSentinel-D5-Developer-Guide
NAME_d6 := ChainSentinel-D6-Operations-Guide
NAME_d7 := ChainSentinel-D7-Simulation-Guide

# Default target
.PHONY: all
all: diagrams catalogs $(DOCS)

# Per-document targets — uses scripts/build_docx.sh which pre-expands {{< include >}}
.PHONY: $(DOCS)
define BUILD_RULE
$(1): diagrams catalogs
	@bash $(SCRIPTS)/build_docx.sh $(1) $(NAME_$(1))
endef
$(foreach d,$(DOCS),$(eval $(call BUILD_RULE,$(d))))

# Diagrams
.PHONY: diagrams
diagrams:
	@bash $(SCRIPTS)/render_diagrams.sh

# Catalog generators
.PHONY: catalogs
catalogs:
	@python3 $(SCRIPTS)/generate_catalog_tables.py

# Coverage verification
.PHONY: verify
verify:
	@python3 $(SCRIPTS)/verify_coverage.py

.PHONY: clean
clean:
	@rm -rf $(BUILD)/*.docx
	@echo "Cleaned $(BUILD)/"

.PHONY: help
help:
	@grep -E '^\.PHONY' Makefile | sed 's/.PHONY: //'

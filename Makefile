.PHONY: help venv setup check ratecheck offline data test lint cost docs clean

# ---------------------------------------------------------------------------
# Which Python to use, in order of preference:
#   1. the interpreter of an activated virtualenv
#   2. .venv/ in this repo, even if you forgot to activate it
#   3. `python` on PATH
#   4. `python3` on PATH
#
# Item 2 matters more than it looks. "I forgot to activate the venv" is the
# single most common setup failure in this module, and there is no reason a
# Makefile should punish you for it. Item 4 matters on macOS and most Linux
# distributions, where `python` does not exist at all -- which is exactly how
# this Makefile broke the first time someone ran it.
# ---------------------------------------------------------------------------
VENV := .venv
PYTHON := $(shell \
  if [ -n "$$VIRTUAL_ENV" ] && [ -x "$$VIRTUAL_ENV/bin/python" ]; then echo "$$VIRTUAL_ENV/bin/python"; \
  elif [ -x "$(VENV)/bin/python" ]; then echo "$(VENV)/bin/python"; \
  elif [ -x "$(VENV)/Scripts/python.exe" ]; then echo "$(VENV)/Scripts/python.exe"; \
  elif command -v python >/dev/null 2>&1; then echo python; \
  else echo python3; fi)

BOOTSTRAP := $(shell command -v python3 >/dev/null 2>&1 && echo python3 || echo python)

help:
	@echo "make setup    create .venv and install what Labs 1-2 need (~290 MB, fast)"
	@echo "make setup-full  add the retrieval stack -- needed from Lab 3 (~1.8 GB)"
	@echo "make env      create .env from the template (does not overwrite)"
	@echo "make check    verify the environment and make one live model call"
	@echo "make ratecheck measure your key's rate-limit headroom (~40 calls)"
	@echo "make offline  run the check in offline replay mode (costs nothing)"
	@echo "make data     regenerate the ticket dataset (deterministic)"
	@echo "make primer   Lab 1 Pydantic primer -- no API key, no cost"
	@echo "make tickets  print five random tickets with their gold labels"
	@echo "make test     run the unit tests"
	@echo "make lint     ruff"
	@echo "make cost     show what you have spent and what is cached"
	@echo "make docs     rebuild the syllabus, proposal, decks, and the aip reference"
	@echo "make clean    remove caches, traces, and the vector index"
	@echo ""
	@echo "using: $(PYTHON)"

venv:
	@if [ ! -x "$(VENV)/bin/python" ] && [ ! -x "$(VENV)/Scripts/python.exe" ]; then \
	  echo "creating $(VENV) with $(BOOTSTRAP)..."; \
	  $(BOOTSTRAP) -m venv $(VENV); \
	else echo "$(VENV) already exists"; fi

# Two tiers, deliberately. The full dependency set is ~1.8 GB and almost all
# of it is PyTorch, pulled in by sentence-transformers for Lab 3's local
# embeddings and reranker. Nothing before Lab 3 imports it -- the heavy imports
# in aip/ are lazy -- so making every student download it to run Lab 1 costs
# them fifteen minutes and buys nothing. `make check` says plainly what is
# missing and when they will need it.
setup: venv
	@$(MAKE) --no-print-directory _install REQS=requirements-lab1.txt TIER="Labs 1-2"

setup-full: venv
	@$(MAKE) --no-print-directory _install REQS=requirements.txt TIER="all labs"

_install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r $(REQS)
	@echo ""
	@echo "Installed $(TIER) dependencies into $(PYTHON)"
	@echo "Next: run 'make env', add your API key to .env, then 'make check'"
	@echo "You do NOT need to activate the venv for make targets -- they find it."
	@echo "To use python directly:  source $(VENV)/bin/activate"

# `.env.example` starts with a dot, so Finder and Explorer hide it by default.
# This target means nobody has to go looking for a file they cannot see.
env:
	@if [ -f .env ]; then \
	  echo ".env already exists -- not touching it."; \
	  echo "Edit it and put your key after GEMINI_API_KEY="; \
	else \
	  cp .env.example .env; \
	  echo "Created .env from the template."; \
	  echo ""; \
	  echo "Now open .env in any editor and put your key after GEMINI_API_KEY="; \
	  echo "Get a free one at https://aistudio.google.com/apikey"; \
	  echo "Then run: make check"; \
	fi

check:
	@$(PYTHON) -c "import litellm" 2>/dev/null || { \
	  echo "Dependencies are not installed in $(PYTHON)."; \
	  echo "Run:  make setup"; exit 1; }
	$(PYTHON) scripts/check_setup.py

ratecheck:
	$(PYTHON) scripts/check_rate_limit.py

offline:
	AIP_OFFLINE=1 $(PYTHON) scripts/check_setup.py

data:
	$(PYTHON) scripts/make_tickets.py

primer:
	@$(PYTHON) labs/lab1/pydantic_primer.py

tickets:
	@$(PYTHON) -c "import json,random; \
	rows=[json.loads(l) for l in open('data/eval/extraction_dev.jsonl')]; \
	[print('='*70,'\n',r['expected'],'\n','-'*70,'\n',r['input'],sep='') \
	 for r in random.sample(rows,5)]"

test:
	$(PYTHON) -m pytest tests/ -q

lint:
	$(PYTHON) -m ruff check aip/ labs/ scripts/ tests/

cost:
	@$(PYTHON) -c "from aip import cache; from aip.cost import global_budget; \
	print('cached:', cache.stats()); print(global_budget().report())"

docs:
	$(PYTHON) -m pip install -q python-docx python-pptx markdown
	$(PYTHON) scripts/build_syllabus_docx.py
	$(PYTHON) scripts/build_proposal_html.py
	$(PYTHON) scripts/build_decks.py
	$(PYTHON) scripts/build_html_decks.py
	$(PYTHON) scripts/build_aip_docs.py

clean:
	rm -rf .aip_traces .chroma .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
	@echo "kept .aip_cache -- delete it by hand if you really mean to re-pay"

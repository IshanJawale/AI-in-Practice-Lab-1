.PHONY: help venv setup check ratecheck offline data primer tickets test lint cost docs quiz clean

VENV := .venv
PYTHON := $(VENV)\Scripts\python.exe
BOOTSTRAP := python

help:
	@echo "make setup    create .venv if needed and install everything"
	@echo "make check    verify the environment and make one live model call"
	@echo "make ratecheck measure your key's rate-limit headroom (~40 calls)"
	@echo "make offline  run the check in offline replay mode (costs nothing)"
	@echo "make data     regenerate the ticket dataset (deterministic)"
	@echo "make primer   Lab 1 Pydantic primer -- no API key, no cost"
	@echo "make tickets  print five random tickets with their gold labels"
	@echo "make test     run the unit tests"
	@echo "make lint     ruff"
	@echo "make cost     show what you have spent and what is cached"
	@echo "make docs     rebuild the .docx syllabus, .html proposal, and the decks"
	@echo "make quiz     rebuild the end-of-lab quizzes (student page + instructor key)"
	@echo "make clean    remove caches, traces, and the vector index"
	@echo ""
	@echo "using: $(PYTHON)"

venv:
	@if exist "$(VENV)\Scripts\python.exe" ( \
		echo $(VENV) already exists \
	) else ( \
		echo creating $(VENV) with $(BOOTSTRAP)... && \
		$(BOOTSTRAP) -m venv $(VENV) \
	)

setup: venv
	@$(MAKE) --no-print-directory _install

_install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	@echo.
	@echo Installed into $(PYTHON)
	@echo Next: copy .env.example .env and add one API key. Then: make check
	@echo You do NOT need to activate the venv for make targets -- they find it.
	@echo To use python directly: .\.venv\Scripts\Activate.ps1

check:
	@$(PYTHON) -c "import litellm" >nul 2>&1 || ( \
		echo Dependencies are not installed in $(PYTHON). && \
		echo Run: make setup && \
		exit /b 1 \
	)
	$(PYTHON) scripts/check_setup.py

ratecheck:
	$(PYTHON) scripts/check_rate_limit.py

offline:
	@set AIP_OFFLINE=1&& $(PYTHON) scripts/check_setup.py

data:
	$(PYTHON) scripts/make_tickets.py

primer:
	@$(PYTHON) labs/lab1/pydantic_primer.py

tickets:
	@$(PYTHON) -c "import json,random; rows=[json.loads(l) for l in open('data/eval/extraction_dev.jsonl', encoding='utf-8')]; [print('='*70,'\n',r['expected'],'\n','-'*70,'\n',r['input'],sep='') for r in random.sample(rows,5)]"

test:
	$(PYTHON) -m pytest tests/ -q

lint:
	$(PYTHON) -m ruff check aip/ labs/ scripts/ tests/

cost:
	@$(PYTHON) -c "from aip import cache; from aip.cost import global_budget; print('cached:', cache.stats()); print(global_budget().report())"

docs:
	$(PYTHON) -m pip install -q python-docx python-pptx
	$(PYTHON) scripts/build_syllabus_docx.py
	$(PYTHON) scripts/build_proposal_html.py
	$(PYTHON) scripts/build_decks.py
	$(PYTHON) scripts/build_html_decks.py

quiz:
	$(PYTHON) scripts/build_quiz.py

clean:
	@if exist .aip_traces rmdir /s /q .aip_traces
	@if exist .chroma rmdir /s /q .chroma
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@if exist .ruff_cache rmdir /s /q .ruff_cache
	@powershell -NoProfile -Command "Get-ChildItem -Path . -Recurse -Directory -Filter __pycache__ -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	@echo kept .aip_cache -- delete it by hand if you really mean to re-pay
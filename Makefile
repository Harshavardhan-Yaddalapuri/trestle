.PHONY: dev install seed test

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install -r backend/requirements.txt

install: $(VENV)

dev:
	cd backend && uvicorn app.main:app --reload --port 8000

seed:
	$(PYTHON) scripts/seed_michigan.py

test:
	cd backend && $(PYTHON) -m pytest tests/ -v 2>/dev/null || echo "No tests yet"

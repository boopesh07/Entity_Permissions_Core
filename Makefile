PYTHON := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: install tests lint format run dev-db

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

tests:
	$(PYTHON) -m pytest -vv

run:
	.venv/bin/uvicorn app.main:app --reload --port 8000

migrate:
	$(PYTHON) -m alembic upgrade head

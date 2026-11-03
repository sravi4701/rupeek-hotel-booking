.PHONY: install run run-weekend test lint format

install:
	uv sync

run:
	SEED_DEMO_DATA=true uv run uvicorn app.main:app --reload

run-weekend:
	SEED_DEMO_DATA=true PRICING_STRATEGY=weekend uv run uvicorn app.main:app --reload

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy

format:
	uv run ruff check --fix .
	uv run ruff format .

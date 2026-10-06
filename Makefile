.PHONY: check fix

# Everything CI runs. Fails on any formatting, lint, type, or test problem.
check:
	uv run --locked ruff format --check
	uv run --locked ruff check
	uv run --locked ty check
	uv run --locked pytest

fix:
	uv run ruff format
	uv run ruff check --fix

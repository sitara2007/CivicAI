.PHONY: install test fix push

install:
	uv sync --extra dev

test:
	uv run python -m pytest tests/ -v

fix:
	ruff check . --fix

push: test
	git add .
	git commit -m "chore: automated commit" || true
	git push origin main

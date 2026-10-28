# AGENTS.md - Instructions for AI Coding Agents (Codex)

## Project Context
- CivicAI is a document triage pipeline with PII redaction and a hash-chained audit log.
- Tech Stack: Python 3.12, FastAPI, uv (package manager), Pytest.
- Monorepo structure: `app/` (main backend), `python-rag-service/`, `frontend/`.

## Coding Rules
1. NEVER delete code without asking.
2. All new features must include Pytest unit tests.
3. Use strict type hinting.
4. Run `uv run pytest tests/ -v` before committing.
5. Do not touch the `schema/` folder (it is being deprecated).

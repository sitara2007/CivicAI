# CivicAI

**AI workflow engine for government and public-sector document triage, classification and routing, with PII redaction and a tamper-evident audit trail.**

Designed to reduce manual document-triage effort. End-to-end latency, classification quality and audit-integrity guarantees have not been independently benchmarked.

Building the reference implementation for India DPDP Act 2023 compliance in AI pipelines. Tamper-evident audit logs for LLMs.

[![CI](https://github.com/sitara2007/CivicAI/actions/workflows/ci.yml/badge.svg)](https://github.com/sitara2007/CivicAI/actions/workflows/ci.yml)

[Live demo](https://civic-ai-nu-ten.vercel.app) · [Benchmarks](./BENCHMARKS.md) · [Security](./SECURITY.md)

---

## What it does

1. **Ingests** documents through a Go service (`cmd/ingest`), using mTLS for secure endpoints.
2. **Redacts PII** in middleware before classification; falls back to regex if Presidio is unavailable.
3. **Dispatches asynchronously** the redacted payload from the Go gateway to the Python FastAPI service.
4. **Classifies and routes** documents with the FastAPI service. LLM output is validated against strict Pydantic schemas using `instructor` to enforce valid structured output, with optional RAG retrieval.
5. **Records every state change** in a PostgreSQL hash-chained audit log, so editing a past record breaks every hash after it.

## Architecture

| Layer | Tech | Path |
|---|---|---|
| Frontend | Next.js (App Router) | `frontend/` |
| Ingestion + mTLS | Go (async gateway) | `cmd/ingest/`, `internal/middleware/` |
| Classification / routing | Python FastAPI, optional RAG, structured LLM output via `instructor` | `app/`, `python-rag-service/` |
| Database | Async SQLAlchemy + PostgreSQL. Tables (`documents`, `decisions`, `audit_logs`) are created at startup via `Base.metadata.create_all`. Alembic migrations are not set up yet. | `app/db/` |
| Evaluation | Python | `eval/` |
| Tests | pytest and Go test. Embeddings and the database are stubbed in most Python tests. | `tests/` |

Health check: `GET /health` returns `200 OK`.

## Audit trail

Each document state transition stores the hash of the previous entry:

```text
entry[n].hash = H(entry[n].payload || entry[n-1].hash)
```

Changing any past record invalidates all later hashes.

**Limitations**

- `verify()` detects edits to stored rows. It does not detect someone who recomputes and rewrites the whole chain, or deletes trailing rows, because there is no external anchor for the latest hash.
- Appends are serialized with a PostgreSQL advisory lock (`pg_advisory_xact_lock`). This has been tested with 20 parallel appends, not under sustained production load.
- The audit log proves integrity, not detection accuracy. Independent verification is on the roadmap.

## Benchmarks

Measured on an Intel i5-13420H (12 cores, WSL2), 2026-11-02. Full details and reproduce commands: [BENCHMARKS.md](./BENCHMARKS.md).

**Hash chain** (Python 3.12.14, pytest-benchmark, single-threaded)

| Operation | Median | Throughput |
|---|---|---|
| genesis_hash | 86.1 ns | 11.6 M ops/s |
| compute_prev_hash (3 keys) | 3.13 µs | 318,471 ops/s |
| compute_prev_hash (100+ elements) | 7.42 µs | 134,770 ops/s |

**Go ingest path** (Go 1.26.0)

| Benchmark | ns/op | allocs/op | Throughput |
|---|---|---|---|
| EventQueuePublish | 30.62 | 0 | 32.7 M ops/s |
| AppendEventJSON | 841.9 | 7 | 1.2 M ops/s |

**Limitations:** these are micro-benchmarks of individual components, not end-to-end request throughput. `DecodeEvent`: 4,581 ns/op median, 600 B/op, 12 allocs/op (3 runs). Outliers up to 9.6 ms were observed (GC/scheduling). No classification or RAG quality metrics have been published.

Reproduce:

```bash
uv run pytest tests/test_hash_chain_bench.py --benchmark-only --benchmark-sort=mean
go test -bench=. -benchmem -run=^$ ./cmd/ingest/...
```

## Testing and quality

CI runs `uv sync --extra dev --extra rag`, `uv run pytest -q` and `go test ./...` under Python 3.12. Pre-commit hooks are configured across the monorepo (Ruff for Python, gofmt/vet for Go, Prettier for Next.js).

Most Python tests use deterministic embedding stubs and an in-memory database repository. Two tests in `tests/test_audit_postgres.py` run against a real PostgreSQL instance: tamper detection and concurrent-append safety. The real Presidio backend is not exercised in CI, because its default analyzer needs the spaCy `en_core_web_lg` model download; CI tests the regex fallback instead.

## Run locally

### With Docker (Python API and infrastructure only)

`docker-compose.yml` starts PostgreSQL, Qdrant, Redis, the FastAPI service and the Celery worker. The Go ingestion service (`cmd/ingest`) is not in the compose file and must be run separately as a binary.

```bash
git clone https://github.com/sitara2007/CivicAI.git
cd CivicAI
cp .env.example .env     # fill in your values
docker compose up --build
```

### Without Docker

```bash
cp .env.example .env
uv sync --extra dev
uv run pytest -q         # Python tests
go build ./...           # compiles the Go ingestion service
go test ./...            # Go tests
```

To install the optional RAG dependencies as well:

```bash
uv sync --extra dev --extra rag
```

## Security

- Database TLS depends on the `DATABASE_URL` configuration; `.env.example` is for local development.
- PII redaction runs before model calls.
- LLM output is validated against a strict schema (`instructor`). This reduces malformed output; it is not a prompt-injection defense.
- Hash-chained audit log (see limitations above).
- Reporting vulnerabilities: see [SECURITY.md](./SECURITY.md).

## Status

- [x] Python pipeline (redaction, classification, audit chain)
- [x] PostgreSQL persistence for `/api/v1/process` (documents, decisions, audit log), verified manually end to end
- [x] Real-PostgreSQL tests for audit tamper detection and concurrent appends
- [x] `/api/v1/history` endpoint (pagination and status filter checked manually against PostgreSQL; DLQ-positive case and automated tests not done yet)
- [ ] CI with a PostgreSQL service
- [ ] Alembic migrations
- [x] Go service (ingestion)
- [x] End-to-end integration (Go async ingestion to Python pipeline)
- [ ] Verify Vercel and Railway deployment status
- [x] Go `DecodeEvent` microbenchmark recorded
- [ ] End-to-end throughput and latency benchmark
- [x] Review dependency alerts (pypdf security patch applied)
- [x] Enforce pre-commit hooks across the monorepo

## Related work

**Subprocess timeout test:** a Python test harness that measures OS-level subprocess startup and handles real timeout failures under concurrent load. Built to understand failure modes in high-concurrency agent environments.

## License

MIT

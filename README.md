# CivicAI

**AI workflow engine for government and public-sector document triage, classification and routing, with PII redaction and a tamper-evident audit trail.**
**Designed to reduce manual document-triage effort; end-to-end latency and audit-integrity guarantees have not been independently benchmarked.**
[![Deploy](https://github.com/sitara2007/CivicAI/actions/workflows/deploy.yml/badge.svg)](https://github.com/sitara2007/CivicAI/actions/workflows/deploy.yml)

[Live demo](https://civic-ai-gray.vercel.app) · [Benchmarks](./BENCHMARKS.md) · [Security](./SECURITY.md)

---

## What it does

1. **Ingests** documents through a Go service (`cmd/ingest`).
2. **Redacts PII** in the Python processing pipeline before classification; regex fallback is used when Presidio is unavailable.
3. **Classifies and routes** documents in the FastAPI service (`app/`) with optional RAG retrieval (`app/services/rag/`, `python-rag-service/`).
4. **Records every state change** in a hash-chained audit log, so editing a past record breaks every hash after it.

## Architecture

| Layer | Tech | Path |
|---|---|---|
| Frontend | Next.js (App Router) | `frontend/` |
| Ingestion + mTLS | Go | `cmd/ingest/`, `internal/middleware/` |
| Classification / routing | Python FastAPI with optional RAG | `app/`, `python-rag-service/` |
| Database | Async SQLAlchemy/PostgreSQL; no PostgreSQL DDL or Alembic migration scripts are checked in | `app/db/`, `alembic.ini` |
| Evaluation | Python | `eval/` |
| Tests | pytest and Go test; embeddings and database are stubbed in Python tests | `tests/` |

Health check: `GET /health` returns `200 OK`.

## Audit trail

Each document state transition stores the hash of the previous entry:

```
entry[n].hash = H(entry[n].payload || entry[n-1].hash)
```

Changing any past record invalidates all later hashes.

## Benchmarks

Measured on an Intel i5-13420H (12 cores, WSL2), 2026-11-02. Full details and reproduce commands: [BENCHMARKS.md](./BENCHMARKS.md).

**Hash chain (Python 3.12.14, pytest-benchmark, single-threaded)**

| Operation | Median | Throughput |
|---|---|---|
| genesis_hash | 86.1 ns | 11.6 M ops/s |
| compute_prev_hash (3 keys) | 3.13 µs | 318,471 ops/s |
| compute_prev_hash (100+ elements) | 7.42 µs | 134,770 ops/s |

**Go ingest path (Go 1.26.0)**

| Benchmark | ns/op | allocs/op | Throughput |
|---|---|---|---|
| EventQueuePublish | 32.68 | 0 | 30.6 M ops/s |
| AppendEventJSON | 724.3 | 7 | 1.38 M ops/s |

**Limitations:** these are micro-benchmarks of individual components, not end-to-end request throughput. `DecodeEvent`: 4,581 ns/op median, 600 B/op, 12 allocs/op (3 runs; Go 1.26.0, WSL2). Outliers up to 9.6 ms were observed (GC/scheduling).

Reproduce:

```bash
uv run pytest tests/test_hash_chain_bench.py --benchmark-only --benchmark-sort=mean
go test -bench=. -benchmem -run=^$ ./cmd/ingest/...
```

These are component performance benchmarks, not model-quality metrics. No classification or RAG quality metrics have been published.

## Testing and quality

CI runs `uv sync --extra dev --extra rag`, `uv run pytest -q`, and `go test ./...` under Python 3.12. Python tests use deterministic embedding stubs and an in-memory database repository; they do not test against PostgreSQL. The real Presidio backend is not exercised in CI because its default analyzer requires the spaCy `en_core_web_lg` model download. CI tests the regex fallback instead.

## Run locally

### With Docker (Python API & Infrastructure only - ⚠️ Unverified locally)
*Note: The `docker-compose.yml` starts PostgreSQL, Qdrant, Redis, the FastAPI service, and the Celery worker. The Go ingestion service (`cmd/ingest`) is **not** included in the compose file and must be run separately as a binary.*

```bash
git clone https://github.com/sitara2007/CivicAI.git
cd CivicAI
cp .env.example .env     # fill in your values
docker compose up --build
```

Without Docker:

```bash
cp .env.example .env
uv sync --extra dev
uv run pytest -q       # Runs Python tests

go build ./...         # Compiles the Go ingestion service
go test ./...          # Runs Go tests
```

To install the optional RAG dependencies as well:

```bash
uv sync --extra dev --extra rag
```

## Security

- Database TLS depends on the `DATABASE_URL` configuration; `.env.example` is for local development.
- PII redaction before model calls
- Hash-chained audit log
- Reporting vulnerabilities: see [SECURITY.md](./SECURITY.md)

## Status

- [x] Python Pipeline (Redaction, Classification, Audit Chain)
- [x] Go Service (Ingestion)
- [ ] **End-to-End Integration** (Go ingest currently decoupled from Python audit chain)
- [ ] Verify Vercel and Railway deployment status (not verifiable from checked-in configuration)
- [x] Go `DecodeEvent` microbenchmark recorded
- [ ] End-to-end throughput and latency benchmark
- [ ] Review dependency alerts (current status not verified)

## License

MIT

## Related Work / Utilities

- **[Real Subprocess Timeout Test](https://gist.github.com/sitara2007/c953cf129d0c191a941da453ab47477d)**: A Python-based test harness that measures OS-level subprocess startup and handles real timeout failures under concurrent loads. Built to understand failure modes in high-concurrency agent environments.

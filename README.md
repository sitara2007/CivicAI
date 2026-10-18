# CivicAI

**AI workflow engine for government and public-sector document triage, classification and routing, with PII redaction and a tamper-evident audit trail.**

[![CI](https://github.com/sitara2007/CivicAI/actions/workflows/ci.yml/badge.svg)](https://github.com/sitara2007/CivicAI/actions/workflows/ci.yml)

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

Measured on an Intel i5-13420H (12 cores, WSL2), 2026-09-28. Full details and reproduce commands: [BENCHMARKS.md](./BENCHMARKS.md).

**Hash chain (Python 3.14.4, pytest-benchmark, single-threaded)**

| Operation | Median | Throughput |
|---|---|---|
| genesis_hash | 261 ns | 2.58 M ops/s |
| compute_prev_hash (3 keys) | 4.37 µs | 116,175 ops/s |
| compute_prev_hash (100+ elements) | 10.17 µs | 74,184 ops/s |

**Go ingest path (Go 1.26.0)**

| Benchmark | ns/op | allocs/op | Throughput |
|---|---|---|---|
| EventQueuePublish | 32.68 | 0 | 30.6 M ops/s |
| AppendEventJSON | 724.3 | 7 | 1.38 M ops/s |

**Limitations:** these are micro-benchmarks of individual components, not end-to-end request throughput. `DecodeEvent` benchmark is pending a fix. Outliers up to 9.6 ms were observed (GC/scheduling).

Reproduce:

```bash
uv run pytest tests/test_hash_chain_bench.py --benchmark-only --benchmark-sort=mean
go test -bench=. -benchmem -run=^$ ./cmd/ingest/...
```

These are component performance benchmarks, not model-quality metrics. No classification or RAG quality metrics have been published.

## Testing and quality

CI runs `uv sync --extra dev` and `uv run pytest -q`. Python tests use deterministic embedding stubs and an in-memory database repository; they do not test against PostgreSQL. The real Presidio backend is not exercised in CI because its default analyzer requires the spaCy `en_core_web_lg` model download. CI tests the regex fallback instead.

## Run locally

```bash
git clone https://github.com/sitara2007/CivicAI.git
cd CivicAI
cp .env.example .env     # fill in your values
docker compose up --build
```

Without Docker:

```bash
uv sync --extra dev
uv run pytest -q
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

- [x] Ingestion, redaction, classification, audit chain
- [ ] Verify Vercel and Railway deployment status (not verifiable from checked-in configuration)
- [ ] Go `DecodeEvent` benchmark fix
- [ ] End-to-end throughput and latency benchmark
- [ ] Review dependency alerts (current status not verified)

## License

MIT

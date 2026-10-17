# CivicAI

**AI workflow engine for government and public-sector document triage, classification and routing, with PII redaction and a tamper-evident audit trail.**

[Live demo](https://civic-ai-gray.vercel.app) · [Benchmarks](./BENCHMARKS.md) · [Security](./SECURITY.md)

<!-- TODO: add architecture diagram: ![CivicAI architecture](docs/architecture.png) -->

---

## What it does

1. **Ingests** documents through a Go service (`cmd/ingest`).
2. **Redacts PII** in middleware (`internal/middleware`) before documents reach the model layer.
3. **Classifies and routes** documents with a Python RAG service (`python-rag-service`).
4. **Records every state change** in a hash-chained audit log, so editing a past record breaks every hash after it.

## Architecture

| Layer | Tech | Path |
|---|---|---|
| Frontend | [FILL: framework], deployed on Vercel | `frontend/` |
| Ingestion + PII redaction | Go | `cmd/ingest`, `internal/middleware` |
| Classification / routing | Python (RAG) | `python-rag-service/` |
| Database | PostgreSQL on Railway, `sslmode=require`, Alembic migrations | `schema/`, `alembic.ini` |
| Evaluation | Python | `eval/` |
| Tests | pytest, Go test | `tests/` |

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
pytest tests/test_hash_chain_bench.py --benchmark-only --benchmark-sort=mean
go test -bench=. -benchmem -run=^$ ./cmd/ingest/...
```

## Run locally

```bash
git clone https://github.com/sitara2007/CivicAI.git
cd CivicAI
cp .env.example .env     # fill in your values
docker compose up --build
```

Without Docker:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Security

- TLS enforced at the database driver level (`sslmode=require`)
- PII redaction before model calls
- Hash-chained audit log
- Reporting vulnerabilities: see [SECURITY.md](./SECURITY.md)

## Status

- [x] Ingestion, redaction, classification, audit chain
- [x] Deployed (Vercel + Railway)
- [ ] Go `DecodeEvent` benchmark fix
- [ ] End-to-end throughput and latency benchmark
- [ ] [FILL: next item]

## License

MIT

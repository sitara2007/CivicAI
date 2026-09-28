# CivicOs Benchmarks

## Hash-Chain Performance

**Machine:** Intel i5-13420H (12 cores, WSL2, Python 3.14.4)
**Date:** 2026-09-28
**Tool:** pytest-benchmark 5.3.0

| Benchmark | Min | Mean | Median | OPS |
|---|---|---|---|---|
| genesis_hash | 238 ns | 387 ns | 261 ns | 2.58 Mops/s |
| compute_prev_hash (small: 3 keys) | 3.98 µs | 8.61 µs | 4.37 µs | 116,175 ops/s |
| compute_prev_hash (large: 100+ elements) | 9.44 µs | 13.48 µs | 10.17 µs | 74,184 ops/s |

**Reproduce:** `pytest tests/test_hash_chain_bench.py --benchmark-only --benchmark-json=benchmarks.json --benchmark-sort=mean`

**Notes:** Outliers up to 9.6 ms observed (GC/scheduling). Single-threaded. Python-only; Go ingest path benchmark pending.

## Go Ingest Path Benchmarks

**Machine:** Intel i5-13420H, Go 1.26.0
**Date:** 2026-09-28

| Benchmark | ns/op | B/op | allocs/op | Throughput |
|---|---|---|---|---|
| BenchmarkEventQueuePublish | 32.68 | 0 | 0 | 30.6M ops/sec |
| BenchmarkAppendEventJSON | 724.3 | 152 | 7 | 1.38M ops/sec |
| BenchmarkDecodeEvent | (pending fix) | — | — | — |

**Reproduce:** `go test -bench=. -benchmem -run=^$ ./cmd/ingest/...`

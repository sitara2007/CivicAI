import hashlib
from datetime import UTC, datetime

import pytest

from app.services.audit.hash_chain import compute_prev_hash


@pytest.mark.benchmark(group="genesis")
def test_genesis_hash(benchmark):
    benchmark(hashlib.sha256, b"GENESIS")

@pytest.mark.benchmark(group="hash_chain")
def test_compute_prev_hash_small(benchmark):
    entry = {"id": "abc", "action": "INGESTED", "ts": datetime.now(UTC)}
    benchmark(compute_prev_hash, entry)

@pytest.mark.benchmark(group="hash_chain")
def test_compute_prev_hash_large(benchmark):
    entry = {
        "id": "abc",
        "action": "REDACTED",
        "ts": datetime.now(UTC),
        "metadata": {"pii_entities": list(range(100)), "tags": ["a"] * 50},
    }
    benchmark(compute_prev_hash, entry)

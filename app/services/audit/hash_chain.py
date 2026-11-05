"""Audit hash-chain helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any

GENESIS_HASH = hashlib.sha256(b"GENESIS").hexdigest()


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def compute_prev_hash(entry: Any) -> str:
    """Return a deterministic SHA-256 hash for an audit log entry."""

    payload = asdict(entry) if is_dataclass(entry) else dict(entry)
    serialized = json.dumps(
        payload, default=_json_default, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

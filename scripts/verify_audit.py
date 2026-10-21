"""Verify the local JSONL audit chain."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.services.audit.chain_store import JSONLAuditStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path("data/audit-chain.jsonl"))
    args = parser.parse_args()

    result = JSONLAuditStore(args.path).verify()
    if result.ok:
        print(f"OK entries={result.entries}")
        return 0
    print(f"FAIL entries={result.entries}: {result.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

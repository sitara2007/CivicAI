"""Local JSONL storage for the slice's hash-chained audit records."""

from __future__ import annotations

import fcntl
import hmac
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.services.audit.hash_chain import GENESIS_HASH, compute_prev_hash


class AuditChainError(Exception):
    """Raised when the audit chain cannot be safely appended."""


@dataclass(frozen=True)
class AuditEntry:
    sequence: int
    prev_hash: str
    payload: dict[str, Any]
    hash: str


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    entries: int
    message: str


class AuditStore(Protocol):
    def append(self, payload: dict[str, Any]) -> AuditEntry: ...

    def verify(self) -> VerificationResult: ...


class JSONLAuditStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def append(self, payload: dict[str, Any]) -> AuditEntry:
        serialized_payload = json.loads(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a+b") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                stream.seek(0)
                contents = stream.read()
                existing, result = _parse_chain(contents)
                if not result.ok:
                    raise AuditChainError(f"cannot append to invalid audit chain: {result.message}")

                prev_hash = existing[-1]["hash"] if existing else GENESIS_HASH
                sequence = len(existing)
                chain_data = {"prev_hash": prev_hash, "payload": serialized_payload}
                entry_hash = compute_prev_hash(chain_data)
                record = {
                    "sequence": sequence,
                    "prev_hash": prev_hash,
                    "payload": serialized_payload,
                    "hash": entry_hash,
                }
                line = json.dumps(
                    record, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode("utf-8") + b"\n"
                stream.seek(0, os.SEEK_END)
                stream.write(line)
                stream.flush()
                os.fsync(stream.fileno())
                return AuditEntry(
                    sequence=sequence,
                    prev_hash=prev_hash,
                    payload=serialized_payload,
                    hash=entry_hash,
                )
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def verify(self) -> VerificationResult:
        try:
            with self._path.open("rb") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
                try:
                    contents = stream.read()
                finally:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        except FileNotFoundError:
            return VerificationResult(ok=True, entries=0, message="empty chain")
        except OSError as exc:
            return VerificationResult(ok=False, entries=0, message=f"cannot read chain: {exc}")
        _, result = _parse_chain(contents)
        return result


def _parse_chain(contents: bytes) -> tuple[list[dict[str, Any]], VerificationResult]:
    if not contents:
        return [], VerificationResult(ok=True, entries=0, message="empty chain")

    records: list[dict[str, Any]] = []
    expected_prev_hash = GENESIS_HASH
    for line_number, line in enumerate(contents.splitlines(), start=1):
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return records, VerificationResult(
                ok=False, entries=len(records), message=f"invalid JSON at line {line_number}"
            )
        if not isinstance(record, dict):
            return records, VerificationResult(
                ok=False, entries=len(records), message=f"invalid record at line {line_number}"
            )
        if (
            set(record) != {"sequence", "prev_hash", "payload", "hash"}
            or not isinstance(record.get("sequence"), int)
            or isinstance(record.get("sequence"), bool)
            or record.get("sequence") != line_number - 1
            or record.get("prev_hash") != expected_prev_hash
            or not isinstance(record.get("payload"), dict)
            or not isinstance(record.get("hash"), str)
        ):
            return records, VerificationResult(
                ok=False, entries=len(records), message=f"broken link at line {line_number}"
            )

        expected_hash = compute_prev_hash(
            {"prev_hash": expected_prev_hash, "payload": record["payload"]}
        )
        if not hmac.compare_digest(record["hash"], expected_hash):
            return records, VerificationResult(
                ok=False, entries=len(records), message=f"hash mismatch at line {line_number}"
            )

        expected_prev_hash = expected_hash
        records.append(record)

    return records, VerificationResult(ok=True, entries=len(records), message="chain valid")


audit_store: AuditStore = JSONLAuditStore(Path("data/audit-chain.jsonl"))

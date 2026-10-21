from __future__ import annotations

import json

from app.services.audit.chain_store import JSONLAuditStore


def test_jsonl_audit_chain_appends_and_verifies(tmp_path) -> None:
    store = JSONLAuditStore(tmp_path / "audit.jsonl")

    first = store.append({"route": "Public Works", "redacted_text": "SSN <US_SSN>"})
    second = store.append({"route": "Water Utilities", "redacted_text": "Leak reported"})

    assert first.sequence == 0
    assert second.sequence == 1
    assert second.prev_hash == first.hash
    assert len(second.hash) == 64
    assert store.verify().ok
    assert store.verify().entries == 2


def test_jsonl_audit_chain_rejects_tampering(tmp_path) -> None:
    path = tmp_path / "audit.jsonl"
    store = JSONLAuditStore(path)
    store.append({"route": "Public Works"})

    record = json.loads(path.read_text(encoding="utf-8"))
    record["payload"]["route"] = "Tax Assessor"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    result = store.verify()
    assert result.ok is False
    assert result.entries == 0
    assert result.message == "hash mismatch at line 1"

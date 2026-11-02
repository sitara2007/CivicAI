# Architecture — explained in my own words

## 1. Why does AuditEvent use fixed-size byte arrays (`[24]byte`, `[128]byte`) instead of `string`?

A `string` in Go is a 16-byte header (pointer + length) pointing to heap-allocated memory. Using fixed-size arrays `[24]byte`, `[128]byte` means the struct is allocated inline without extra heap pointers. When we get an event from `sync.Pool`, the entire struct is reused with zero allocations for queueing (as seen in EventQueuePublish). The trade-off is that `decodeEvent` still does 12 allocs/op because `json.Unmarshal` allocates for the intermediate `ingestRequest` strings. However, for the hot path of moving events through the queue, the fixed arrays prevent GC pressure.

## 2. Why does decodeEvent validate BEFORE copying into the AuditEvent?

If we copied first and validated later, `copy(evt.TenantID[:], req.TenantID)` with a 30-byte input would silently write only the first 24 bytes — resulting in silent data corruption. Even though the code resets the struct with `*evt = AuditEvent{}` before copying, validating first avoids wasted CPU cycles populating a struct that will be discarded. More importantly, it ensures the caller never receives a half-populated or truncated event that could be forwarded downstream as a silent security bug.

## 3. How does the hash-chain work? What breaks if someone edits a past entry?

Each entry stores `prev_hash` = the hash of the previous entry. The current entry's hash is `entry[n].hash = sha256(entry[n].payload || entry[n].prev_hash)`.

Note: The hash-chain logic is implemented in Python (`app/services/audit/`), not in the Go ingestion service. The Go service only decodes and queues events; the Python service handles the chain.

If someone edits `entry[k].payload`, its recomputed hash no longer equals its stored hash — the chain is invalid at `k`. To hide it, the attacker would have to recompute all subsequent hashes to the end of the chain. Because this is computationally possible, the system is tamper-evident, not tamper-proof. To prevent tail truncation (deleting the last few entries), the head hash must be anchored externally.

## 4. Trade-offs — what does this design NOT do well?

**128-byte payload limit:** This limit is for metadata only (e.g., document ID, file hash). Real documents must be stored in object storage.
**Signature not verified:** `Sig` is stored as bytes but never verified against a public key. The hash chain proves sequence integrity, but not authenticity.
**Schema is fixed and inconsistent:** `[24]byte`, `[64]byte` are compiled into the struct. Also, `TenantID` and `Source` lack explicit length fields (unlike `EventTypeN`, etc.), relying on trimming which is error-prone.
**Truncated UUID Design Question:** `bench_test.go` uses a 23-character truncated UUID for `tenant_id`. A real UUID is 36 characters. The validation logic (line 265 in `cmd/ingest/main.go`) rejects anything over 24 bytes. This is a potential design mismatch that needs a decision: either expand the array limit or standardise on shorter IDs.
**Timestamp not trusted:** `TS` is wall-clock time from the writer and can be spoofed.

package main

import (
    "bytes"
    "testing"
    "time"
)

var benchPayload = []byte(`{
    "tenant_id": "550e8400-e29b-41d4-a716",
    "sequence": 42,
    "source": "webhook-gov-in",
    "timestamp": "2026-09-28T14:00:00Z",
    "event_type": "document.ingested",
    "trace_id": "abc123def456",
    "sig": "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    "payload": {"doc_id": "doc-999", "size": 4096, "mime": "application/pdf"}
}`)

func BenchmarkDecodeEvent(b *testing.B) {
    b.ReportAllocs()
    for i := 0; i < b.N; i++ {
        evt, err := decodeEvent(benchPayload, "fallback")
        if err != nil {
            b.Fatal(err)
        }
        if evt == nil {
            b.Fatal("nil event")
        }
        releaseEvent(evt)
    }
}

func BenchmarkEventQueuePublish(b *testing.B) {
    b.ReportAllocs()
    q := newEventQueue(65536)
    evt := &AuditEvent{}
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        if !q.publish(evt) {
            <-q.ch
            q.publish(evt)
        }
    }
}

func BenchmarkAppendEventJSON(b *testing.B) {
    b.ReportAllocs()
    evt := &AuditEvent{}
    evt.Sequence = 42
    evt.TS = time.Now().UnixNano()
    copy(evt.TenantID[:], "550e8400-e29b-41d4-a716")
    copy(evt.EventType[:], "document.ingested")
    evt.EventTypeN = len("document.ingested")
    var buf bytes.Buffer
    buf.Grow(512)
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        buf.Reset()
        appendEventJSON(&buf, evt)
    }
}

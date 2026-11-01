package main

import (
	"strings"
	"testing"
)

// validPayload returns a minimal valid ingestRequest JSON.
func validPayload() string {
	return `{
		"tenant_id": "t1",
		"sequence": 42,
		"source": "src",
		"timestamp": "2026-09-28T14:00:00Z",
		"event_type": "document.ingested",
		"trace_id": "tr1",
		"sig": "sha256:abc",
		"payload": {"doc_id": "d1"}
	}`
}

func TestDecodeEvent_HappyPath(t *testing.T) {
	evt, err := decodeEvent([]byte(validPayload()), "fb")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if evt == nil {
		t.Fatal("nil event")
	}
	defer releaseEvent(evt)

	if evt.TS == 0 {
		t.Error("timestamp not parsed into TS")
	}
	if !strings.HasPrefix(string(evt.TraceID[:]), "tr1") {
		t.Errorf("trace_id not stored, got %q", string(evt.TraceID[:]))
	}
	if !strings.HasPrefix(string(evt.TenantID[:]), "t1") {
		t.Errorf("tenant_id not stored, got %q", string(evt.TenantID[:]))
	}
}

func TestDecodeEvent_InvalidJSON(t *testing.T) {
	if _, err := decodeEvent([]byte(`not json`), "fb"); err == nil {
		t.Fatal("expected error for invalid JSON")
	}
}

func TestDecodeEvent_FallbackTraceID(t *testing.T) {
	payload := strings.Replace(validPayload(), `"trace_id": "tr1",`, "", 1)
	evt, err := decodeEvent([]byte(payload), "fb-trace")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	defer releaseEvent(evt)
	if !strings.HasPrefix(string(evt.TraceID[:]), "fb-trace") {
		t.Errorf("fallback trace_id not used, got %q", string(evt.TraceID[:]))
	}
}

func TestDecodeEvent_TenantIDTooLong(t *testing.T) {
	payload := strings.Replace(validPayload(), `"tenant_id": "t1"`, `"tenant_id": "`+strings.Repeat("a", 25)+`"`, 1)
	_, err := decodeEvent([]byte(payload), "fb")
	if err == nil || !strings.Contains(err.Error(), "tenant_id") {
		t.Fatalf("expected tenant_id error, got %v", err)
	}
}

func TestDecodeEvent_SourceTooLong(t *testing.T) {
	payload := strings.Replace(validPayload(), `"source": "src"`, `"source": "`+strings.Repeat("a", 25)+`"`, 1)
	_, err := decodeEvent([]byte(payload), "fb")
	if err == nil || !strings.Contains(err.Error(), "source") {
		t.Fatalf("expected source error, got %v", err)
	}
}

func TestDecodeEvent_EventTypeTooLong(t *testing.T) {
	payload := strings.Replace(validPayload(), `"event_type": "document.ingested"`, `"event_type": "`+strings.Repeat("a", 65)+`"`, 1)
	_, err := decodeEvent([]byte(payload), "fb")
	if err == nil || !strings.Contains(err.Error(), "event_type") {
		t.Fatalf("expected event_type error, got %v", err)
	}
}

func TestDecodeEvent_TraceIDTooLong(t *testing.T) {
	payload := strings.Replace(validPayload(), `"trace_id": "tr1"`, `"trace_id": "`+strings.Repeat("a", 65)+`"`, 1)
	_, err := decodeEvent([]byte(payload), "fb")
	if err == nil || !strings.Contains(err.Error(), "trace_id") {
		t.Fatalf("expected trace_id error, got %v", err)
	}
}

func TestDecodeEvent_SigTooLong(t *testing.T) {
	payload := strings.Replace(validPayload(), `"sig": "sha256:abc"`, `"sig": "`+strings.Repeat("a", 129)+`"`, 1)
	_, err := decodeEvent([]byte(payload), "fb")
	if err == nil || !strings.Contains(err.Error(), "sig") {
		t.Fatalf("expected sig error, got %v", err)
	}
}

func TestDecodeEvent_MissingTimestamp(t *testing.T) {
	payload := strings.Replace(validPayload(), `"timestamp": "2026-09-28T14:00:00Z",`, "", 1)
	_, err := decodeEvent([]byte(payload), "fb")
	if err == nil || !strings.Contains(err.Error(), "timestamp") {
		t.Fatalf("expected timestamp error, got %v", err)
	}
}

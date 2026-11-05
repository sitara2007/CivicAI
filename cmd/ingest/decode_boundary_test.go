package main

import (
	"bytes"
	"strings"
	"testing"
)

type boundaryFields struct {
	tenant, source, etype, trace, sig, payload string
}

func defaultBoundaryFields() boundaryFields {
	return boundaryFields{
		tenant:  "t1",
		source:  "src",
		etype:   "e",
		trace:   "tr",
		sig:     "s",
		payload: "{}",
	}
}

func (f boundaryFields) raw() []byte {
	return []byte(`{"tenant_id":"` + f.tenant + `","sequence":1,"source":"` + f.source + `","timestamp":"2026-09-28T14:00:00Z","event_type":"` + f.etype + `","trace_id":"` + f.trace + `","sig":"` + f.sig + `","payload":` + f.payload + `}`)
}

func repA(n int) string {
	return strings.Repeat("a", n)
}

func jsonObjLen(n int) string {
	return `{"k":"` + strings.Repeat("a", n-8) + `"}`
}

func trimmedLen(b []byte) int {
	return len(bytes.TrimRight(b, " \x00"))
}

func TestDecodeEvent_ExactLimits(t *testing.T) {
	tests := []struct {
		name    string
		mut     func(*boundaryFields)
		wantErr string
		stored  func(*AuditEvent) int
		wantLen int
	}{
		{
			name:    "tenant_id 24 ok",
			mut:     func(f *boundaryFields) { f.tenant = repA(24) },
			wantErr: "",
			stored:  func(e *AuditEvent) int { return trimmedLen(e.TenantID[:]) },
			wantLen: 24,
		},
		{
			name:    "tenant_id 25 rejected",
			mut:     func(f *boundaryFields) { f.tenant = repA(25) },
			wantErr: "tenant_id exceeds",
			stored:  nil,
			wantLen: 0,
		},
		{
			name:    "source 24 ok",
			mut:     func(f *boundaryFields) { f.source = repA(24) },
			wantErr: "",
			stored:  func(e *AuditEvent) int { return trimmedLen(e.Source[:]) },
			wantLen: 24,
		},
		{
			name:    "source 25 rejected",
			mut:     func(f *boundaryFields) { f.source = repA(25) },
			wantErr: "source exceeds",
			stored:  nil,
			wantLen: 0,
		},
		{
			name:    "event_type 64 ok",
			mut:     func(f *boundaryFields) { f.etype = repA(64) },
			wantErr: "",
			stored:  func(e *AuditEvent) int { return e.EventTypeN },
			wantLen: 64,
		},
		{
			name:    "event_type 65 rejected",
			mut:     func(f *boundaryFields) { f.etype = repA(65) },
			wantErr: "event_type exceeds",
			stored:  nil,
			wantLen: 0,
		},
		{
			name:    "trace_id 64 ok",
			mut:     func(f *boundaryFields) { f.trace = repA(64) },
			wantErr: "",
			stored:  func(e *AuditEvent) int { return e.TraceIDN },
			wantLen: 64,
		},
		{
			name:    "trace_id 65 rejected",
			mut:     func(f *boundaryFields) { f.trace = repA(65) },
			wantErr: "trace_id exceeds",
			stored:  nil,
			wantLen: 0,
		},
		{
			name:    "sig 128 ok",
			mut:     func(f *boundaryFields) { f.sig = repA(128) },
			wantErr: "",
			stored:  func(e *AuditEvent) int { return e.SigN },
			wantLen: 128,
		},
		{
			name:    "sig 129 rejected",
			mut:     func(f *boundaryFields) { f.sig = repA(129) },
			wantErr: "sig exceeds",
			stored:  nil,
			wantLen: 0,
		},
		{
			name:    "payload 128 ok",
			mut:     func(f *boundaryFields) { f.payload = jsonObjLen(128) },
			wantErr: "",
			stored:  func(e *AuditEvent) int { return e.PayloadN },
			wantLen: 128,
		},
		{
			name:    "payload 129 rejected",
			mut:     func(f *boundaryFields) { f.payload = jsonObjLen(129) },
			wantErr: "payload exceeds",
			stored:  nil,
			wantLen: 0,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			f := defaultBoundaryFields()
			tc.mut(&f)
			evt, err := decodeEvent(f.raw(), "fb")
			if tc.wantErr != "" {
				if err == nil || !strings.Contains(err.Error(), tc.wantErr) {
					t.Fatalf("err = %v, want contains %q", err, tc.wantErr)
				}
				if evt != nil {
					releaseEvent(evt)
					t.Fatal("non-nil event on error")
				}
				return
			}
			if err != nil || evt == nil {
				t.Fatalf("want success, got evt=%v err=%v", evt, err)
			}
			defer releaseEvent(evt)
			if got := tc.stored(evt); got != tc.wantLen {
				t.Fatalf("stored length = %d, want %d (silent truncation?)", got, tc.wantLen)
			}
		})
	}
}

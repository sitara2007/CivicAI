package middleware

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestPIIRedactionMiddlewareRedactsBeforeHandler(t *testing.T) {
	handler := PIIRedactionMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		text, ok := RedactedTextFromContext(r.Context())
		if !ok {
			t.Fatal("redacted text missing from request context")
		}
		if got := RedactedCountFromContext(r.Context()); got != 3 {
			t.Fatalf("redacted count = %d, want 3", got)
		}

		var body map[string]string
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			t.Fatal(err)
		}
		if body["text"] != text {
			t.Fatalf("downstream body text = %q, context text = %q", body["text"], text)
		}
		if strings.Contains(text, "123-45-6789") ||
			strings.Contains(text, "555-123-4567") ||
			strings.Contains(text, "person@example.gov") {
			t.Fatalf("PII was not redacted: %q", text)
		}
		w.WriteHeader(http.StatusNoContent)
	}))

	request := httptest.NewRequest(
		http.MethodPost,
		"/v1/redact",
		strings.NewReader(`{"text":"SSN 123-45-6789, phone 555-123-4567, email person@example.gov"}`),
	)
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	if response.Code != http.StatusNoContent {
		t.Fatalf("status = %d, want %d", response.Code, http.StatusNoContent)
	}
}

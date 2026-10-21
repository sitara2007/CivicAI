package middleware

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"regexp"
	"strings"
)

const maxPIIRequestSize = 1 << 20

type piiContextKey string

const (
	redactedTextKey  piiContextKey = "redacted_text"
	redactedCountKey piiContextKey = "redacted_count"
)

var piiPatterns = []struct {
	pattern     *regexp.Regexp
	replacement string
}{
	{regexp.MustCompile(`\b\d{3}-\d{2}-\d{4}\b`), "<US_SSN>"},
	{regexp.MustCompile(`\b\d{3}[-.]?\d{3}[-.]?\d{4}\b`), "<PHONE_NUMBER>"},
	{regexp.MustCompile(`\b[\w.+-]+@[\w-]+\.[\w.-]+\b`), "<EMAIL_ADDRESS>"},
}

type documentRequest struct {
	Text       string `json:"text"`
	SourceType string `json:"source_type,omitempty"`
}

func RedactPII(text string) (string, int) {
	count := 0
	for _, item := range piiPatterns {
		var countForPattern int
		text, countForPattern = replaceMatches(item.pattern, text, item.replacement)
		count += countForPattern
	}
	return text, count
}

func replaceMatches(pattern *regexp.Regexp, text, replacement string) (string, int) {
	matches := pattern.FindAllStringIndex(text, -1)
	if len(matches) == 0 {
		return text, 0
	}
	var result strings.Builder
	result.Grow(len(text))
	last := 0
	for _, match := range matches {
		result.WriteString(text[last:match[0]])
		result.WriteString(replacement)
		last = match[1]
	}
	result.WriteString(text[last:])
	return result.String(), len(matches)
}

func PIIRedactionMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if r.ContentLength > maxPIIRequestSize {
			http.Error(w, "payload too large", http.StatusRequestEntityTooLarge)
			return
		}

		originalBody := r.Body
		defer originalBody.Close()
		body, err := io.ReadAll(io.LimitReader(originalBody, maxPIIRequestSize+1))
		if err != nil {
			http.Error(w, "failed to read body", http.StatusBadRequest)
			return
		}
		if len(body) > maxPIIRequestSize {
			http.Error(w, "payload too large", http.StatusRequestEntityTooLarge)
			return
		}

		var input documentRequest
		if err := json.Unmarshal(body, &input); err != nil || strings.TrimSpace(input.Text) == "" {
			http.Error(w, "invalid document payload", http.StatusBadRequest)
			return
		}
		var count int
		input.Text, count = RedactPII(input.Text)
		safeBody, err := json.Marshal(input)
		if err != nil {
			http.Error(w, "failed to redact document", http.StatusInternalServerError)
			return
		}

		ctx := context.WithValue(r.Context(), redactedTextKey, input.Text)
		ctx = context.WithValue(ctx, redactedCountKey, count)
		r.Body = io.NopCloser(bytes.NewReader(safeBody))
		defer r.Body.Close()
		r.ContentLength = int64(len(safeBody))
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func RedactedTextFromContext(ctx context.Context) (string, bool) {
	text, ok := ctx.Value(redactedTextKey).(string)
	return text, ok
}

func RedactedCountFromContext(ctx context.Context) int {
	count, _ := ctx.Value(redactedCountKey).(int)
	return count
}

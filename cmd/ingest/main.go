package main

import (
	"bytes"
	"context"
	"crypto/tls"
	"crypto/x509"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strconv"
	"sync"
	"syscall"
	"time"

	"CivicAI/internal/middleware"
)

const (
	defaultAddr               = "0.0.0.0:8443"
	defaultRingCap            = 65536
	defaultMaxBodySize        = 1 << 20
	defaultWorkers            = 4
	defaultClickHouseDatabase = "civic_audit"
	defaultClickHouseTable    = "audit_events"
)

type AuditEvent struct {
	TenantID   [24]byte
	Source     [24]byte
	EventType  [64]byte
	TraceID    [64]byte
	Sig        [128]byte
	Sequence   uint64
	TS         int64
	Payload    [128]byte
	PayloadN   int
	EventTypeN int
	TraceIDN   int
	SigN       int
}

var auditEventPool = sync.Pool{
	New: func() any {
		return &AuditEvent{}
	},
}

type eventQueue struct {
	ch chan *AuditEvent
}

func newEventQueue(capacity int) *eventQueue {
	return &eventQueue{ch: make(chan *AuditEvent, capacity)}
}

func (q *eventQueue) publish(e *AuditEvent) bool {
	select {
	case q.ch <- e:
		return true
	default:
		return false
	}
}

type ingestRequest struct {
	TenantID string          `json:"tenant_id"`
	Sequence uint64          `json:"sequence"`
	Source   string          `json:"source"`
	TS       time.Time       `json:"timestamp"`
	EventType string         `json:"event_type"`
	TraceID  string         `json:"trace_id"`
	Sig      string          `json:"sig"`
	Payload  json.RawMessage `json:"payload"`
}

type clickHouseBatchWriter struct {
	client     *http.Client
	endpoint   string
	username   string
	password   string
	insertSQL  string
	bufferPool sync.Pool
}

func newClickHouseBatchWriter() (*clickHouseBatchWriter, error) {
	database := getenv("CLICKHOUSE_DATABASE", defaultClickHouseDatabase)
	table := getenv("CLICKHOUSE_TABLE", defaultClickHouseTable)
	if !validIdentifier(database) {
		return nil, fmt.Errorf("invalid CLICKHOUSE_DATABASE %q", database)
	}
	if !validIdentifier(table) {
		return nil, fmt.Errorf("invalid CLICKHOUSE_TABLE %q", table)
	}

	return &clickHouseBatchWriter{
		client:    &http.Client{Timeout: 5 * time.Second},
		endpoint:  getenv("CLICKHOUSE_HTTP_URL", "http://localhost:8123"),
		username:  os.Getenv("CLICKHOUSE_USER"),
		password:  os.Getenv("CLICKHOUSE_PASSWORD"),
		insertSQL: fmt.Sprintf("INSERT INTO %s.%s (tenant_id, sequence, timestamp, source, event_type, payload, trace_id, sig) FORMAT JSONEachRow", database, table),
		bufferPool: sync.Pool{
			New: func() any {
				return bytes.NewBuffer(make([]byte, 0, 64<<10))
			},
		},
	}, nil
}

func (w *clickHouseBatchWriter) writeBatch(events []*AuditEvent) error {
	buf := w.bufferPool.Get().(*bytes.Buffer)
	buf.Reset()
	defer w.bufferPool.Put(buf)

	for _, e := range events {
		appendEventJSON(buf, e)
		buf.WriteByte('\n')
	}

	endpoint, err := clickHouseInsertURL(w.endpoint, w.insertSQL)
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(context.Background(), http.MethodPost, endpoint, bytes.NewReader(buf.Bytes()))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	if w.username != "" {
		req.SetBasicAuth(w.username, w.password)
	}
	resp, err := w.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode < http.StatusOK || resp.StatusCode >= http.StatusMultipleChoices {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
		return fmt.Errorf("clickhouse insert failed: status=%d body=%q", resp.StatusCode, string(body))
	}
	return nil
}

func validIdentifier(s string) bool {
	if s == "" {
		return false
	}
	for _, r := range s {
		if r >= 'a' && r <= 'z' {
			continue
		}
		if r >= 'A' && r <= 'Z' {
			continue
		}
		if r >= '0' && r <= '9' {
			continue
		}
		if r == '_' {
			continue
		}
		return false
	}
	return true
}

func clickHouseInsertURL(endpoint, query string) (string, error) {
	u, err := url.Parse(endpoint)
	if err != nil {
		return "", err
	}
	values := u.Query()
	values.Set("query", query)
	u.RawQuery = values.Encode()
	return u.String(), nil
}

func appendEventJSON(buf *bytes.Buffer, e *AuditEvent) {
	buf.WriteString(`{"tenant_id":`)
	appendQuoted(buf, bytesWithoutZero(e.TenantID[:]))
	buf.WriteString(`,"sequence":`)
	buf.WriteString(strconv.FormatUint(e.Sequence, 10))
	buf.WriteString(`,"timestamp":`)
	appendQuoted(buf, []byte(time.Unix(0, e.TS).UTC().Format("2006-01-02 15:04:05.000")))
	buf.WriteString(`,"source":`)
	appendQuoted(buf, bytesWithoutZero(e.Source[:]))
	buf.WriteString(`,"event_type":`)
	appendQuoted(buf, e.EventType[:e.EventTypeN])
	buf.WriteString(`,"payload":`)
	appendQuoted(buf, e.Payload[:e.PayloadN])
	buf.WriteString(`,"trace_id":`)
	appendQuoted(buf, e.TraceID[:e.TraceIDN])
	buf.WriteString(`,"sig":`)
	appendQuoted(buf, e.Sig[:e.SigN])
	buf.WriteByte('}')
}

func appendQuoted(buf *bytes.Buffer, b []byte) {
	buf.WriteString(strconv.Quote(string(b)))
}

func bytesWithoutZero(b []byte) []byte {
	end := len(b)
	for end > 0 && b[end-1] == 0 {
		end--
	}
	return b[:end]
}

func loadServerTLS() (*tls.Config, error) {
	certPath := getenv("MTLS_CERT_FILE", "/etc/civic-audit-core/tls/server.crt")
	keyPath := getenv("MTLS_KEY_FILE", "/etc/civic-audit-core/tls/server.key")
	caPath := getenv("MTLS_CLIENT_CA_FILE", "/etc/civic-audit-core/tls/ca.crt")

	cert, err := tls.LoadX509KeyPair(certPath, keyPath)
	if err != nil {
		return nil, err
	}
	caPEM, err := os.ReadFile(caPath)
	if err != nil {
		return nil, err
	}
	pool := x509.NewCertPool()
	if !pool.AppendCertsFromPEM(caPEM) {
		return nil, fmt.Errorf("failed to append client CA certs from %s", caPath)
	}
	return &tls.Config{
		MinVersion:   tls.VersionTLS13,
		Certificates: []tls.Certificate{cert},
		ClientCAs:    pool,
		ClientAuth:   tls.RequireAndVerifyClientCert,
	}, nil
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func parseInt(name string, fallback int) int {
	v := os.Getenv(name)
	if v == "" {
		return fallback
	}
	n, err := strconv.Atoi(v)
	if err != nil || n <= 0 {
		return fallback
	}
	return n
}

func decodeEvent(raw []byte, fallbackTraceID string) (*AuditEvent, error) {
	var req ingestRequest
	if err := json.Unmarshal(raw, &req); err != nil {
		return nil, err
	}
	if len(req.TenantID) > 24 {
		return nil, fmt.Errorf("tenant_id exceeds 24 bytes")
	}
	if len(req.Source) > 24 {
		return nil, fmt.Errorf("source exceeds 24 bytes")
	}
	if len(req.EventType) > 64 {
		return nil, fmt.Errorf("event_type exceeds 64 bytes")
	}
	if req.TraceID == "" {
		req.TraceID = fallbackTraceID
	}
	if len(req.TraceID) > 64 {
		return nil, fmt.Errorf("trace_id exceeds 64 bytes")
	}
	if len(req.Sig) > 128 {
		return nil, fmt.Errorf("sig exceeds 128 bytes")
	}
	if len(req.Payload) > 128 {
		return nil, fmt.Errorf("payload exceeds 128 bytes")
	}
	if req.TS.IsZero() {
		return nil, fmt.Errorf("timestamp is required")
	}
	evt := auditEventPool.Get().(*AuditEvent)
	*evt = AuditEvent{}
	copy(evt.TenantID[:], req.TenantID)
	copy(evt.Source[:], req.Source)
	evt.EventTypeN = copy(evt.EventType[:], req.EventType)
	evt.TraceIDN = copy(evt.TraceID[:], req.TraceID)
	evt.SigN = copy(evt.Sig[:], req.Sig)
	evt.Sequence = req.Sequence
	evt.TS = req.TS.UnixNano()
	if len(req.Payload) > 0 {
		n := copy(evt.Payload[:], req.Payload)
		evt.PayloadN = n
	}
	return evt, nil
}

func releaseEvent(evt *AuditEvent) {
	if evt == nil {
		return
	}
	*evt = AuditEvent{}
	auditEventPool.Put(evt)
}

func (q *eventQueue) startWorkers(ctx context.Context, w *clickHouseBatchWriter, flushInterval time.Duration, batchSize, workers int, logger *log.Logger) *sync.WaitGroup {
	var wg sync.WaitGroup
	for id := 0; id < workers; id++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			q.runBatchWorker(ctx, workerID, w, flushInterval, batchSize, logger)
		}(id)
	}
	return &wg
}

func (q *eventQueue) runBatchWorker(ctx context.Context, workerID int, w *clickHouseBatchWriter, flushInterval time.Duration, batchSize int, logger *log.Logger) {
	ticker := time.NewTicker(flushInterval)
	defer ticker.Stop()
	batch := make([]*AuditEvent, 0, batchSize)
	flush := func() {
		if len(batch) == 0 {
			return
		}
		if err := w.writeBatch(batch); err != nil {
			logger.Printf("audit writer worker=%d: %v", workerID, err)
		}
		for _, evt := range batch {
			releaseEvent(evt)
		}
		batch = batch[:0]
	}
	for {
		select {
		case <-ctx.Done():
			for {
				select {
				case evt := <-q.ch:
					batch = append(batch, evt)
					if len(batch) == batchSize {
						flush()
					}
				default:
					flush()
					return
				}
			}
		case evt := <-q.ch:
			batch = append(batch, evt)
			if len(batch) == batchSize {
				flush()
			}
		case <-ticker.C:
			flush()
		}
	}
}

func httpHandler(q *eventQueue) http.HandlerFunc {
	return func(w http.ResponseWriter, req *http.Request) {
		if req.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		if req.ContentLength > int64(defaultMaxBodySize) {
			http.Error(w, "payload too large", http.StatusRequestEntityTooLarge)
			return
		}

		tenant, ok := middleware.TenantFromContext(req.Context())
		if !ok {
			http.Error(w, "tenant not present", http.StatusUnauthorized)
			return
		}
		if len(tenant) > 24 {
			http.Error(w, "tenant identity too large", http.StatusUnauthorized)
			return
		}

		body, err := io.ReadAll(io.LimitReader(req.Body, defaultMaxBodySize+1))
		if err != nil {
			http.Error(w, "failed to read body", http.StatusBadRequest)
			return
		}
		if len(body) > defaultMaxBodySize {
			http.Error(w, "payload too large", http.StatusRequestEntityTooLarge)
			return
		}

		evt, err := decodeEvent(body, req.Header.Get("X-Trace-ID"))
		if err != nil {
			http.Error(w, "invalid ingest payload", http.StatusBadRequest)
			return
		}

		if tenant != "" {
			copy(evt.TenantID[:], tenant)
		}

		if !q.publish(evt) {
			releaseEvent(evt)
			http.Error(w, "audit queue full", http.StatusServiceUnavailable)
			return
		}

		w.WriteHeader(http.StatusAccepted)
	}
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	queue := newEventQueue(parseInt("AUDIT_RING_CAPACITY", defaultRingCap))
	logger := log.New(os.Stdout, "audit-ingest ", log.LstdFlags|log.LUTC)

	writer, err := newClickHouseBatchWriter()
	if err != nil {
		logger.Fatalf("clickhouse writer: %v", err)
	}
	batcherCtx, cancel := context.WithCancel(ctx)
	defer cancel()
	workers := parseInt("AUDIT_WORKERS", defaultWorkers)
	workerWG := queue.startWorkers(batcherCtx, writer, 10*time.Millisecond, 256, workers, logger)

	mux := http.NewServeMux()
	mux.Handle("/v1/audit-events", middleware.MTLSMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		httpHandler(queue)(w, r)
	})))
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	tlsCfg, err := loadServerTLS()
	if err != nil {
		logger.Fatalf("load server tls: %v", err)
	}

	srv := &http.Server{
		Addr:              getenv("AUDIT_ADDR", defaultAddr),
		Handler:           mux,
		TLSConfig:         tlsCfg,
		ReadHeaderTimeout: 2 * time.Second,
		ReadTimeout:       5 * time.Second,
		WriteTimeout:      5 * time.Second,
		IdleTimeout:       30 * time.Second,
	}

	bindAddr := getenv("AUDIT_ADDR", defaultAddr)
	if bindAddr == "localhost" || bindAddr == "127.0.0.1" || bindAddr == "[::1]" {
		port := getenv("PORT", "8443")
		bindAddr = "0.0.0.0:" + port
	}
	if bindAddr == "" {
		bindAddr = defaultAddr
	}
	srv.Addr = bindAddr

	logger.Printf("listening on %s", srv.Addr)
	serverErr := make(chan error, 1)
	go func() {
		serverErr <- srv.ListenAndServeTLS("", "")
	}()

	select {
	case <-ctx.Done():
		shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
		if err := srv.Shutdown(shutdownCtx); err != nil {
			logger.Printf("shutdown: %v", err)
		}
		shutdownCancel()
	case err := <-serverErr:
		if err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Fatalf("serve: %v", err)
		}
	}

	cancel()
	workerWG.Wait()
}

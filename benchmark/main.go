package main

import (
	"context"
	"errors"
	"fmt"
	"math/rand"
	"sync"
	"time"
)

// The API now has an "Outage" state to simulate correlated real-world failures
type LLMClient struct {
	failureRate float64
	latencyMin  time.Duration
	latencyMax  time.Duration
	mu          sync.Mutex
	isOutage    bool
	outageTimer *time.Timer
}

func NewLLMClient(failureRate float64) *LLMClient {
	c := &LLMClient{failureRate: failureRate, latencyMin: 50 * time.Millisecond, latencyMax: 150 * time.Millisecond}
	// Simulate a 2-second correlated outage every 5 seconds
	go func() {
		for {
			time.Sleep(5 * time.Second)
			c.mu.Lock()
			c.isOutage = true
			fmt.Println("\n[SYSTEM] 🚨 API OUTAGE DETECTED: All requests failing...")
			c.mu.Unlock()
			time.Sleep(2 * time.Second)
			c.mu.Lock()
			c.isOutage = false
			fmt.Println("[SYSTEM] ✅ API RECOVERED")
			c.mu.Unlock()
		}
	}()
	return c
}

func (c *LLMClient) Extract(ctx context.Context, doc string) (string, error) {
	latency := c.latencyMin + time.Duration(rand.Int63n(int64(c.latencyMax-c.latencyMin)))
	time.Sleep(latency) // Simulate network

	c.mu.Lock()
	outage := c.isOutage
	c.mu.Unlock()

	if outage {
		return "", errors.New("server_error: 503 service unavailable (OUTAGE)")
	}
	if rand.Float64() < c.failureRate {
		return "", errors.New("timeout: context deadline exceeded")
	}
	return fmt.Sprintf("extracted_data_from_%s", doc), nil
}

// WORKER POOL APPROACH (Real-world concurrency)
func processDocs(ctx context.Context, client *LLMClient, docs []string, strategy func(context.Context, *LLMClient, string) (bool, error)) (success, fail int) {
	var wg sync.WaitGroup
	var mu sync.Mutex
	// Simulate a worker pool of 10 concurrent workers
	sem := make(chan struct{}, 10)

	for _, doc := range docs {
		wg.Add(1)
		go func(d string) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			ok, _ := strategy(ctx, client, d)
			mu.Lock()
			if ok {
				success++
			} else {
				fail++
			}
			mu.Unlock()
		}(doc)
	}
	wg.Wait()
	return
}

func noRetry(ctx context.Context, client *LLMClient, doc string) (bool, error) {
	_, err := client.Extract(ctx, doc)
	return err == nil, err
}

func fixedRetry(ctx context.Context, client *LLMClient, doc string) (bool, error) {
	for i := 0; i < 3; i++ {
		_, err := client.Extract(ctx, doc)
		if err == nil {
			return true, nil
		}
		time.Sleep(100 * time.Millisecond)
	}
	return false, errors.New("failed after 3 attempts")
}

func expBackoff(ctx context.Context, client *LLMClient, doc string) (bool, error) {
	baseDelay := 50 * time.Millisecond
	for i := 0; i < 5; i++ {
		_, err := client.Extract(ctx, doc)
		if err == nil {
			return true, nil
		}
		delay := baseDelay * time.Duration(1<<uint(i))
		jitter := time.Duration(rand.Int63n(int64(delay / 2)))
		time.Sleep(delay + jitter)
	}
	return false, errors.New("failed after 5 attempts")
}

func main() {
	rand.Seed(time.Now().UnixNano())

	// 100 documents, 30% base failure rate
	docs := make([]string, 100)
	for i := range docs {
		docs[i] = fmt.Sprintf("doc_%d.pdf", i)
	}

	client := NewLLMClient(0.30)
	ctx := context.Background()

	fmt.Println("=== LLM Reliability Benchmark (Concurrent + Outage Sim) ===")

	start := time.Now()
	s, f := processDocs(ctx, client, docs, noRetry)
	fmt.Printf("No Retry:        Success: %d | Fail: %d | Time: %v\n", s, f, time.Since(start).Round(time.Millisecond))

	time.Sleep(3 * time.Second) // Wait for outage cycle to reset

	start = time.Now()
	s, f = processDocs(ctx, client, docs, fixedRetry)
	fmt.Printf("Fixed Retry:     Success: %d | Fail: %d | Time: %v\n", s, f, time.Since(start).Round(time.Millisecond))

	time.Sleep(3 * time.Second)

	start = time.Now()
	s, f = processDocs(ctx, client, docs, expBackoff)
	fmt.Printf("Exp Backoff:     Success: %d | Fail: %d | Time: %v\n", s, f, time.Since(start).Round(time.Millisecond))
}

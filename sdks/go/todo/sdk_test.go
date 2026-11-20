package todo_test

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"strconv"
	"sync/atomic"
	"testing"
	"time"

	"github.com/FranciscoHonorat/ToDo/sdks/go/todo"
)

func task(n int) map[string]string {
	return map[string]string{
		"id":          fmt.Sprintf("00000000-0000-0000-0000-00000000000%d", n),
		"title":       fmt.Sprintf("T%d", n),
		"description": "",
		"status":      "PENDING",
	}
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

func TestRetryTransportWaitsRetryAfterAndRetries(t *testing.T) {
	var calls atomic.Int32
	var bodies []string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		bodies = append(bodies, string(body))
		if calls.Add(1) == 1 {
			w.Header().Set("Retry-After", "2")
			writeJSON(w, http.StatusTooManyRequests, map[string]string{"detail": "slow down"})
			return
		}
		writeJSON(w, http.StatusCreated, task(1))
	}))
	defer server.Close()

	var slept []time.Duration
	client, err := todo.New(server.URL, todo.WithSleep(func(d time.Duration) { slept = append(slept, d) }))
	if err != nil {
		t.Fatal(err)
	}

	resp, err := client.CreateTaskWithResponse(context.Background(), todo.TaskInput{Title: "A"})
	if err != nil {
		t.Fatal(err)
	}

	if resp.StatusCode() != http.StatusCreated {
		t.Fatalf("status = %d, want 201", resp.StatusCode())
	}
	if len(slept) != 1 || slept[0] != 2*time.Second {
		t.Fatalf("slept = %v, want [2s]", slept)
	}
	if len(bodies) != 2 || bodies[0] != bodies[1] || bodies[0] == "" {
		t.Fatalf("o corpo precisa ser reenviado igual no retry, got %q", bodies)
	}
}

func TestRetryTransportGivesUpAfterMaxRetries(t *testing.T) {
	var calls atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls.Add(1)
		w.Header().Set("Retry-After", "1")
		writeJSON(w, http.StatusTooManyRequests, map[string]string{"detail": "no"})
	}))
	defer server.Close()

	client, _ := todo.New(server.URL, todo.WithMaxRetries(2), todo.WithSleep(func(time.Duration) {}))
	resp, err := client.ListTasksWithResponse(context.Background(), nil)
	if err != nil {
		t.Fatal(err)
	}

	if resp.StatusCode() != http.StatusTooManyRequests || calls.Load() != 3 {
		t.Fatalf("status=%d calls=%d, want 429 and 3 calls", resp.StatusCode(), calls.Load())
	}
	if resp.JSON429 == nil || resp.JSON429.Detail != "no" {
		t.Fatalf("o 429 final deve vir tipado, got %+v", resp.JSON429)
	}
}

func TestRetryTransportDoesNotWaitLongerThanMaxDelay(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Retry-After", "3600")
		writeJSON(w, http.StatusTooManyRequests, map[string]string{"detail": "later"})
	}))
	defer server.Close()

	slept := false
	client, _ := todo.New(server.URL, todo.WithMaxDelay(30*time.Second), todo.WithSleep(func(time.Duration) { slept = true }))
	resp, _ := client.ListTasksWithResponse(context.Background(), nil)

	if resp.StatusCode() != http.StatusTooManyRequests || slept {
		t.Fatalf("status=%d slept=%v, want 429 without sleeping", resp.StatusCode(), slept)
	}
}

func TestAllTasksWalksEveryPage(t *testing.T) {
	all := []map[string]string{task(1), task(2), task(3), task(4), task(5)}
	var calls atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls.Add(1)
		limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
		offset, _ := strconv.Atoi(r.URL.Query().Get("offset"))
		end := min(offset+limit, len(all))
		w.Header().Set("X-Total-Count", strconv.Itoa(len(all)))
		writeJSON(w, http.StatusOK, all[offset:end])
	}))
	defer server.Close()

	client, _ := todo.New(server.URL)
	var titles []string
	for task, err := range todo.AllTasks(context.Background(), client, nil, 2) {
		if err != nil {
			t.Fatal(err)
		}
		titles = append(titles, task.Title)
	}

	if fmt.Sprint(titles) != "[T1 T2 T3 T4 T5]" || calls.Load() != 3 {
		t.Fatalf("titles=%v calls=%d", titles, calls.Load())
	}
}

func TestAllTasksYieldsTheError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusUnprocessableEntity, map[string]any{"detail": []any{}})
	}))
	defer server.Close()

	client, _ := todo.New(server.URL)
	for _, err := range todo.AllTasks(context.Background(), client, nil, 10) {
		if err == nil || err.Error() != "GET /tasks falhou com 422" {
			t.Fatalf("err = %v", err)
		}
		return
	}
	t.Fatal("esperava um erro")
}

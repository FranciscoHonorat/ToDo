// Package todo é a SDK Go da ToDo API.
//
// client.gen.go é GERADO a partir de docs/openapi.yaml (go generate ./... ou make sdk-go) — não edite.
// Este arquivo é a camada fina escrita à mão: cliente com retry no 429 e paginação.
//
//	client, _ := todo.New("http://localhost:8080/api")
//	created, _ := client.CreateTaskWithResponse(ctx, todo.TaskInput{Title: "Comprar pão"})
//	for task, err := range todo.AllTasks(ctx, client, nil, 100) { ... }
package todo

import (
	"context"
	"fmt"
	"iter"
	"net/http"
	"strconv"
	"time"
)

type options struct {
	maxRetries int
	maxDelay   time.Duration
	sleep      func(time.Duration)
	httpClient *http.Client
}

// Option configura NewClient.
type Option func(*options)

// WithMaxRetries define quantas vezes repetir depois do primeiro 429 (padrão 3).
func WithMaxRetries(n int) Option { return func(o *options) { o.maxRetries = n } }

// WithMaxDelay: se o Retry-After for maior que isso, devolve o 429 em vez de esperar (padrão 60 s).
func WithMaxDelay(d time.Duration) Option { return func(o *options) { o.maxDelay = d } }

// WithSleep troca a espera (útil em testes).
func WithSleep(sleep func(time.Duration)) Option { return func(o *options) { o.sleep = sleep } }

// UseHTTPClient usa um *http.Client próprio; o transporte dele ganha o retry.
// (WithHTTPClient é a ClientOption do código gerado.)
func UseHTTPClient(c *http.Client) Option { return func(o *options) { o.httpClient = c } }

// New cria o cliente gerado (com respostas tipadas) já com retry no 429.
// baseURL ex.: "http://localhost:8000" ou "http://localhost:8080/api" (atrás do nginx).
func New(baseURL string, opts ...Option) (*ClientWithResponses, error) {
	o := options{maxRetries: 3, maxDelay: 60 * time.Second, sleep: time.Sleep, httpClient: &http.Client{Timeout: 10 * time.Second}}
	for _, opt := range opts {
		opt(&o)
	}
	httpClient := *o.httpClient // cópia: não altera o client de quem chamou
	inner := httpClient.Transport
	if inner == nil {
		inner = http.DefaultTransport
	}
	httpClient.Transport = &RetryTransport{Inner: inner, MaxRetries: o.maxRetries, MaxDelay: o.maxDelay, Sleep: o.sleep}
	return NewClientWithResponses(baseURL, WithHTTPClient(&httpClient))
}

// RetryTransport repete requisições que recebem 429, esperando o Retry-After (segundos).
type RetryTransport struct {
	Inner      http.RoundTripper
	MaxRetries int
	MaxDelay   time.Duration
	Sleep      func(time.Duration)
}

func (t *RetryTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	for attempt := 0; ; attempt++ {
		resp, err := t.Inner.RoundTrip(req)
		if err != nil || resp.StatusCode != http.StatusTooManyRequests || attempt >= t.MaxRetries {
			return resp, err
		}
		seconds, convErr := strconv.Atoi(resp.Header.Get("Retry-After"))
		delay := time.Duration(seconds) * time.Second
		if convErr != nil || delay > t.MaxDelay {
			return resp, nil
		}
		// O corpo já foi consumido: GetBody (preenchido pelo http.NewRequest) devolve uma cópia nova.
		if req.Body != nil {
			if req.GetBody == nil {
				return resp, nil
			}
			body, err := req.GetBody()
			if err != nil {
				return resp, nil
			}
			req = req.Clone(req.Context())
			req.Body = body
		}
		resp.Body.Close()
		t.Sleep(delay)
	}
}

// AllTasks percorre todas as tarefas, página por página (limit/offset + X-Total-Count).
// params pode ser nil; Limit/Offset dele são ignorados.
func AllTasks(ctx context.Context, c ClientWithResponsesInterface, params *ListTasksParams, pageSize int) iter.Seq2[TaskOutput, error] {
	return func(yield func(TaskOutput, error) bool) {
		var status *StatusFilter
		if params != nil {
			status = params.Status
		}
		for offset := 0; ; {
			limit, off := pageSize, offset
			resp, err := c.ListTasksWithResponse(ctx, &ListTasksParams{Status: status, Limit: &limit, Offset: &off})
			if err != nil {
				yield(TaskOutput{}, err)
				return
			}
			if resp.JSON200 == nil {
				yield(TaskOutput{}, fmt.Errorf("GET /tasks falhou com %d", resp.StatusCode()))
				return
			}
			page := *resp.JSON200
			for _, task := range page {
				if !yield(task, nil) {
					return
				}
			}
			offset += len(page)
			total, _ := strconv.Atoi(resp.HTTPResponse.Header.Get("X-Total-Count"))
			if len(page) < pageSize || offset >= total {
				return
			}
		}
	}
}

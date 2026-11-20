package todo_test

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/FranciscoHonorat/ToDo/sdks/go/todo"
)

// startAPI sobe a API de verdade (uvicorn do backend/.venv) com banco temporário.
func startAPI(t *testing.T, rateLimit string) string {
	t.Helper()
	backend, _ := filepath.Abs("../../../backend")
	python := filepath.Join(backend, ".venv", "bin", "python")
	if _, err := os.Stat(python); err != nil {
		t.Skip("backend/.venv não instalado")
	}

	listener, _ := net.Listen("tcp", "127.0.0.1:0")
	port := listener.Addr().(*net.TCPAddr).Port
	listener.Close()

	cmd := exec.Command(python, "-m", "uvicorn", "server:app", "--port", fmt.Sprint(port))
	cmd.Dir = backend
	cmd.Env = append(os.Environ(), "TODO_DATABASE="+filepath.Join(t.TempDir(), "sdk.db"), "TODO_RATE_LIMIT="+rateLimit)
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = cmd.Process.Kill(); _ = cmd.Wait() })

	url := fmt.Sprintf("http://127.0.0.1:%d", port)
	for range 100 {
		if resp, err := http.Get(url + "/health"); err == nil && resp.StatusCode == http.StatusOK {
			resp.Body.Close()
			return url
		}
		time.Sleep(100 * time.Millisecond)
	}
	t.Fatal("uvicorn não subiu")
	return ""
}

func TestFullJourneyAgainstRealAPI(t *testing.T) {
	ctx := context.Background()
	client, _ := todo.New(startAPI(t, "off"))

	created, err := client.CreateTaskWithResponse(ctx, todo.TaskInput{Title: "Pelo SDK"})
	if err != nil || created.JSON201 == nil {
		t.Fatalf("create: %v %s", err, created.Body)
	}
	id := created.JSON201.Id

	completed, _ := client.CompleteTaskWithResponse(ctx, id)
	if completed.JSON200.Status != todo.COMPLETED {
		t.Fatalf("complete: %s", completed.Body)
	}
	reopened, _ := client.ReopenTaskWithResponse(ctx, id)
	if reopened.JSON200.Status != todo.PENDING {
		t.Fatalf("reopen: %s", reopened.Body)
	}

	var titles []string
	for task, err := range todo.AllTasks(ctx, client, nil, 100) {
		if err != nil {
			t.Fatal(err)
		}
		titles = append(titles, task.Title)
	}
	if fmt.Sprint(titles) != "[Pelo SDK]" {
		t.Fatalf("titles = %v", titles)
	}

	if deleted, _ := client.DeleteTaskWithResponse(ctx, id); deleted.StatusCode() != http.StatusNoContent {
		t.Fatalf("delete: %d", deleted.StatusCode())
	}
	missing, _ := client.GetTaskWithResponse(ctx, id)
	if missing.JSON404 == nil || !strings.Contains(missing.JSON404.Detail, "not found") {
		t.Fatalf("get after delete: %d %s", missing.StatusCode(), missing.Body)
	}
}

func TestRetriesThroughTheRealRateLimit(t *testing.T) {
	client, _ := todo.New(startAPI(t, "2/second"))

	for i := range 4 {
		resp, err := client.ListTasksWithResponse(context.Background(), nil)
		if err != nil || resp.StatusCode() != http.StatusOK {
			t.Fatalf("chamada %d: status %d err %v", i, resp.StatusCode(), err)
		}
	}
}

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]


class Server:
    """Um uvicorn de verdade, num processo separado, com banco próprio."""

    def __init__(self, database: Path):
        self.database = database
        self.port = _free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self.process = None

    def start(self):
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server:app", "--port", str(self.port)],
            cwd=BACKEND,
            env={**os.environ, "TODO_DATABASE": str(self.database)},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                if self.call("GET", "/health")[0] == 200:
                    return self
            except OSError:
                time.sleep(0.1)
        self.stop()
        raise RuntimeError("uvicorn não subiu em 10s")

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=10)
            self.process = None

    def call(self, method, path, body=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        request = urllib.request.Request(self.url + path, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                status, text = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, text = error.code, error.read()
        return status, json.loads(text) if text else None


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def make_server(tmp_path):
    servers = []

    def factory(database=None):
        server = Server(database or tmp_path / "e2e.db")
        servers.append(server)
        return server.start()

    yield factory
    for server in servers:
        server.stop()


@pytest.fixture
def server(make_server):
    return make_server()

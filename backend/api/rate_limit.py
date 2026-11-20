"""Rate limiting por cliente (IP) com token bucket em memória.

Cada cliente tem um "balde" com até `requests` fichas; cada requisição gasta uma,
e o balde reenche continuamente a `requests / period` fichas por segundo. Isso permite
rajadas curtas (até o tamanho do balde) mas limita a média.

Em memória é suficiente porque o backend roda com uma réplica (SQLite). Com várias
réplicas, cada uma teria o próprio contador — aí o estado precisaria ir para fora
(ex.: Redis) ou o limite para a borda (Ingress/nginx).
"""

import math
import re
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

PERIODS = {"second": 1, "minute": 60, "hour": 3600}
DISABLED = {"", "off", "0"}


@dataclass(frozen=True)
class RateLimit:
    requests: int
    period: float  # segundos

    @classmethod
    def parse(cls, text: str) -> "RateLimit | None":
        """'300/minute' -> RateLimit(300, 60); 'off', '0' ou vazio -> None (desligado)."""
        text = text.strip().lower()
        if text in DISABLED:
            return None
        match = re.fullmatch(r"(\d+)\s*/\s*(second|minute|hour)", text)
        if not match:
            raise ValueError(f"Rate limit inválido: {text!r}. Use '<n>/second|minute|hour' ou 'off'.")
        requests = int(match.group(1))
        return cls(requests, PERIODS[match.group(2)]) if requests else None


@dataclass(frozen=True)
class Decision:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int  # segundos até haver uma ficha (0 se permitido)


class _Bucket:
    __slots__ = ("tokens", "updated")

    def __init__(self, tokens: float, updated: float):
        self.tokens = tokens
        self.updated = updated


class TokenBucketLimiter:
    def __init__(self, limit: RateLimit, clock: Callable[[], float] = time.monotonic, max_clients: int = 10_000):
        self.limit = limit
        self.rate = limit.requests / limit.period  # fichas por segundo
        self.clock = clock
        self.max_clients = max_clients
        self._buckets: dict[str, _Bucket] = {}

    def hit(self, key: str) -> Decision:
        now = self.clock()
        bucket = self._buckets.get(key)
        if bucket is None:
            self._make_room(now)
            bucket = self._buckets[key] = _Bucket(self.limit.requests, now)
        self._refill(bucket, now)

        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return Decision(True, self.limit.requests, math.floor(bucket.tokens), 0)

        wait = math.ceil((1 - bucket.tokens) / self.rate)
        return Decision(False, self.limit.requests, 0, wait)

    def tracked_clients(self) -> int:
        return len(self._buckets)

    def _refill(self, bucket: _Bucket, now: float):
        bucket.tokens = min(self.limit.requests, bucket.tokens + (now - bucket.updated) * self.rate)
        bucket.updated = now

    def _make_room(self, now: float):
        """Mantém a memória limitada: esquece primeiro quem já está com o balde cheio (inativo)."""
        if len(self._buckets) < self.max_clients:
            return
        for key, bucket in list(self._buckets.items()):
            self._refill(bucket, now)
            if bucket.tokens >= self.limit.requests:
                del self._buckets[key]
        # Ainda cheio (muitos clientes ativos)? Remove os mais antigos.
        while len(self._buckets) >= self.max_clients:
            del self._buckets[min(self._buckets, key=lambda k: self._buckets[k].updated)]


def add_rate_limiting(app: FastAPI, limiter: TokenBucketLimiter, exempt: Iterable[str] = ("/health",)):
    exempt = frozenset(exempt)

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        if request.url.path in exempt:
            return await call_next(request)

        # Atrás do nginx, o uvicorn (--proxy-headers) já põe aqui o IP real do X-Forwarded-For.
        decision = limiter.hit(request.client.host if request.client else "unknown")
        headers = {"X-RateLimit-Limit": str(decision.limit), "X-RateLimit-Remaining": str(decision.remaining)}

        if not decision.allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Too many requests. Try again in {decision.retry_after} seconds."},
                headers={**headers, "Retry-After": str(decision.retry_after)},
            )

        response = await call_next(request)
        response.headers.update(headers)
        return response

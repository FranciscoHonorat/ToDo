import pytest

from api.rate_limit import RateLimit, TokenBucketLimiter


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.mark.parametrize(
    "text, expected",
    [
        ("300/minute", RateLimit(300, 60)),
        ("10/second", RateLimit(10, 1)),
        ("1000/hour", RateLimit(1000, 3600)),
        (" 5 / minute ", RateLimit(5, 60)),
    ],
)
def test_parse_reads_requests_per_period(text, expected):
    assert RateLimit.parse(text) == expected


@pytest.mark.parametrize("text", ["off", "OFF", "0", "", "0/minute"])
def test_parse_returns_none_when_disabled(text):
    assert RateLimit.parse(text) is None


@pytest.mark.parametrize("text", ["abc", "10/fortnight", "-1/minute", "10"])
def test_parse_rejects_garbage(text):
    with pytest.raises(ValueError):
        RateLimit.parse(text)


def make_limiter(requests=3, period=60, **kwargs):
    clock = FakeClock()
    return TokenBucketLimiter(RateLimit(requests, period), clock=clock, **kwargs), clock


def test_allows_up_to_the_limit_then_blocks():
    limiter, _ = make_limiter(requests=3)

    decisions = [limiter.hit("1.2.3.4") for _ in range(4)]

    assert [d.allowed for d in decisions] == [True, True, True, False]
    assert [d.remaining for d in decisions] == [2, 1, 0, 0]


def test_blocked_decision_says_how_long_to_wait():
    limiter, _ = make_limiter(requests=3, period=60)  # 1 ficha a cada 20 s
    for _ in range(3):
        limiter.hit("ip")

    assert limiter.hit("ip").retry_after == 20


def test_tokens_refill_over_time():
    limiter, clock = make_limiter(requests=3, period=60)
    for _ in range(3):
        limiter.hit("ip")

    clock.advance(20)

    assert limiter.hit("ip").allowed is True
    assert limiter.hit("ip").allowed is False


def test_refill_never_exceeds_the_limit():
    limiter, clock = make_limiter(requests=3)
    clock.advance(10_000)

    assert [limiter.hit("ip").allowed for _ in range(4)] == [True, True, True, False]


def test_each_client_has_its_own_bucket():
    limiter, _ = make_limiter(requests=1)

    assert limiter.hit("a").allowed is True
    assert limiter.hit("b").allowed is True
    assert limiter.hit("a").allowed is False


def test_idle_clients_are_forgotten_so_memory_stays_bounded():
    limiter, clock = make_limiter(requests=1, period=60, max_clients=2)
    limiter.hit("a")
    limiter.hit("b")
    clock.advance(60)  # os dois baldes já encheram de novo: esquecê-los não muda nada

    limiter.hit("c")

    assert limiter.tracked_clients() <= 2

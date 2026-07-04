import urllib.error

import pytest

import http_client


def _http_error(code, retry_after=None):
    hdrs = {"Retry-After": retry_after} if retry_after is not None else {}
    return urllib.error.HTTPError("http://x", code, "err", hdrs, None)


def test_http_get_retries_status_in_set_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 3:
            raise _http_error(503)
        return "OK"

    out = http_client.http_get("http://x", opener, frozenset({503}),
                               base_delay=1.0, sleep=slept.append)
    assert out == "OK"
    assert slept == [1.0, 2.0]


def test_http_get_does_not_retry_status_outside_set():
    def opener(url):
        raise _http_error(404)

    with pytest.raises(urllib.error.HTTPError) as exc:
        http_client.http_get("http://x", opener, frozenset({503}),
                             sleep=lambda s: None)
    assert exc.value.code == 404


def test_http_get_retry_status_is_parameterized():
    # 403 is retried only when the caller's set includes it.
    def opener(url):
        raise _http_error(403)

    # excluded -> raises immediately (no sleep)
    slept = []
    with pytest.raises(urllib.error.HTTPError):
        http_client.http_get("http://x", opener, frozenset({429}),
                             sleep=slept.append)
    assert slept == []
    # included -> retried then gives up after attempts
    slept2 = []
    with pytest.raises(urllib.error.HTTPError):
        http_client.http_get("http://x", opener, frozenset({403}), attempts=3,
                             base_delay=1.0, sleep=slept2.append)
    assert slept2 == [1.0, 2.0]


def test_http_get_retries_urlerror_and_timeout():
    for exc in (urllib.error.URLError("reset"), TimeoutError("t")):
        calls = {"n": 0}
        slept = []

        def opener(url, _e=exc):
            calls["n"] += 1
            if calls["n"] < 2:
                raise _e
            return "OK"

        assert http_client.http_get("http://x", opener, frozenset(),
                                    base_delay=1.0, sleep=slept.append) == "OK"
        assert slept == [1.0]


def test_http_get_honors_retry_after_header():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _http_error(429, retry_after="7")
        return "OK"

    http_client.http_get("http://x", opener, frozenset({429}),
                        base_delay=1.0, sleep=slept.append)
    assert slept == [7.0]


class _FakeClock:
    """Monotonic clock whose sleep() advances the clock, so RateLimiter's
    wait-until-token loop terminates deterministically without real time."""
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def time(self):
        return self.t

    def sleep(self, dt):
        self.sleeps.append(dt)
        self.t += dt


def test_rate_limiter_spaces_calls_to_same_key():
    clk = _FakeClock()
    rl = http_client.RateLimiter(10.0, clock=clk.time, sleep=clk.sleep)
    for _ in range(3):
        rl.acquire("sec.gov")
    # first call is free (full bucket); each subsequent call waits 1/rate = 0.1s
    assert clk.sleeps == [0.1, 0.1]


def test_rate_limiter_keys_are_independent():
    clk = _FakeClock()
    rl = http_client.RateLimiter(10.0, clock=clk.time, sleep=clk.sleep)
    rl.acquire("a")
    rl.acquire("b")  # different key -> its own full bucket -> no wait
    assert clk.sleeps == []


def test_rate_limiter_refills_over_elapsed_time():
    clk = _FakeClock()
    rl = http_client.RateLimiter(10.0, clock=clk.time, sleep=clk.sleep)
    rl.acquire("sec.gov")   # consumes the one token
    clk.t += 0.1            # 0.1s elapses -> one token refilled externally
    rl.acquire("sec.gov")   # token available, no sleep
    assert clk.sleeps == []


def test_make_opener_acquires_limiter_before_request():
    order = []

    class FakeLimiter:
        def acquire(self, key):
            order.append(("acquire", key))

    class FakeResp:
        def read(self): return b"BODY"
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout=None):
        order.append(("request", req.full_url))
        return FakeResp()

    orig = http_client.urllib.request.urlopen
    http_client.urllib.request.urlopen = fake_urlopen
    try:
        opener = http_client.make_opener(
            {"User-Agent": "UA"}, limiter=FakeLimiter(), limiter_key="sec.gov")
        opener("http://data.sec.gov/x")
    finally:
        http_client.urllib.request.urlopen = orig
    # throttle is paid BEFORE the network request, and with the domain key
    assert order == [("acquire", "sec.gov"), ("request", "http://data.sec.gov/x")]


def test_make_opener_attaches_headers_and_reads_body():
    seen = {}

    class FakeResp:
        def read(self): return b"BODY"
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout=None):
        seen["headers"] = dict(req.header_items())
        seen["timeout"] = timeout
        return FakeResp()

    orig = http_client.urllib.request.urlopen
    http_client.urllib.request.urlopen = fake_urlopen
    try:
        opener = http_client.make_opener({"User-Agent": "UA", "X-App-Token": "TOK"})
        body = opener("http://x")
    finally:
        http_client.urllib.request.urlopen = orig
    assert body == "BODY"
    assert seen["timeout"] == 60
    # urllib title-cases header names
    assert seen["headers"].get("X-app-token") == "TOK"
    assert seen["headers"].get("User-agent") == "UA"

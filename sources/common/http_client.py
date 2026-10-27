"""Shared bounded-backoff HTTP GET used by every network fetcher.

Each screener builds its opener from ``DEFAULT_UA`` (plus any auth headers) and
picks one of the three retryable-status families below, since the services
throttle differently (SEC: 403; Socrata/FRED/EIA: 429 + 5xx; CDN-fronted
FINRA/Cboe files: 429/503 only)."""

import time
import urllib.error
import urllib.request
from collections.abc import Callable

DEFAULT_UA = {"User-Agent": "agentic-trading-research-bot ninadk.dev@gmail.com"}

RETRY_SEC = frozenset({403, 429, 503})  # SEC throttles with 403 (not 429)
RETRY_THROTTLE_5XX = frozenset({429, 500, 502, 503, 504})
RETRY_CDN = frozenset({429, 503})


class RateLimiter:
    """Token-bucket rate limiter keyed on an arbitrary string (e.g. a host or
    registrable domain). ``acquire(key)`` blocks — via the injected ``sleep`` —
    until a token is available for that key, then consumes one, enforcing an
    average of ``rate`` acquisitions/sec per key with a burst of ``capacity``.

    Single-threaded by design: the screeners fetch serially, so no lock is
    needed, and its absence keeps the fake-clock test deterministic. Each key
    gets an independent bucket, so limiting one host never starves another."""

    def __init__(
        self, rate: float, capacity: float = 1.0, *, clock=time.monotonic, sleep=time.sleep
    ):
        self._rate = rate
        self._capacity = capacity
        self._clock = clock
        self._sleep = sleep
        self._state: dict[str, tuple[float, float]] = {}  # key -> (tokens, ts)

    def acquire(self, key: str = "") -> None:
        tokens, last = self._state.get(key, (self._capacity, self._clock()))
        while True:
            now = self._clock()
            tokens = min(self._capacity, tokens + (now - last) * self._rate)
            last = now
            if tokens >= 1.0:
                self._state[key] = (tokens - 1.0, now)
                return
            self._sleep((1.0 - tokens) / self._rate)


# One process-wide bucket shared by every *.sec.gov fetcher (edgar, ftd,
# fundamentals). SEC's fair-access cap is per-IP across the whole domain, not
# per-host, so all SEC openers acquire under the single SEC_HOST_KEY — never the
# literal hostname, which would split www.sec.gov and data.sec.gov into separate
# buckets and permit ~2x the intended aggregate rate. 9 req/s keeps headroom
# under the documented 10 req/s ceiling.
SEC_HOST_KEY = "sec.gov"
SEC_RATE_LIMITER = RateLimiter(9.0)


def make_opener(
    headers: dict,
    timeout: int = 60,
    *,
    limiter: "RateLimiter | None" = None,
    limiter_key: str = "",
    decode: bool = True,
):
    """Return opener(url)->str that GETs the URL with the given request headers
    and decodes the body as UTF-8 (replacing undecodable bytes); ``decode=False``
    returns the raw bytes for binary (ZIP) downloads. When a ``limiter`` is
    supplied, ``limiter.acquire(limiter_key)`` is paid before each request
    (including retries), throttling the shared source."""

    def opener(url: str):
        if limiter is not None:
            limiter.acquire(limiter_key)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return body.decode("utf-8", "replace") if decode else body

    return opener


def retry_delay(err, attempt: int, base_delay: float) -> float:
    """Honor a numeric Retry-After header if present, else exponential backoff."""
    headers = getattr(err, "headers", None)
    retry_after = headers.get("Retry-After") if headers is not None else None
    if retry_after is not None and str(retry_after).isdigit():
        return float(retry_after)
    return base_delay * (2 ** (attempt - 1))


def http_get[T](
    url: str,
    opener: Callable[[str], T],
    retry_status,
    attempts: int = 5,
    base_delay: float = 1.0,
    sleep=time.sleep,
) -> T:
    """GET a URL via ``opener`` (text or bytes) with bounded exponential
    backoff. Retryable: HTTP
    statuses in ``retry_status``, and transient network errors (URLError,
    TimeoutError). Other HTTP errors raise immediately. HTTPError is a URLError
    subclass, so it is matched first."""
    for attempt in range(1, attempts + 1):
        try:
            return opener(url)
        except urllib.error.HTTPError as e:
            if e.code not in retry_status or attempt == attempts:
                raise
            sleep(retry_delay(e, attempt, base_delay))
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == attempts:
                raise
            sleep(retry_delay(e, attempt, base_delay))
    raise AssertionError("unreachable")  # pragma: no cover


def make_getter(opener, retry_status, *, attempts: int = 5, base_delay: float = 1.0):
    """Bind ``http_get`` to a module's opener and retry family. The returned
    ``getter(url, opener=, attempts=, base_delay=, sleep=)`` keeps every seam
    injectable so tests can swap the opener and the sleep."""

    def getter(
        url: str,
        opener=opener,
        attempts: int = attempts,
        base_delay: float = base_delay,
        sleep=time.sleep,
    ):
        return http_get(url, opener, retry_status, attempts, base_delay, sleep)

    return getter

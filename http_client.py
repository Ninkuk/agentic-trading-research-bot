"""Shared bounded-backoff HTTP GET used by the edgar/fred/cftc fetchers.

Each screener supplies its own opener (with its User-Agent / auth headers) and
its own retryable-status set, since the services throttle differently
(SEC: 403; Socrata/FRED: 429 + 5xx)."""
import time
import urllib.error
import urllib.request


def make_opener(headers: dict, timeout: int = 60):
    """Return opener(url)->str that GETs the URL with the given request headers
    and decodes the body as UTF-8 (replacing undecodable bytes)."""
    def opener(url: str) -> str:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")
    return opener


def retry_delay(err, attempt: int, base_delay: float) -> float:
    """Honor a numeric Retry-After header if present, else exponential backoff."""
    headers = getattr(err, "headers", None)
    retry_after = headers.get("Retry-After") if headers is not None else None
    if retry_after is not None and str(retry_after).isdigit():
        return float(retry_after)
    return base_delay * (2 ** (attempt - 1))


def http_get(url: str, opener, retry_status, attempts: int = 5,
             base_delay: float = 1.0, sleep=time.sleep) -> str:
    """GET a URL as text with bounded exponential backoff. Retryable: HTTP
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

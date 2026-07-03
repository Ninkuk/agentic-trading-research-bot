import json
import time
import urllib.error

import http_client

BASE = "https://cdn.cboe.com/api/global/delayed_quotes/options"

_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
# Undocumented CDN behind Cloudflare. Retry only throttling/5xx; 404 means no
# chain for this ticker (fetch_chain maps it to None). Deep-OTM contracts often
# report iv/greeks as 0 — stored as-is; downstream views filter.
_RETRY_STATUS = frozenset({429, 503})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0

_urlopen = http_client.make_opener(_UA)  # opener(url) -> decoded UTF-8 text


def chain_url(symbol: str, is_index: bool, base: str = BASE) -> str:
    """URL of the delayed-quotes chain JSON. Indices take a leading underscore."""
    prefix = "_" if is_index else ""
    return f"{base}/{prefix}{symbol}.json"


def _num(raw, cast):
    """Coerce raw via cast; None/blank/unparseable -> None."""
    if raw is None or raw == "":
        return None
    try:
        return cast(raw)
    except (TypeError, ValueError):
        return None


def _to_int(raw):
    """OI/volume arrive as floats (e.g. 3131.0). None-safe int()."""
    return _num(raw, lambda v: int(float(v)))


def parse_occ(option: str):
    """Parse an OCC symbol ``{ROOT}{YYMMDD}{C|P}{STRIKE*1000:08d}`` by slicing
    from the right (robust to variable/numeric roots). Returns
    (root, 'YYYY-MM-DD', 'call'|'put', strike_float) or None if malformed."""
    s = (option or "").strip()
    if len(s) < 16:
        return None
    strike_raw, cp, ymd, root = s[-8:], s[-9], s[-15:-9], s[:-15]
    if not (root and strike_raw.isdigit() and ymd.isdigit() and cp in ("C", "P")):
        return None
    expiration = f"20{ymd[:2]}-{ymd[2:4]}-{ymd[4:6]}"
    kind = "call" if cp == "C" else "put"
    return root, expiration, kind, int(strike_raw) / 1000.0


def session_date(payload: dict):
    """The 'YYYY-MM-DD' trading date the data represents: the underlying's
    last_trade_time date, else the top-level generation timestamp date, else
    None. Both CBOE formats start with a 10-char ISO date."""
    data = payload.get("data") or {}
    for cand in (data.get("last_trade_time"), payload.get("timestamp")):
        s = (cand or "")[:10]
        if len(s) == 10 and s[4] == "-" and s[7] == "-":
            return s
    return None


def _mark(bid, ask):
    return (bid + ask) / 2 if bid is not None and ask is not None else None


def parse_chain(payload: dict, underlying: str):
    """Split a CBOE chain payload into (daily rollup dict, list of contract
    dicts) for the given catalog `underlying`. Contracts with an unparseable OCC
    symbol are skipped. Pure — no I/O."""
    data = payload.get("data") or {}
    px = _num(data.get("current_price"), float)
    contracts = []
    call_vol = put_vol = call_oi = put_oi = 0
    for o in data.get("options", []):
        parsed = parse_occ(o.get("option"))
        if parsed is None:
            continue
        _root, expiration, kind, strike = parsed
        bid, ask = _num(o.get("bid"), float), _num(o.get("ask"), float)
        oi, vol = _to_int(o.get("open_interest")), _to_int(o.get("volume"))
        contracts.append({
            "occ_symbol": o["option"], "underlying": underlying,
            "expiration": expiration, "strike": strike, "type": kind,
            "bid": bid, "ask": ask, "mark": _mark(bid, ask),
            "last": _num(o.get("last_trade_price"), float),
            "theo": _num(o.get("theo"), float),
            "iv": _num(o.get("iv"), float),
            "delta": _num(o.get("delta"), float),
            "gamma": _num(o.get("gamma"), float),
            "theta": _num(o.get("theta"), float),
            "vega": _num(o.get("vega"), float),
            "rho": _num(o.get("rho"), float),
            "open_interest": oi, "volume": vol,
            "underlying_price": px,
            "vol_oi_ratio": (vol or 0) / max(oi or 0, 1),
        })
        if kind == "call":
            call_vol += vol or 0
            call_oi += oi or 0
        else:
            put_vol += vol or 0
            put_oi += oi or 0
    daily = {
        "underlying": underlying, "underlying_price": px,
        "close": _num(data.get("close"), float),
        "iv30": _num(data.get("iv30"), float),
        "total_call_volume": call_vol, "total_put_volume": put_vol,
        "put_call_volume_ratio": (put_vol / call_vol) if call_vol else None,
        "total_call_oi": call_oi, "total_put_oi": put_oi,
        "put_call_oi_ratio": (put_oi / call_oi) if call_oi else None,
    }
    return daily, contracts


def _http_get(url: str, opener=_urlopen, attempts: int = _MAX_ATTEMPTS,
              base_delay: float = _BASE_DELAY, sleep=time.sleep) -> str:
    """GET chain JSON text with bounded backoff, retrying 429/503 and transient
    network errors. Non-retryable HTTP errors (e.g. 403/404) raise at once, so
    fetch_chain can map 404 -> None."""
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts,
                                base_delay, sleep)


def fetch_chain(symbol: str, is_index: bool, get=_http_get):
    """Download + JSON-decode one ticker's chain. Returns the payload dict, or
    None on HTTP 404 (no chain for this ticker)."""
    try:
        body = get(chain_url(symbol, is_index), opener=_urlopen)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return json.loads(body)

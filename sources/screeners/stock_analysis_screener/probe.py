"""General-purpose probe for stockanalysis.com SvelteKit ``__data.json`` routes.

Every page on stockanalysis.com has a sibling ``__data.json`` endpoint that
returns the server ``load()`` output, ``devalue``-serialized (a flat pool where
integers are back-references). ``catalog.py`` decodes that shape for the screener
page specifically; this module generalizes it so *any* route can be fetched,
decoded, and schema-summarized.

CLI:
    python -m stock_analysis_screener.probe /stocks/AAPL/statistics/
    python -m stock_analysis_screener.probe --keys /markets/gainers/ /ipos/
"""

import json
import sys
import urllib.request

BASE = "https://stockanalysis.com"
_UA = {"User-Agent": "agentic-trading-research-bot ninadk.dev@gmail.com"}
"""Descriptive, per the catalog's "real User-Agent" note and edgar_screener's precedent.

Not a browser spoof: the research corpus loop issues ~77 requests per session, and a
polite client says who it is. stockanalysis.com enforces no UA policy either way.
"""


def unflatten(values):
    """Decode a ``devalue`` flat-array pool. ``values[0]`` is the root.

    Integers in the pool are indices into it; negative sentinels encode
    ``undefined``/holes/non-finite numbers. Arrays whose first element is a
    string are type-tagged specials (Date/Set/Map/...); plain arrays hold only
    integer indices, which is what makes the two cases distinguishable.
    """
    if not isinstance(values, list) or not values:
        return values
    cache: dict = {}
    _SENTINELS = {
        -1: None,
        -2: None,
        -3: float("nan"),
        -4: float("inf"),
        -5: float("-inf"),
        -6: -0.0,
    }

    def hydrate(i):
        if i < 0:
            return _SENTINELS.get(i)
        if i in cache:
            return cache[i]
        v = values[i]
        if v is None or not isinstance(v, (list, dict)):
            cache[i] = v
            return v
        if isinstance(v, list):
            if v and isinstance(v[0], str):  # type-tagged special
                tag = v[0]
                if tag in ("Date", "BigInt"):
                    return v[1]
                if tag == "RegExp":
                    return {"__regexp__": v[1:]}
                if tag == "Set":
                    out = [hydrate(x) for x in v[1:]]
                    cache[i] = out
                    return out
                if tag == "Map":
                    d: dict = {}
                    cache[i] = d
                    for k in range(1, len(v), 2):
                        d[str(hydrate(v[k]))] = hydrate(v[k + 1])
                    return d
                cache[i] = v  # unknown tag -> literal
                return v
            out = []
            cache[i] = out
            out.extend(hydrate(x) for x in v)
            return out
        d = {}
        cache[i] = d
        for k, idx in v.items():
            d[k] = hydrate(idx)
        return d

    return hydrate(0)


def data_url(path):
    """Turn a page route into its ``__data.json`` sibling, preserving query."""
    q = ""
    if "?" in path:
        path, rest = path.split("?", 1)
        q = "?" + rest
    if not path.endswith("/"):
        path += "/"
    return (path if path.startswith("http") else BASE + path) + "__data.json" + q


def resolve_data_json(path, timeout=60, *, urlopen=urllib.request.urlopen, max_redirects=3):
    """Fetch the ``__data.json`` for a page route, following SvelteKit's JSON
    redirect envelope, and return ``(final_path, raw)``.

    A moved route (``/stocks/{T}/filings/`` -> ``/filings/{T}/``), a lowercase
    symbol, or a changed ticker (``/stocks/CSU/`` -> ``/stocks/snda/``) answers
    HTTP 200 with ``{"type": "redirect", "location": ...}`` and no ``nodes`` --
    urllib never sees a 3xx, so a raw fetch decodes to zero nodes.
    """
    hops = 0
    while True:
        req = urllib.request.Request(data_url(path), headers=_UA)
        with urlopen(req, timeout=timeout) as resp:
            raw = json.load(resp)
        if not (isinstance(raw, dict) and raw.get("type") == "redirect"):
            return path, raw
        hops += 1
        if hops > max_redirects:
            raise RuntimeError(f"too many __data.json redirects from {path}")
        path = raw["location"]


def fetch_data_json(path, timeout=60, **kw):
    """Fetch and JSON-parse the ``__data.json`` for a page route (redirects followed)."""
    return resolve_data_json(path, timeout, **kw)[1]


def page_error(raw):
    """The trailing ``{"type": "error", "status": ...}`` node, or ``None``.

    Pro-gated pages, bogus slugs and tickers a route has no data for all end in
    this node inside an HTTP 200; ``decode_nodes`` drops it, so ``page_data``
    silently hands back the preceding layout node instead.
    """
    nodes = raw.get("nodes") or []
    last = nodes[-1] if nodes else None
    if isinstance(last, dict) and last.get("type") == "error":
        return {"status": last.get("status"), "message": (last.get("error") or {}).get("message")}
    return None


def decode_nodes(raw):
    """Return one decoded root object per SvelteKit data node (``None`` for
    skipped/layout-less nodes). The last non-null node is usually the
    page-specific payload."""
    out = []
    for node in raw.get("nodes", []):
        if isinstance(node, dict) and node.get("type") == "data":
            out.append(unflatten(node.get("data")))
        else:
            out.append(None)
    return out


def page_data(path):
    """Convenience: the last non-null decoded node for a route (the page data)."""
    nodes = [n for n in decode_nodes(fetch_data_json(path)) if n is not None]
    return nodes[-1] if nodes else None


def summarize(value, depth=0, maxdepth=3):
    """Compact recursive schema: keys + value types, arrays collapsed to their
    first element with a length marker. Useful for cataloging an unknown route."""
    if depth > maxdepth:
        return "..."
    if isinstance(value, dict):
        return {k: summarize(v, depth + 1, maxdepth) for k, v in list(value.items())[:40]} or "{}"
    if isinstance(value, list):
        if not value:
            return "[]"
        return {f"[{len(value)} items]": summarize(value[0], depth + 1, maxdepth)}
    if isinstance(value, bool):
        return f"bool:{value}"
    if isinstance(value, (int, float)):
        return f"num:{value}"
    if isinstance(value, str):
        return f"str:{value[:40]!r}"
    return "null" if value is None else type(value).__name__


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    keys_only = "--keys" in argv
    for path in (a for a in argv if not a.startswith("--")):
        try:
            final, raw = resolve_data_json(path)
        except Exception as exc:  # noqa: BLE001 - CLI diagnostic
            print(json.dumps({"path": path, "error": str(exc)[:120]}))
            continue
        nodes = [n for n in decode_nodes(raw) if n is not None]
        last = nodes[-1] if nodes else None
        report = {"path": path, "n_data_nodes": len(nodes)}
        if final != path:
            report["redirected_to"] = final
        err = page_error(raw)
        if err:
            report["page_error"] = err  # keys below are the layout fallback, not page data
        if isinstance(last, dict):
            report["keys"] = sorted(last)
            if not keys_only:
                report["schema"] = summarize(last)
        print(json.dumps(report, indent=2, default=str))
        print("=" * 80)


if __name__ == "__main__":
    main()

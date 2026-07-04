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
_UA = {"User-Agent": "Mozilla/5.0"}


def unflatten(values):
    """Decode a ``devalue`` flat-array pool. ``values[0]`` is the root.

    Integers in the pool are indices into it; negative sentinels encode
    ``undefined``/holes/non-finite numbers. Arrays whose first element is a
    string are type-tagged specials (Date/Set/Map/...); plain arrays hold only
    integer indices, which is what makes the two cases distinguishable.
    """
    if not isinstance(values, list) or not values:
        return values
    cache = {}
    _SENTINELS = {-1: None, -2: None, -3: float("nan"),
                  -4: float("inf"), -5: float("-inf"), -6: -0.0}

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
            if v and isinstance(v[0], str):        # type-tagged special
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
                    d = {}
                    cache[i] = d
                    for k in range(1, len(v), 2):
                        d[str(hydrate(v[k]))] = hydrate(v[k + 1])
                    return d
                cache[i] = v                       # unknown tag -> literal
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


def fetch_data_json(path, timeout=60):
    """Fetch and JSON-parse the ``__data.json`` for a page route."""
    req = urllib.request.Request(data_url(path), headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


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
        return {k: summarize(v, depth + 1, maxdepth)
                for k, v in list(value.items())[:40]} or "{}"
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
            raw = fetch_data_json(path)
        except Exception as exc:                    # noqa: BLE001 - CLI diagnostic
            print(json.dumps({"path": path, "error": str(exc)[:120]}))
            continue
        nodes = [n for n in decode_nodes(raw) if n is not None]
        last = nodes[-1] if nodes else None
        report = {"path": path, "n_data_nodes": len(nodes)}
        if isinstance(last, dict):
            report["keys"] = sorted(last)
            if not keys_only:
                report["schema"] = summarize(last)
        print(json.dumps(report, indent=2, default=str))
        print("=" * 80)


if __name__ == "__main__":
    main()

"""Local settings UI: view/change .env tunables in a browser, secrets masked.

NOT the reports dashboard (reports/dashboard.html renders data, is published,
and stays read-only). This file is a local-only writer: it binds 127.0.0.1,
serves one self-contained HTML form over stdlib http.server, and rewrites
.env preserving comments, ordering, and unknown keys. Never scheduled, never
published, not a source (no registry.py entry).

Run: uv run python config_ui.py  (opens your browser; Ctrl-C stops)
"""

import re

_ASSIGN = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<rest>.*)$")
_COMMENTED = re.compile(r"^#\s?(?P<key>[A-Za-z_][A-Za-z0-9_]*)=.*$")


def _split_trailing_comment(rest: str) -> tuple[str, str]:
    """('value', '  # comment') — bash `.env` sourcing treats unquoted
    whitespace-then-# as a comment, so the value ends at that boundary."""
    m = re.search(r"\s+#", rest)
    if m:
        return rest[: m.start()], rest[m.start() :]
    return rest, ""


def parse_env(text: str) -> dict[str, str]:
    """Active KEY=value assignments; trailing comments stripped; last wins."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = _ASSIGN.match(line)
        if m:
            value, _ = _split_trailing_comment(m.group("rest"))
            out[m.group("key")] = value.strip()
    return out


def apply_updates(text: str, updates: dict[str, str | None]) -> str:
    """Rewrite assignments, touching only the lines whose keys are updated.

    Set: uncomment a `#KEY=` default line in place, else rewrite the active
    line (preserving its trailing comment), else append at end. None: drop
    the active assignment line. Everything else passes through untouched.
    """
    if not updates:
        return text
    pending = dict(updates)
    lines = text.splitlines(keepends=True)
    active_keys = {
        m.group("key") for m in (_ASSIGN.match(line.rstrip("\n")) for line in lines) if m
    }
    out_lines: list[str] = []
    for line in lines:
        bare = line.rstrip("\n")
        m = _ASSIGN.match(bare)
        if m and m.group("key") in pending:
            key = m.group("key")
            value = pending.pop(key)
            if value is None:
                continue  # drop the line
            _, comment = _split_trailing_comment(m.group("rest"))
            comment = "  # " + comment.lstrip().lstrip("#").lstrip() if comment else ""
            out_lines.append(f"{key}={value}{comment}\n")
            continue
        mc = _COMMENTED.match(bare)
        if mc and mc.group("key") in pending and mc.group("key") not in active_keys:
            key = mc.group("key")
            value = pending.pop(key)
            if value is None:
                pending[key] = None  # nothing active to remove; keep scanning
                out_lines.append(line)
                continue
            out_lines.append(f"{key}={value}\n")
            continue
        out_lines.append(line)
    result = "".join(out_lines)
    appends = [f"{k}={v}\n" for k, v in pending.items() if v is not None]
    if appends:
        if result and not result.endswith("\n"):
            result += "\n"
        result += "".join(appends)
    return result

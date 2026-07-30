"""Parse docs/GLOSSARY.md (**Term** — definition paragraphs) into a dict.

The glossary is the single source of truth for the dashboard's beginner
popovers; the exporter embeds the parsed dict in data.json. Parsing is
deliberately dumb: a term is a line starting with **, its definition is
everything until the next blank-line-then-** or EOF.
"""

import re
from pathlib import Path

_TERM = re.compile(r"^\*\*(?P<term>[^*]+)\*\*\s*[—-]\s*(?P<rest>.*)$")
_PAREN = re.compile(r"^(?P<main>.+?)\s*\((?P<alt>[^)]+)\)$")


def load_glossary(path: str | Path) -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    out: dict[str, str] = {}
    term: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal term, buf
        if term is None:
            return
        definition = " ".join(s.strip() for s in buf if s.strip())
        if definition:
            m = _PAREN.match(term)
            if m:
                out[m.group("main").strip()] = definition
                out[m.group("alt").strip()] = definition
            else:
                out[term] = definition
        term, buf = None, []

    for line in p.read_text(encoding="utf-8").splitlines():
        m = _TERM.match(line)
        if m:
            flush()
            term = m.group("term").strip()
            buf = [m.group("rest")]
        elif term is not None:
            if not line.strip():
                flush()
            else:
                buf.append(line)
    flush()
    return out

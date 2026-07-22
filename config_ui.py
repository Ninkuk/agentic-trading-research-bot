"""Local settings UI: view/change .env tunables in a browser, secrets masked.

NOT the reports dashboard (reports/dashboard.html renders data, is published,
and stays read-only). This file is a local-only writer: it binds 127.0.0.1,
serves one self-contained HTML form over stdlib http.server, and rewrites
.env preserving comments, ordering, and unknown keys. Never scheduled, never
published, not a source (no registry.py entry).

Run: uv run python config_ui.py  (opens your browser; Ctrl-C stops)
"""

import re
from dataclasses import dataclass

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


SENTINEL = re.compile(r"^ZZ_.*_ZZ$")
_FORBIDDEN = re.compile(r"[\s#\"'`\\]")


@dataclass(frozen=True)
class Knob:
    key: str
    label: str
    help: str
    kind: str  # "int" | "enum" | "str" | "secret"
    lo: int | None = None
    hi: int | None = None
    choices: tuple[str, ...] = ()
    default: str = ""


KNOBS: tuple[Knob, ...] = (
    Knob(
        "RESEARCH_NIGHTLY_MAX",
        "Tickers per night",
        "How many tickers the 10:00pm research run may cover. 0 disables the run. Takes effect at the next 10:00pm run.",
        "int",
        lo=0,
        hi=10,
        default="3",
    ),
    Knob(
        "RESEARCH_STALE_DAYS",
        "Thesis freshness (days)",
        "A thesis older than this is eligible for an automatic refresh. Takes effect at the next 10:00pm run.",
        "int",
        lo=1,
        hi=365,
        default="30",
    ),
    Knob(
        "RESEARCH_NIGHTLY_MODEL",
        "Research model",
        "Model for the overnight research sessions. Takes effect at the next 10:00pm run.",
        "enum",
        choices=("opus", "sonnet", "haiku"),
        default="opus",
    ),
    Knob(
        "NTFY_SERVER",
        "ntfy server",
        "Optional self-hosted ntfy server URL; leave unset for https://ntfy.sh.",
        "str",
    ),
    Knob(
        "NTFY_TOPIC",
        "ntfy topic",
        "Notification topic name — treat like a password (anyone who knows it can read your alerts). https://ntfy.sh",
        "secret",
    ),
    Knob(
        "NTFY_TOKEN",
        "ntfy token",
        "Optional Bearer token for protected topics.",
        "secret",
    ),
    Knob(
        "FRED_API_KEY",
        "FRED API key",
        "St. Louis Fed (macro/regime reader) — https://fred.stlouisfed.org/docs/api/api_key.html",
        "secret",
    ),
    Knob(
        "CFTC_APP_TOKEN",
        "CFTC app token",
        "Optional Socrata token (lifts rate limits) — https://publicreporting.cftc.gov/profile/edit/developer_settings",
        "secret",
    ),
    Knob(
        "EIA_API_KEY",
        "EIA API key",
        "EIA Open Data — https://www.eia.gov/opendata/register.php",
        "secret",
    ),
    Knob(
        "NASS_API_KEY",
        "USDA NASS key",
        "USDA NASS Quick Stats — https://quickstats.nass.usda.gov/api",
        "secret",
    ),
    Knob(
        "HEALTHCHECK_URL",
        "Healthcheck URL",
        "Dead-man's-switch URL pinged nightly (the URL itself is the secret) — https://healthchecks.io",
        "secret",
    ),
)


def is_set(value: str | None) -> bool:
    return bool(value) and not SENTINEL.match(value or "")


def validate(knob: Knob, raw: str) -> str | None:
    if knob.kind == "int":
        if not raw.isdigit():
            return "must be a whole number"
        if (knob.lo is not None and int(raw) < knob.lo) or (
            knob.hi is not None and int(raw) > knob.hi
        ):
            return f"must be between {knob.lo} and {knob.hi}"
        return None
    if knob.kind == "enum":
        return None if raw in knob.choices else f"must be one of: {', '.join(knob.choices)}"
    # str and secret share the .env-safety check; never echo the value back.
    if _FORBIDDEN.search(raw):
        return "may not contain spaces, quotes, backslashes, or #"
    return None


def handle_save(env_text: str, form: dict[str, str]) -> tuple[str | None, dict[str, str]]:
    """Pure save pipeline: form -> validated updates -> new env text.

    All-or-nothing: any error returns (None, errors) and nothing is written.
    Error strings never contain submitted values (secret hygiene).
    """
    current = parse_env(env_text)
    updates: dict[str, str | None] = {}
    errors: dict[str, str] = {}
    for knob in KNOBS:
        if knob.kind == "secret":
            if f"clear_{knob.key}" in form:
                updates[knob.key] = None
            elif form.get(f"secret_{knob.key}", ""):
                raw = form[f"secret_{knob.key}"]
                err = validate(knob, raw)
                if err:
                    errors[knob.key] = err
                else:
                    updates[knob.key] = raw
            continue
        if knob.key not in form:
            continue
        raw = form[knob.key].strip()
        if raw == "":
            if knob.key in current:
                updates[knob.key] = None
            continue
        if raw == current.get(knob.key):
            continue
        err = validate(knob, raw)
        if err:
            errors[knob.key] = err
        else:
            updates[knob.key] = raw
    if errors:
        return None, errors
    return apply_updates(env_text, updates), {}

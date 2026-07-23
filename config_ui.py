"""Local settings UI: view/change .env tunables in a browser, secrets masked.

NOT the reports dashboard (reports/dashboard.html renders data, is published,
and stays read-only). This file is a local-only writer: it binds 127.0.0.1,
serves one self-contained HTML form over stdlib http.server, and rewrites
.env preserving comments, ordering, and unknown keys. Never scheduled, never
published, not a source (no registry.py entry).

Run: uv run python config_ui.py  (opens your browser; Ctrl-C stops)
"""

import argparse
import html as _html
import os
import re
import secrets as _secrets
import sys
import tempfile
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs

_ASSIGN = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<rest>.*)$")
_COMMENTED = re.compile(r"^#\s?(?P<key>[A-Za-z_][A-Za-z0-9_]*)=.*$")


def _split_trailing_comment(rest: str) -> tuple[str, str]:
    """('value', '  # comment') — bash `.env` sourcing treats unquoted
    whitespace-then-# as a comment, so the value ends at that boundary."""
    m = re.search(r"\s+#", rest)
    if m:
        return rest[: m.start()], rest[m.start() :]
    return rest, ""


def _unquote(value: str) -> str:
    """Strip one layer of surrounding matching quotes (`'x'`/`"x"` -> `x`).

    Mirrors what bash itself does when sourcing .env, so parse_env keeps
    reading _quote_env's output back as the plain value (mask/no-op/current
    -value comparisons all operate on the unquoted form).
    """
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def parse_env(text: str) -> dict[str, str]:
    """Active KEY=value assignments; trailing comments stripped; last wins."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = _ASSIGN.match(line)
        if m:
            value, _ = _split_trailing_comment(m.group("rest"))
            out[m.group("key")] = _unquote(value.strip())
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
_SAFE_BARE = re.compile(r"^[A-Za-z0-9_./:@+=-]*$")


def _quote_env(value: str) -> str:
    """Single-quote a value written to .env unless it's bash-bare-safe.

    env.sh bash-sources .env with `set -a; . ./.env` — any of
    `$ ; & | < > ( ) ~ * ! space` there is subject to expansion,
    command-substitution, or re-tokenization by the shell, not treated as
    literal text. Wrapping the value in single quotes suppresses ALL of
    that (bash performs no expansion of any kind inside `'...'`), and no
    escaping is required because validate() already rejects a literal `'`
    in the input — so a quoted value can never be broken out of.
    """
    if _SAFE_BARE.fullmatch(value):
        return value
    return f"'{value}'"


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
        "Notification topic name; treat it like a password (anyone who knows it can read your alerts). https://ntfy.sh",
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
        "St. Louis Fed (macro/regime reader): https://fred.stlouisfed.org/docs/api/api_key.html",
        "secret",
    ),
    Knob(
        "CFTC_APP_TOKEN",
        "CFTC app token",
        "Optional Socrata token (lifts rate limits): https://publicreporting.cftc.gov/profile/edit/developer_settings",
        "secret",
    ),
    Knob(
        "EIA_API_KEY",
        "EIA API key",
        "EIA Open Data: https://www.eia.gov/opendata/register.php",
        "secret",
    ),
    Knob(
        "NASS_API_KEY",
        "USDA NASS key",
        "USDA NASS Quick Stats: https://quickstats.nass.usda.gov/api",
        "secret",
    ),
    Knob(
        "HEALTHCHECK_URL",
        "Healthcheck URL",
        "Dead-man's-switch URL pinged nightly (the URL itself is the secret): https://healthchecks.io",
        "secret",
    ),
)


def is_set(value: str | None) -> bool:
    return bool(value) and not SENTINEL.match(value or "")


def validate(knob: Knob, raw: str) -> str | None:
    if knob.kind == "int":
        if not re.fullmatch(r"[0-9]+", raw):
            return "must be a whole number (digits only)"
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
                    updates[knob.key] = _quote_env(raw)
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
            updates[knob.key] = _quote_env(raw)
    if errors:
        return None, errors
    return apply_updates(env_text, updates), {}


def mask(value: str) -> str:
    return "••••" + value[-4:] if len(value) >= 8 else "••••"


def _field(knob: Knob, values: dict[str, str], errors: dict[str, str]) -> str:
    cur = values.get(knob.key, "")
    err = errors.get(knob.key)
    err_html = f'<p class="err">{_html.escape(err)}</p>' if err else ""
    help_html = re.sub(
        r"(https://[^\s<>\"']+?)([.,)!?]*)(?=\s|$)",
        r'<a href="\1">\1</a>\2',
        _html.escape(knob.help),
    )
    if knob.kind == "secret":
        if is_set(cur):
            state = f"currently {mask(cur)}"
            clear = (
                f'<label class="clear"><input type="checkbox" '
                f'name="clear_{knob.key}"> clear</label>'
            )
        else:
            state, clear = "not set", ""
        state_cls = "state" if is_set(cur) else "state unset"
        control = (
            f'<input type="text" name="secret_{knob.key}" value="" '
            f'placeholder="paste new value (blank = keep)" autocomplete="off"> '
            f'<span class="{state_cls}">{_html.escape(state)}</span> {clear}'
        )
    elif knob.kind == "enum":
        cur_or_default = cur if cur else ""
        opts = [f'<option value="">(default: {_html.escape(knob.default)})</option>']
        for c in knob.choices:
            sel = " selected" if c == cur_or_default else ""
            opts.append(f'<option value="{_html.escape(c)}"{sel}>{_html.escape(c)}</option>')
        control = f'<select name="{knob.key}">{"".join(opts)}</select>'
    else:
        ph = f"default: {knob.default}" if knob.default else "not set"
        control = (
            f'<input type="text" name="{knob.key}" value="{_html.escape(cur)}" placeholder="{ph}">'
        )
    return (
        f'<div class="knob"><label><strong>{_html.escape(knob.label)}</strong>'
        f'</label><div class="ctl">{control}</div>{err_html}'
        f'<p class="help">{help_html}</p></div>'
    )


def render_page(
    values: dict[str, str],
    errors: dict[str, str],
    csrf_token: str,
    saved: bool = False,
) -> str:
    tunables = "".join(_field(k, values, errors) for k in KNOBS if k.kind != "secret")
    secrets_html = "".join(_field(k, values, errors) for k in KNOBS if k.kind == "secret")
    banner = '<p class="saved">Saved.</p>' if saved else ""
    # Visual system mirrors deploy/launchd/dashboard.py's _STYLE (the house
    # style: ink + brass, serif masthead, mono kickers, ledger margin-note
    # grid). If tokens drift, the dashboard is the source of truth.
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Trading bot settings</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<style>
:root{{
  --ink:#0d1013; --paper:#151a1e; --gutter:#10161a; --edge:#232c33;
  --fg:#e8e6df; --muted:#9aa1ab; --faint:#7b828c;
  --brass:#e0bd76; --brass-dim:#b39758; --down:#e0736b; --up:#5bbf8a;
  --serif:ui-serif,Georgia,"Iowan Old Style","Palatino Linotype","Times New Roman",serif;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}}
*{{box-sizing:border-box;}}
body{{margin:0;background:
    radial-gradient(1200px 500px at 80% -10%, rgba(224,189,118,.06), transparent 70%),
    var(--ink);
  color:var(--fg);font-family:var(--sans);font-size:14px;line-height:1.55;
  padding:32px 20px 64px;}}
.page{{max-width:820px;margin:0 auto;}}
.mast{{display:flex;justify-content:space-between;align-items:flex-end;
  border-bottom:2px solid var(--edge);padding-bottom:14px;margin-bottom:26px;}}
.mast h1{{font-family:var(--serif);font-size:30px;font-weight:600;
  letter-spacing:.01em;line-height:1;margin:0;}}
.mast h1 em{{color:var(--brass);font-style:italic;}}
.mast .tag{{color:var(--muted);font-size:12px;margin-top:6px;letter-spacing:.02em;}}
.mast .edition{{text-align:right;font-family:var(--mono);font-size:11px;
  color:var(--muted);letter-spacing:.06em;text-transform:uppercase;line-height:1.7;}}
.mast .edition b{{color:var(--fg);font-weight:600;}}
.saved{{background:rgba(224,189,118,.09);border:1px solid var(--brass-dim);
  color:var(--brass);border-radius:8px;padding:7px 13px;font-size:12px;
  margin:0 0 26px;font-family:var(--mono);}}
.ledger{{display:grid;grid-template-columns:210px 1fr;gap:0;
  border-top:1px solid var(--edge);}}
.note{{padding:22px 22px 22px 0;border-right:1px solid var(--edge);}}
.note .kicker{{font-family:var(--mono);font-size:10px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--brass-dim);margin:0 0 8px;}}
.note h2{{font-family:var(--serif);font-size:18px;font-weight:600;
  margin:0 0 10px;line-height:1.15;}}
.note p{{color:var(--muted);font-size:12.5px;line-height:1.55;margin:0;font-style:italic;}}
.data{{padding:22px 0 26px 26px;min-width:0;}}
.knob{{padding:14px 0;}}
.knob + .knob{{border-top:1px solid rgba(255,255,255,.06);}}
.knob label strong{{font-weight:600;font-size:13.5px;letter-spacing:.01em;}}
.ctl{{margin:7px 0 0;display:flex;align-items:center;gap:12px;flex-wrap:wrap;}}
input[type=text],select{{background:var(--paper);color:var(--fg);
  border:1px solid var(--edge);border-radius:6px;padding:7px 10px;
  font-family:var(--mono);font-size:13px;width:100%;max-width:26rem;
  transition:border-color .12s ease, box-shadow .12s ease;}}
select{{width:auto;min-width:14rem;}}
input[type=text]::placeholder{{color:var(--faint);}}
input[type=text]:hover,select:hover{{border-color:var(--faint);}}
input[type=text]:focus,select:focus{{outline:none;border-color:var(--brass-dim);
  box-shadow:0 0 0 3px rgba(224,189,118,.14);}}
.state{{font-family:var(--mono);font-size:11.5px;color:var(--brass-dim);white-space:nowrap;}}
.state.unset{{color:var(--faint);font-style:italic;}}
.clear{{font-family:var(--mono);font-size:11px;color:var(--muted);
  display:inline-flex;align-items:center;gap:5px;white-space:nowrap;}}
.clear input{{accent-color:var(--brass);}}
.help{{color:var(--muted);font-size:12px;line-height:1.5;margin:7px 0 0;max-width:60ch;}}
.help a{{color:var(--brass-dim);text-decoration:none;border-bottom:1px solid rgba(179,151,88,.4);}}
.help a:hover{{color:var(--brass);border-bottom-color:var(--brass);}}
.err{{color:var(--down);font-family:var(--mono);font-size:12px;margin:6px 0 0;}}
.actions{{border-top:1px solid var(--edge);padding:22px 0 0;margin-top:2px;}}
button{{background:var(--brass);color:var(--ink);border:0;border-radius:6px;
  padding:9px 22px;font-family:var(--mono);font-size:12px;font-weight:600;
  letter-spacing:.08em;text-transform:uppercase;cursor:pointer;
  transition:background .12s ease;}}
button:hover{{background:#eccd8b;}}
button:focus-visible{{outline:2px solid var(--brass-dim);outline-offset:2px;}}
.foot{{color:var(--faint);font-family:var(--mono);font-size:11px;
  margin-top:34px;letter-spacing:.04em;}}
@media (max-width:640px){{
  .ledger{{grid-template-columns:1fr;}}
  .note{{border-right:0;border-bottom:1px solid var(--edge);padding:18px 0 14px;}}
  .data{{padding:18px 0 22px;}}
}}
@media (prefers-reduced-motion:reduce){{
  *{{transition:none !important;}}
}}
</style></head><body>
<div class="page">
<header class="mast">
  <div>
    <h1>The <em>Settings</em> Page</h1>
    <p class="tag">Changes are saved to .env and apply at each job's next
scheduled run. Nothing to restart.</p>
  </div>
  <div class="edition">local only<br><b>nothing leaves this machine</b></div>
</header>
{banner}
<form method="post" action="/">
<input type="hidden" name="csrf" value="{_html.escape(csrf_token)}">
<section class="ledger">
  <div class="note">
    <p class="kicker">Tuning</p>
    <h2>Tunables</h2>
    <p>How the overnight research loop behaves. Plain values, applied at the
next 10:00pm run.</p>
  </div>
  <div class="data">{tunables}</div>
</section>
<section class="ledger">
  <div class="note">
    <p class="kicker">Credentials</p>
    <h2>API keys &amp; tokens</h2>
    <p>Stored in .env, shown masked. Leave a field blank to keep the current
value.</p>
  </div>
  <div class="data">{secrets_html}</div>
</section>
<div class="actions"><button type="submit">Save</button></div>
</form>
<p class="foot">edits .env in place · loopback only · no external assets</p>
</div></body></html>"""


def _atomic_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".env.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


_NONSECRET_KEYS = {k.key for k in KNOBS if k.kind != "secret"}


def _make_handler(env_path: Path, csrf_token: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _respond(self, body: str, status: int = 200) -> None:
            data = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802 — http.server API
            text = env_path.read_text() if env_path.exists() else ""
            saved = self.path.startswith("/?saved")
            self._respond(render_page(parse_env(text), {}, csrf_token, saved=saved))

        def do_POST(self) -> None:  # noqa: N802
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._respond("<h1>400</h1>bad Content-Length header", status=400)
                return
            if length < 0:
                self._respond("<h1>400</h1>bad Content-Length header", status=400)
                return
            qs = parse_qs(self.rfile.read(length).decode(), keep_blank_values=True)
            form = {k: v[0] for k, v in qs.items()}
            received = form.pop("csrf", None)
            if received is None or not _secrets.compare_digest(received, csrf_token):
                self._respond("<h1>403</h1>bad csrf token", status=403)
                return
            text = env_path.read_text() if env_path.exists() else ""
            new_text, errors = handle_save(text, form)
            if errors:
                shown = parse_env(text) | {k: v for k, v in form.items() if k in _NONSECRET_KEYS}
                self._respond(render_page(shown, errors, csrf_token))
                return
            _atomic_write(env_path, new_text or "")
            self.send_response(303)
            self.send_header("Location", "/?saved=1")
            self.end_headers()

        def log_message(self, fmt: str, *args: object) -> None:
            pass  # request lines can carry nothing sensitive, but stay quiet

    return Handler


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Local settings UI (edits .env)")
    ap.add_argument("--port", type=int, default=8378)
    ap.add_argument("--env", default=".env", help="path to the env file")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)

    csrf_token = _secrets.token_hex(16)
    try:
        server = HTTPServer(("127.0.0.1", args.port), _make_handler(Path(args.env), csrf_token))
    except OSError:
        print(
            f"port {args.port} already in use — pass --port <other>",
            file=sys.stderr,
        )
        return 1
    url = f"http://127.0.0.1:{args.port}/"
    print(f"settings UI at {url}  (Ctrl-C to stop)")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())

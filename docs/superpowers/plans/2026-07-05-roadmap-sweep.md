# Roadmap Sweep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement every open task across the docs/ roadmaps: the `gate-llm-backend` (headless `claude -p` replaces the API-key path), fractional sizing + notional-cost checks, the two-tier crowding/pump defense, the launchd deployment tick, the `account-positions` portfolio screener + skill, the `paper-trail-report` skill, and the old-repo ApeWisdom backfill decision.

**Architecture:** Seven independently shippable tasks against the existing four-file screener/pipeline shape. All pipeline changes preserve the repo invariants: stdlib-only, injected `now_iso`, no network in tests, secret hygiene (exception type names only), ELT views, deterministic Stage 4 replay. Config changes ride the frozen `GateConfig` (visible via `config_hash`); replay-relevant state is persisted in gate.db, never read from live config.

**Tech Stack:** Python 3.12 stdlib (`subprocess`, `sqlite3`, `json`, `argparse`), pytest (offline), launchd plist, Claude Code project skills (`.claude/skills/`).

## Global Constraints

- Zero runtime third-party dependencies (stdlib only); pytest is the sole dev dep.
- No network in tests: every external call sits behind an injectable seam (`get=`, `opener=`, `run_proc=`, `complete=`).
- Time enters as injected `now_iso` (UTC `isoformat()`); never wall-clock in the hot path.
- Secret hygiene on errors: print `type(e).__name__` only — never `str(e)`, `repr(e)`, `.url`, subprocess stderr.
- **Strictly no `ANTHROPIC_API_KEY`** dependency for the default gate path (user policy).
- Append-only gate tables: never UPDATE/DELETE `gate_decisions`/`gate_decision_events`; `gate_runs` may gain columns via `ALTER TABLE ... ADD COLUMN` migration.
- Views are derived: recreate with `DROP VIEW IF EXISTS` + `CREATE VIEW` when their definition changes.
- Commits: `--no-gpg-sign` (1Password signing hangs non-interactive), no co-author line.
- Tests mirror module layout: `tests/test_<name>_<layer>.py`.
- Docs: update the owning roadmap file in the same commit as the code that completes the item.

---

### Task 1: `gate-llm-backend` — `complete_cli()` + `--backend` flag

**Files:**
- Modify: `pipeline/gate/catalog.py` (add `CLI_BIN`, `CLI_TIMEOUT_S`)
- Modify: `pipeline/gate/llm.py` (add `CLIError`, `complete_cli`)
- Modify: `pipeline/gate/run.py` (`--backend`, backend-aware key resolution, backend-aware `complete` default in `run()` and `replay()`)
- Modify: `.env.example` (ANTHROPIC_API_KEY comment → optional, api backend only)
- Modify: `docs/CLAUDE_ROADMAP.md` (status ✅)
- Test: `tests/test_gate_llm.py`, `tests/test_gate_run.py`, `tests/test_gate_replay.py`

**Interfaces:**
- Produces: `llm.complete_cli(system, user, *, model, api_key=None, run_proc=None, sleep=time.sleep) -> dict` returning a Messages-shaped body `{"content":[{"type":"text","text": <result>}], "model": <served-model-id>}` so `response_text`/`response_model`/`parse_agent` are untouched.
- Produces: `run.run(..., backend="claude-cli")` and `run.replay(..., backend="claude-cli")`; CLI flag `--backend {claude-cli,api}` default `claude-cli`.
- `run_proc` seam has the `subprocess.run` calling convention: `run_proc(argv, input=<str>, capture_output=True, text=True, timeout=<s>, env=<dict>) -> CompletedProcess`.

**Live-verify first (repo policy):** run `claude -p --help` and confirm `--output-format json`, `--model`, `--system-prompt` flags and the result envelope (`{"type":"result","result":"...", "modelUsage":{...}}`) with one real `claude -p 'say hi' --output-format json` call. Adjust argv/envelope parsing if the installed CLI differs.

- [ ] **Step 1: Write failing tests** in `tests/test_gate_llm.py`:

```python
def _cli_envelope(result_text, model="claude-sonnet-5-20250929", is_error=False):
    return json.dumps({"type": "result", "subtype": "success",
                       "is_error": is_error, "result": result_text,
                       "modelUsage": {model: {"inputTokens": 1}}})

class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr

def test_complete_cli_returns_messages_shaped_body():
    calls = []
    def fake_run(argv, **kw):
        calls.append((argv, kw))
        return _Proc(stdout=_cli_envelope('{"action":"approve"}'))
    body = llm.complete_cli("SYS", "USER", model="claude-sonnet-5",
                            run_proc=fake_run)
    assert llm.response_text(body) == '{"action":"approve"}'
    assert llm.response_model(body) == "claude-sonnet-5-20250929"

def test_complete_cli_prompt_via_stdin_not_argv():
    seen = {}
    def fake_run(argv, **kw):
        seen["argv"], seen["input"] = argv, kw["input"]
        return _Proc(stdout=_cli_envelope("ok"))
    llm.complete_cli("SYS", "USER", model="m", run_proc=fake_run)
    assert seen["input"] == "USER"
    assert all("USER" not in a for a in seen["argv"])

def test_complete_cli_strips_api_key_from_env():
    seen = {}
    def fake_run(argv, **kw):
        seen["env"] = kw["env"]
        return _Proc(stdout=_cli_envelope("ok"))
    os.environ["ANTHROPIC_API_KEY"] = "sk-test"
    try:
        llm.complete_cli("SYS", "USER", model="m", run_proc=fake_run)
    finally:
        del os.environ["ANTHROPIC_API_KEY"]
    assert "ANTHROPIC_API_KEY" not in seen["env"]

def test_complete_cli_retries_then_raises_clierror():
    attempts = []
    def fake_run(argv, **kw):
        attempts.append(1)
        return _Proc(returncode=1, stderr="boom")
    with pytest.raises(llm.CLIError):
        llm.complete_cli("SYS", "USER", model="m", run_proc=fake_run,
                         sleep=lambda s: None)
    assert len(attempts) == catalog.LLM_ATTEMPTS

def test_complete_cli_retries_timeout():
    # first attempt raises subprocess.TimeoutExpired, second succeeds
def test_complete_cli_bad_envelope_json_is_retryable():
def test_complete_cli_is_error_envelope_raises():
def test_complete_cli_model_falls_back_to_requested_when_no_modelusage():
```

And in `tests/test_gate_run.py`:

```python
def test_run_default_backend_needs_no_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # run(..., complete=fake_complete) with NO api_key must not raise
def test_run_api_backend_still_demands_key(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError):
        run(..., backend="api")
```

- [ ] **Step 2: Run to verify failures** — `uv run pytest tests/test_gate_llm.py -x` fails with `AttributeError: complete_cli`.

- [ ] **Step 3: Implement.** `pipeline/gate/catalog.py` additions:

```python
CLI_BIN = "claude"     # headless subscription-auth backend (gate-llm-backend)
CLI_TIMEOUT_S = 180    # per-attempt subprocess budget
```

`pipeline/gate/llm.py` additions:

```python
import os
import subprocess

class CLIError(RuntimeError):
    """The claude CLI backend failed after LLM_ATTEMPTS tries."""

def _run_cli(argv, user, timeout):
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    return subprocess.run(argv, input=user, capture_output=True, text=True,
                          timeout=timeout, env=env)

def complete_cli(system: str, user: str, *, model: str, api_key=None,
                 run_proc=None, sleep=time.sleep) -> dict:
    """Headless `claude -p` completion (subscription auth — the no-API-key
    policy path). Returns a Messages-shaped body so response_text /
    response_model / parse_agent and every downstream guardrail are
    untouched. api_key is accepted and ignored (seam compatibility).
    The user prompt travels via stdin, never argv (ps hygiene); the child
    env never carries ANTHROPIC_API_KEY, so auth is structurally
    subscription-only. Retries LLM_ATTEMPTS times on timeout, non-zero
    exit, an unparseable envelope, or is_error; then raises CLIError."""
    argv = [catalog.CLI_BIN, "-p", "--output-format", "json",
            "--model", model, "--system-prompt", system]
    run_proc = run_proc or _run_cli
    last = "unknown"
    for attempt in range(1, catalog.LLM_ATTEMPTS + 1):
        try:
            proc = run_proc(argv, input=user, capture_output=True, text=True,
                            timeout=catalog.CLI_TIMEOUT_S,
                            env={k: v for k, v in os.environ.items()
                                 if k != "ANTHROPIC_API_KEY"})
        except (subprocess.TimeoutExpired, OSError) as e:
            last = type(e).__name__
            proc = None
        if proc is not None and proc.returncode == 0:
            try:
                envelope = json.loads(proc.stdout)
            except ValueError:
                envelope, last = None, "bad envelope"
            if envelope is not None and not envelope.get("is_error"):
                served = next(iter(envelope.get("modelUsage") or {}), model)
                return {"content": [{"type": "text",
                                     "text": envelope.get("result", "")}],
                        "model": served}
            if envelope is not None:
                last = "is_error"
        elif proc is not None:
            last = f"exit {proc.returncode}"
        if attempt < catalog.LLM_ATTEMPTS:
            sleep(retry_delay(None, attempt, 1.0))
    raise CLIError(last)
```

Note: `_run_cli` duplicates the env-strip so the default path is safe even though the loop passes `env=` explicitly — collapse to a single call site in implementation (the loop's `run_proc(...)` call passes all kwargs; `_run_cli` just forwards to `subprocess.run`). Check `retry_delay(None, ...)` handles a non-HTTPError argument (it does for URLError today; verify for None, else pass a dummy `Exception()`).

`pipeline/gate/run.py` changes:

```python
def _resolve_api_key(api_key, dry_run, backend):
    if dry_run or backend == "claude-cli":
        return api_key
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("no API key: pass api_key or set ANTHROPIC_API_KEY "
                         "(api backend only; default backend is claude-cli)")
    return key

def _complete_for(backend, complete):
    if complete is not None:
        return complete
    return llm.complete_cli if backend == "claude-cli" else llm.complete
```

- `run(..., complete=None, backend="claude-cli")`: `complete = _complete_for(backend, complete)`; `api_key = _resolve_api_key(api_key, dry_run, backend)`.
- `replay(..., complete=None, api_key=None, backend="claude-cli")`: same treatment for the `--live` branch (key demanded only for `backend="api"`).
- `main()`: `p.add_argument("--backend", choices=("claude-cli", "api"), default="claude-cli")`; thread through both `run()` and `replay()` calls.
- Scheduler `argv_for` needs **no change**: default backend is the policy.

- [ ] **Step 4: Run** `uv run pytest tests/test_gate_llm.py tests/test_gate_run.py tests/test_gate_replay.py -q` → all pass; then full suite.
- [ ] **Step 5: Update docs** — CLAUDE_ROADMAP `gate-llm-backend` → ✅ with decisions (stdin delivery, env-strip, model pin from `modelUsage`, timeout/retry mapping, no argv_for change). `.env.example` ANTHROPIC_API_KEY comment: "optional — only for `gate --backend api`; default backend is subscription-auth `claude -p`".
- [ ] **Step 6: Commit** `feat(gate): claude-cli backend — headless subscription-auth default, api kept for compatibility`

---

### Task 2: Fractional sizing + notional-cost check

**Files:**
- Modify: `pipeline/promote/catalog.py` (`fractional_shares`, `min_notional` in GateConfig)
- Modify: `pipeline/promote/gates.py` (`size_candidate` fractional + notional clamp; new `gate_notional_book`)
- Modify: `pipeline/promote/db.py` (shares columns → REAL; snapshots `fractional` column + migration; views drop/recreate; `v_gate_input` exposes `fractional`)
- Modify: `pipeline/promote/run.py` (`--fractional` flag + `PIPELINE_FRACTIONAL` env fallback; wire `gate_notional_book`)
- Modify: `pipeline/gate/resolve.py` (`resolve(..., fractional=False)` quantizes to 1e-6)
- Modify: `pipeline/gate/db.py` (DDL REAL; `gate_runs.fractional` column + migration; `write_run` gains `fractional`)
- Modify: `pipeline/gate/run.py` (read `fractional` from `v_gate_input`, store on run, pass to resolve; replay reads header)
- Modify: `.env.example` (`PIPELINE_FRACTIONAL`)
- Modify: `docs/DEFENSES_ROADMAP.md` (status ✅)
- Test: `tests/test_promote_gates.py`, `tests/test_promote_db.py`, `tests/test_promote_run.py`, `tests/test_gate_resolve.py`, `tests/test_gate_run.py`, `tests/test_gate_replay.py`

**Interfaces:**
- Produces: `GateConfig.fractional_shares: bool = False`, `GateConfig.min_notional: float = 1.0`.
- Produces: `gates.gate_notional_book(candidates: list, equity: float) -> (passed, rejections)` — whole-candidate cuts ascending `(det_score, instrument)` until cumulative `shares*price <= equity`; rejections carry `gate='notional'`.
- Produces: `resolve.resolve(size_lo, size_hi, proposal, tau, fractional=False)`; quantum = 1 share or 1e-6.
- Produces: `promote` snapshots column `fractional INTEGER NOT NULL DEFAULT 0`, exposed on `v_gate_input`; `gate_runs.fractional INTEGER NOT NULL DEFAULT 0`; `db.write_run(conn, captured_at, candidates_snapshot_id, window, equity, heat_cap, tau, guardrail_config_version, fractional=0)`.

**Design pins (from DEFENSES_ROADMAP, decided here):**
- Rounding increment 1e-6 (Robinhood), floored: `math.floor(x * 1_000_000 + 1e-6) / 1_000_000`.
- `min_notional` $1 enforced at sizing (Robinhood per-order minimum); a post-gate agent cut can still land under $1 — accepted, order placement is a Claude-command concern (documented in roadmap).
- Per-symbol fractional eligibility: not knowable from current sources — deferred, noted in roadmap.
- gate.db migration stance: `ALTER TABLE gate_runs ADD COLUMN` (not trigger-protected); `gate_decisions` DDL changes to REAL for fresh DBs only — SQLite INTEGER affinity stores non-integral REALs losslessly, proven by test.
- `heat_cut` unchanged (already REAL-safe, no flooring).
- Notional clamp (`shares ≤ equity/price`) applies in **both** modes (the latent whole-share overdraft); `gate_notional_book` cuts the aggregate.

- [ ] **Step 1: Failing tests.** `tests/test_promote_gates.py`:

```python
def _group(price=310.0, atr=6.0, avg_vol=5_000_000, det=0.9):
    return {"instrument": "GLD", "instrument_kind": "etf", "direction": "long",
            "det_score": det, "horizon_band": "months", "signals": [],
            "details": [], "as_of_date": "2026-07-03", "price": price,
            "atr": atr, "average_volume": avg_vol, "sector": "gold",
            "next_earnings_date": None}

def test_size_candidate_fractional_small_account():
    cfg = dataclasses.replace(catalog.DEFAULT_CONFIG, fractional_shares=True)
    cand, rej = gates.size_candidate(_group(), 200.0, 0.5, cfg)
    assert rej is None
    assert 0 < cand["shares"] < 1                # $1 risk / $12 stop ≈ 0.083333
    assert cand["shares"] == math.floor(1.0 / 12.0 * 1e6 + 1e-6) / 1e6
    assert cand["size_hi"] == cand["shares"]

def test_size_candidate_whole_share_notional_clamp():
    # 1 GLD share $310 > $200 equity: even with a huge risk budget the
    # notional clamp zeroes it in whole-share mode -> 'notional' rejection
    cfg = dataclasses.replace(catalog.DEFAULT_CONFIG, risk_fraction=2.0)
    cand, rej = gates.size_candidate(_group(), 200.0, 1.0, cfg)
    assert cand is None and rej["gate"] == "notional"

def test_size_candidate_fractional_min_notional():
    # sized shares worth < $1 -> rejected, not a dust order
def test_size_candidate_whole_share_default_unchanged():
    # regression: default config on a $100k account matches pre-change math
def test_gate_notional_book_cuts_lowest_score_first():
    cands = [{"instrument": "A", "det_score": 0.9, "shares": 0.5, "price": 300.0},
             {"instrument": "B", "det_score": 0.8, "shares": 0.4, "price": 300.0}]
    passed, rejections = gates.gate_notional_book(cands, 200.0)
    assert [c["instrument"] for c in passed] == ["A"]
    assert rejections[0]["gate"] == "notional"
def test_gate_notional_book_all_fit_no_cuts():
```

`tests/test_gate_resolve.py`:

```python
def test_resolve_fractional_quantizes_to_millionth():
    p = {"action": "approve", "size_mult": 0.5, "confidence": 0.9, "rationale": ""}
    out = resolve.resolve(0, 0.083333, p, 0.5, fractional=True)
    assert out["final_shares"] == 0.041666
def test_resolve_whole_share_floor_unchanged():
    # floor(10 * 0.55) == 5 exactly as before
```

`tests/test_promote_db.py` / `tests/test_gate_run.py`:

```python
def test_old_integer_schema_roundtrips_fractional_shares(tmp_path):
    # create candidates table with the OLD INTEGER DDL, insert shares=0.5,
    # read back 0.5 exactly (SQLite NUMERIC affinity keeps REALs lossless)
def test_snapshots_fractional_migration(tmp_path):
    # ensure_schema on a DB created without the column adds it via ALTER
def test_v_gate_input_exposes_fractional(tmp_path):
def test_gate_run_persists_fractional_and_replay_uses_it(tmp_path):
    # promote fractional candidates -> gate run stores fractional=1 ->
    # replay recomputes final_shares with the 1e-6 quantum and reports clean
def test_run_env_fallback_fractional(monkeypatch):
    # PIPELINE_FRACTIONAL=1 flips cfg.fractional_shares
```

- [ ] **Step 2: Verify failures.**
- [ ] **Step 3: Implement.** `gates.size_candidate` core:

```python
def _floor_shares(x: float, fractional: bool):
    if fractional:
        return math.floor(x * 1_000_000 + 1e-6) / 1_000_000
    return math.floor(x)

# inside size_candidate, replacing the two floor/min lines:
    risk_dollars = equity * cfg.risk_fraction * regime_scalar
    raw = risk_dollars / stop_distance
    raw = min(raw, cfg.participation_cap * group["average_volume"])
    price = group["price"]
    notional_cap = equity / price if price > 0 else 0.0
    clamped_by_notional = raw > notional_cap
    raw = min(raw, notional_cap)
    shares = _floor_shares(raw, cfg.fractional_shares)
    if shares <= 0 or shares * price < cfg.min_notional:
        gate = "notional" if (clamped_by_notional
                              or shares * price < cfg.min_notional and shares > 0) \
               else "size_zero"
        return None, _reject(group, gate, ...reason with numbers...)
```

`gate_notional_book(candidates, equity)`: sum `shares*price`; while over budget, cut ascending `(det_score, instrument)`, appending `gate='notional'` rejections; return survivors in original order. Wire in `promote/run.py` after the sizing loop. `--fractional` flag / `PIPELINE_FRACTIONAL` env resolution mirrors `_resolve_equity`; `cfg = dataclasses.replace(cfg, fractional_shares=True)` when set. `db.write_snapshot` gains `fractional` param; `_SCHEMA` snapshots column + `_migrate(conn)` doing `PRAGMA table_info` → `ALTER TABLE snapshots ADD COLUMN fractional INTEGER NOT NULL DEFAULT 0`; `_VIEWS` prefixed with `DROP VIEW IF EXISTS v_latest_candidates; ...` for all three views; `v_gate_input` adds `s.fractional`. `resolve.resolve` gains `fractional=False`, `raw = _floor_shares(size_hi * mult, fractional)` (share the helper by defining it in resolve and importing into gates, or duplicate 3 lines — prefer defining `floor_shares` in `pipeline/gate/resolve.py` and importing in promote is a layering smell; duplicate the tiny helper with a cross-reference comment). Gate `run()`: `fractional = bool(rows[0].get("fractional")) if rows else False`; `db.write_run(..., fractional=int(fractional))`; both `resolve.resolve(...)` call sites (run + `_recompute_decision`) pass it; `_recompute_decision(row, header)` uses `bool(header.get("fractional"))`; gate `db.ensure_schema` migrates `gate_runs`.

- [ ] **Step 4: Full suite green.**
- [ ] **Step 5: Docs** — DEFENSES_ROADMAP section → ✅ with pins; `.env.example` `PIPELINE_FRACTIONAL=` comment.
- [ ] **Step 6: Commit** `feat(promote,gate): fractional shares behind GateConfig + notional-cost checks`

---

### Task 3: Crowding / pump defense (Tier 1 + Tier 2 + plumbing)

**Files:**
- Modify: `pipeline/promote/catalog.py` (crowding thresholds in GateConfig + `CROWDING_FILTER = "all-stocks"`)
- Modify: `pipeline/promote/extract.py` (`load_crowding`)
- Modify: `pipeline/promote/gates.py` (`gate_crowding`)
- Modify: `pipeline/promote/run.py` (`--reddit-db`, wire after G3)
- Modify: `pipeline/gate/catalog.py` (`MASK_DETAIL_KEYS` += `retail_attention_z`)
- Modify: `pipeline/scheduler/catalog.py` (reddit Job + DB_FILES + promote chain + argv_for)
- Modify: `docs/DEFENSES_ROADMAP.md`, `docs/FOLLOWUPS.md` (reddit.db long-retention note)
- Test: `tests/test_promote_extract.py`, `tests/test_promote_gates.py`, `tests/test_promote_run.py`, `tests/test_gate_mask.py`, `tests/test_schedule_catalog.py`

**Interfaces:**
- Produces: GateConfig fields `crowding_rank_max: int = 10`, `crowding_mult: float = 3.0`, `crowding_baseline_days: int = 30`, `crowding_min_n: int = 5`.
- Produces: `extract.load_crowding(conn, now_iso, baseline_days) -> {TICKER: {"rank", "mentions", "baseline_mean", "baseline_std", "n"}}` reading the `all-stocks` filter only; tickers via `pipeline_common.normalize_ticker`.
- Produces: `gates.gate_crowding(groups, crowding, cfg) -> (passed, rejections)`; kills `gate='crowding'`; survivors with data get `{"retail_attention_z": z}` appended to `details` (z rounded 2dp, only when `n >= crowding_min_n` and `baseline_std > 0`).

**Design pins:** kill (not size-halve) — gates only kill in v1, scalar variant deferred to Stage 6 trials; threshold form = rank floor AND per-name multiple (both required); ETFs get no special case (per-name baseline self-normalizes SPY-class chatter); absence from reddit.db or `n < crowding_min_n` = calm = pass free (no data_missing noise); baseline excludes the latest snapshot; z only crosses the mask as data (`MASK_DETAIL_KEYS`), Tier 2 stays advisory/τ-filtered by construction.

- [ ] **Step 1: Failing tests.**

```python
# test_promote_extract.py
def test_load_crowding_latest_vs_trailing_baseline(tmp_path):
    # seed reddit.db: 6 daily all-stocks snapshots; GME mentions
    # [10,10,10,10,10] then latest 90 rank 2 -> baseline_mean 10, n 5, rank 2
def test_load_crowding_ignores_other_filters(tmp_path):   # 4chan rows don't leak
def test_load_crowding_window_excludes_older_than_cutoff(tmp_path):

# test_promote_gates.py
def _crowd(rank=2, mentions=90, mean=10.0, std=2.0, n=10):
    return {"GME": {"rank": rank, "mentions": mentions,
                    "baseline_mean": mean, "baseline_std": std, "n": n}}
def test_gate_crowding_kills_hot_name():
    passed, rej = gates.gate_crowding([_group_named("GME")], _crowd(), cfg)
    assert rej[0]["gate"] == "crowding"
def test_gate_crowding_rank_alone_not_enough():      # rank 2, mentions 1.5x norm
def test_gate_crowding_mentions_alone_not_enough():  # 9x norm but rank 40
def test_gate_crowding_absent_name_passes_free():
def test_gate_crowding_thin_baseline_passes():       # n < crowding_min_n
def test_gate_crowding_appends_attention_z_detail():
    passed, _ = gates.gate_crowding([_group_named("GME")],
                                    _crowd(rank=40, mentions=14), cfg)
    assert {"retail_attention_z": 2.0} in passed[0]["details"]

# test_promote_run.py
def test_run_missing_reddit_db_warns_and_passes_all(tmp_path, capsys):
# test_gate_mask.py
def test_masked_view_carries_retail_attention_z():
# test_schedule_catalog.py
def test_reddit_daily_job_registered():
def test_promote_chain_includes_reddit():
def test_argv_for_promote_passes_reddit_db():
```

- [ ] **Step 2: Verify failures.**
- [ ] **Step 3: Implement.** `extract.load_crowding`:

```python
def load_crowding(conn, now_iso, baseline_days) -> dict:
    """Per-ticker attention: latest all-stocks rank/mentions + the name's own
    trailing baseline (mean/std over prior snapshots in the window). Names
    absent from the latest snapshot are simply absent (= calm)."""
    latest = conn.execute(
        "SELECT id, captured_at FROM snapshots WHERE filter=? "
        "ORDER BY captured_at DESC, id DESC LIMIT 1",
        (catalog.CROWDING_FILTER,)).fetchone()
    if latest is None:
        return {}
    latest_id, latest_at = latest
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=baseline_days)).isoformat()
    out = {}
    for ticker, rank, mentions in conn.execute(
            "SELECT ticker, rank, mentions FROM observations "
            "WHERE snapshot_id=?", (latest_id,)):
        out[pipeline_common.normalize_ticker(ticker)] = {
            "rank": rank, "mentions": mentions,
            "baseline_mean": None, "baseline_std": None, "n": 0, "_hist": []}
    for ticker, mentions in conn.execute(
            "SELECT o.ticker, o.mentions FROM observations o "
            "JOIN snapshots s ON s.id = o.snapshot_id "
            "WHERE s.filter=? AND s.id != ? AND s.captured_at >= ? "
            "AND s.captured_at < ?",
            (catalog.CROWDING_FILTER, latest_id, cutoff, latest_at)):
        t = pipeline_common.normalize_ticker(ticker)
        if t in out and mentions is not None:
            out[t]["_hist"].append(mentions)
    for c in out.values():
        hist = c.pop("_hist")
        c["n"] = len(hist)
        if hist:
            mean = sum(hist) / len(hist)
            c["baseline_mean"] = mean
            c["baseline_std"] = (sum((x - mean) ** 2 for x in hist)
                                 / len(hist)) ** 0.5
    return out
```

`gates.gate_crowding`:

```python
def gate_crowding(groups, crowding: dict, cfg) -> tuple:
    """G3b: pump defense — kill when attention is extreme relative to the
    name's OWN baseline (rank floor AND multiple-of-norm; absolute mentions
    can't work, SPY is always chattered about). Absence from reddit.db or a
    thin baseline = calm = pass free. Survivors with a usable baseline get
    retail_attention_z appended to details for the Stage 3 mask (Tier 2)."""
    passed, rejections = [], []
    for g in groups:
        c = crowding.get(g["instrument"])
        if c is None or c["n"] < cfg.crowding_min_n or not c["baseline_mean"]:
            passed.append(g)
            continue
        hot = (c["rank"] is not None and c["rank"] <= cfg.crowding_rank_max
               and (c["mentions"] or 0)
               >= cfg.crowding_mult * c["baseline_mean"])
        if hot:
            rejections.append(_reject(
                g, "crowding",
                f"rank {c['rank']} <= {cfg.crowding_rank_max} and mentions "
                f"{c['mentions']} >= {cfg.crowding_mult}x baseline "
                f"{c['baseline_mean']:.1f}"))
            continue
        if c["baseline_std"]:
            g = dict(g)
            g["details"] = list(g["details"]) + [{
                "retail_attention_z": round(
                    (c["mentions"] - c["baseline_mean"]) / c["baseline_std"], 2)}]
        passed.append(g)
    return passed, rejections
```

`run.py`: `--reddit-db` default `"reddit.db"`; tolerant loader (missing → `{}` + `warning: reddit db unavailable: <TypeName>`); call between G3 and G4. Scheduler catalog: `Job("reddit", "reddit", "daily")` before the chains; `DB_FILES["reddit"] = "reddit.db"`; promote `after=("leads", "reddit")`; `argv_for` promote adds `["--reddit-db", d("reddit.db")]` (no `--keep-days` → long retention by default). Gate catalog `MASK_DETAIL_KEYS += ("retail_attention_z",)`.

- [ ] **Step 4: Full suite green.**
- [ ] **Step 5: Docs** — DEFENSES_ROADMAP both tiers + plumbing → ✅ with pins; FOLLOWUPS §4 long-retention list gains reddit.db.
- [ ] **Step 6: Commit** `feat(promote,gate,scheduler): two-tier crowding defense off reddit.db baselines`

---

### Task 4: `portfolio` screener + `account-positions` skill

**Files:**
- Create: `sources/screeners/portfolio_screener/{__init__.py,catalog.py,fetch.py,db.py,run.py}`
- Create: `.claude/skills/account-positions/SKILL.md`
- Modify: `registry.py` (register `portfolio`)
- Modify: `docs/CLAUDE_ROADMAP.md` (status ✅; downstream integrations stay follow-ons)
- Test: `tests/test_portfolio_fetch.py`, `tests/test_portfolio_db_schema.py`, `tests/test_portfolio_db_write.py`, `tests/test_portfolio_db_views.py`, `tests/test_portfolio_run.py`, `tests/test_registry.py`

**Interfaces:**
- Produces: dispatcher `main.py portfolio --db portfolio.db --input <path|->` consuming one combined JSON doc `{"account": {...}, "positions": [...]}` (written by the skill from Robinhood MCP output).
- Produces: `fetch.parse_snapshot(doc) -> (account: dict, positions: list[dict])` — pure, tolerant numeric coercion, raises `ValueError` on a non-dict doc; positions missing `symbol` or `quantity` are skipped (skip-and-continue, counted).
- Produces: `db` schema — `snapshots(id, captured_at, position_count)`, `account(snapshot_id, equity REAL, cash REAL, buying_power REAL)`, `positions(snapshot_id, symbol TEXT, quantity REAL, avg_cost REAL, market_value REAL, PRIMARY KEY(snapshot_id, symbol))`, views `v_latest_account`, `v_latest_positions`, own cascade `prune`.
- Guiding invariant honored: Claude fetches via MCP, but data enters as a file through a normal screener — downstream stays offline-testable.

- [ ] **Step 1: Failing tests.**

```python
# test_portfolio_fetch.py
DOC = {"account": {"equity": "205.37", "cash": 12.4, "buying_power": "12.40"},
       "positions": [
           {"symbol": "gld", "quantity": "0.5", "average_buy_price": "301.2",
            "market_value": 155.0},
           {"symbol": "AAPL"},                       # no quantity -> skipped
           {"quantity": 3}]}                          # no symbol -> skipped
def test_parse_snapshot_coerces_and_normalizes():
    account, positions = fetch.parse_snapshot(DOC)
    assert account == {"equity": 205.37, "cash": 12.4, "buying_power": 12.4}
    assert positions == [{"symbol": "GLD", "quantity": 0.5,
                          "avg_cost": 301.2, "market_value": 155.0}]
def test_parse_snapshot_rejects_non_dict():
def test_parse_snapshot_missing_account_yields_nulls():

# test_portfolio_run.py
def test_run_ingests_stdin_doc(tmp_path, monkeypatch, capsys):
    # --input - ; assert snapshot row + account row + position rows
def test_run_bad_json_prints_type_name_only(tmp_path, capsys):
    # stderr contains 'JSONDecodeError', not the payload
```

Plus schema/write/views/prune tests following the standard screener test shapes, and a `test_registry.py` line asserting `"portfolio" in REGISTRY`.

- [ ] **Step 2: Verify failures.**
- [ ] **Step 3: Implement** the four files. `catalog.py` holds the field maps:

```python
ACCOUNT_FIELDS = ("equity", "cash", "buying_power")
# MCP position payloads vary; first match wins per target field.
POSITION_FIELDS = {"quantity": ("quantity", "shares"),
                   "avg_cost": ("average_buy_price", "avg_cost"),
                   "market_value": ("market_value", "equity")}
```

`fetch.parse_snapshot` uses a `_num(x)` helper (`float(x)` for int/float/numeric-str, else `None`), `normalize_ticker`-style symbol uppercase via `pipeline`-free local `.strip().upper()` (screeners don't import pipeline). `run.run(db_path, doc, now_iso=None)` + `main(argv)` reading `--input` (file or stdin), erroring with type names only. Register in `registry.py`.

- [ ] **Step 4: Suite green.**
- [ ] **Step 5: Write the skill** `.claude/skills/account-positions/SKILL.md`:

```markdown
---
name: account-positions
description: Snapshot live Robinhood account state (positions, equity, cash, buying power) into data/portfolio.db via the portfolio screener. Use when the user asks to sync/refresh account positions or before sizing reviews.
---
1. Call Robinhood MCP: get_accounts, get_portfolio, get_equity_positions.
2. Build one JSON doc {"account": {equity, cash, buying_power}, "positions": [...]}
   in the scratchpad (never paste raw MCP payloads into the conversation).
3. Run: uv run python main.py portfolio --db data/portfolio.db --input <scratch>/portfolio.json
4. Report: snapshot id, position count, equity/cash/buying_power.
Secret hygiene: on MCP or CLI errors report exception type names only.
Read-only rule: this skill writes ONLY portfolio.db, through the dispatcher.
```

- [ ] **Step 6: Docs** — CLAUDE_ROADMAP `account-positions` → ✅ (command + package built; the four downstream integrations remain listed as follow-ons). **Step 7: Commit** `feat(portfolio): account snapshot screener + account-positions skill`

---

### Task 5: `paper-trail-report` skill

**Files:**
- Create: `.claude/skills/paper-trail-report/SKILL.md`
- Modify: `docs/CLAUDE_ROADMAP.md` (status ✅)

No code, no tests — this is a read-only Claude procedure. The skill instructs:

1. Read, via `sqlite3 'file:data/<db>?mode=ro'` (URI read-only — zero-writes is structural):
   - `candidates.db`: `v_rejection_summary`, latest `rejections` rows (gate, reason)
   - `gate.db`: `v_gate_alerts`, `v_delta_history` (last ~10 runs), `v_decision_makers`
   - `schedule.db`: `v_failures`, `v_recent_runs`
   - `schedule.log`: tail ~200 lines for `warning:` skip-and-continue lines
2. Produce the digest in the roadmap's sketch shape: per run — promoted X of Y leads, kills by gate with plain-English reasons, gate vetoes/clamps/discarded-vetoes with the τ context, scheduler failures, and log warnings; end with "worth a look" bullets (e.g. a discarded-veto streak suggesting τ review).
3. Read-only by design: the skill must never mutate any DB (mode=ro enforces it).

- [ ] **Step 1: Write SKILL.md** with the exact queries inline. **Step 2: Exercise it end-to-end once** against the real `data/` DBs (they exist from the 2026-07-05 first run). **Step 3: Docs + commit** `feat(skills): paper-trail-report read-only digest`

---

### Task 6: launchd tick (deployment)

**Files:**
- Create: `deploy/schedule-tick.sh` (chmod +x)
- Create: `deploy/com.agentic-trading-bot.schedule.plist`
- Modify: `pipeline/scheduler/run.py` (docstring: Linux → cron+flock; macOS → launchd plist, lock unnecessary by design)
- Modify: `docs/DEPLOYMENT_ROADMAP.md` (status ✅)

`deploy/schedule-tick.sh`:

```bash
#!/bin/sh
# launchd tick: single-runner is guaranteed by launchd (it never starts a
# second instance of a running label) — no flock needed on macOS.
set -eu
cd "$(dirname "$0")/.."
# claude (gate backend) + uv live outside launchd's minimal PATH
PATH="$HOME/.claude/local:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export PATH
set -a; . ./.env; set +a
exec /opt/homebrew/bin/uv run python main.py schedule --run
```

Plist: `Label com.agentic-trading-bot.schedule`, `ProgramArguments [/bin/sh, <abs>/deploy/schedule-tick.sh]`, `StartInterval 900`, `StandardOutPath`/`StandardErrorPath` → `<abs>/schedule.log` (stderr captured — the skip-and-continue warnings only exist there), `WorkingDirectory <abs>`.

- [ ] **Step 1: Write both files** (resolve the real `claude` install dir first — the session shim path is not durable; check `ls ~/.claude/local/claude || command -v claude` outside the shim).
- [ ] **Step 2: Verify the script runs standalone:** `sh deploy/schedule-tick.sh` (expect a normal scheduler tick against `data/`; confirm scheduler default `--data-dir` matches — check `schedule --help`; pass `--data-dir data` in the script if the default is CWD).
- [ ] **Step 3: Install + load:** copy plist to `~/Library/LaunchAgents/`, `launchctl bootstrap gui/$(id -u) ...`, confirm with `launchctl list | grep agentic-trading-bot`; reversal is `launchctl bootout`.
- [ ] **Step 4: Docstring note + docs** (known limitation restated: LaunchAgent needs a logged-in, awake session for the 15:30 ET window). **Commit** `feat(deploy): launchd schedule tick for macOS`

---

### Task 7: ApeWisdom backfill decision (old repo)

**Files:**
- Scratchpad-only backfill script (not committed — one-off migration)
- Modify: `docs/DEPLOYMENT_ROADMAP.md` (resolve the open 💡)

Findings already in hand: `~/Desktop/agentic-trades/tools/data/reddit_velocity.db` holds `mentions(ts, ticker, sub, mentions, upvotes)` hourly 2026-06-20 → 2026-07-05 for subs `wallstreetbets`/`4chan`/`stocks` — **no rank, different universe than `all-stocks`**.

**Decision (research-and-recommend):** backfill, but under the original sub names as filters — never into `all-stocks`. Rationale: the crowding baseline reads `all-stocks` only; old 3-sub counts are scale-incompatible (a ~1.5× universe bias would eat half the 3× kill headroom and false-kill live top-10 names). The `4chan` series IS the same ApeWisdom universe as the live `4chan` filter, so it merges cleanly. The crowding gate self-arms after `crowding_min_n` (5) daily `all-stocks` snapshots — about a week — which is the accepted cost of unbiased baselines. Preserved history stays queryable for Stage 6 calibration.

- [ ] **Step 1:** Scratchpad script: downsample to one snapshot per (day, sub) (max `ts` per day), rank by mentions desc within each synthesized snapshot, `mentions_24h_ago`/`rank_24h_ago` from the prior day's snapshot; insert via the reddit screener's own `db.write_snapshot`/`upsert_tickers` against `data/reddit.db` with `captured_at` = source `ts`.
- [ ] **Step 2:** Verify: `v_history` returns sane per-ticker series for GME/SPY; live filters unaffected (`SELECT DISTINCT filter FROM snapshots`).
- [ ] **Step 3:** DEPLOYMENT_ROADMAP: resolve the open item with the decision + note the old repo is now safe to delete (user's call, not ours). **Commit** (docs only) `docs(deploy): resolve ApeWisdom backfill — imported under original sub filters`

---

### Task 8: Final sweep

- [ ] Full suite: `uv run pytest -q` green.
- [ ] `uv run python main.py --list` shows `portfolio`.
- [ ] Cross-doc consistency: CLAUDE_ROADMAP / DEFENSES_ROADMAP / DEPLOYMENT_ROADMAP / FOLLOWUPS all reflect shipped state; PIPELINE_ROADMAP untouched (already complete).
- [ ] Merge the feature branch into main (no co-author, --no-gpg-sign).

## Self-Review

- Spec coverage: every 💡 in CLAUDE/DEFENSES/DEPLOYMENT roadmaps maps to Tasks 1–7; FOLLOWUPS §3 idea backlog and 🟠 intentionally-deferred sub-items are explicitly out of scope (docs mark them deferred by choice); calibration questions are empirical and out of scope.
- Type consistency: `complete_cli` matches the `complete(system, user, model=, api_key=)` call sites in `run.py`; `fractional` flows candidates→v_gate_input→gate_runs→resolve/replay as one boolean; `gate_crowding` consumes exactly `load_crowding`'s dict shape.
- Placeholders: test lists name concrete behaviors with assertions; code blocks are the intended implementations.

# Research Corpus (Unit 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `research-ticker` an attributed, coverage-honest way to search a company's
earnings-call transcripts, without ever letting a zero-hit search be written up as "management
never said this."

**Architecture:** Split on **purity, not subject**. The three things whose silent wrongness is
dangerous — speaker attribution, the concept lexicon, and coverage arithmetic — are pure
functions over already-decoded dicts, so they land in `tools/research/transcripts.py` beside
`tools/valuation/reverse_dcf.py` (no network, no DB, no clock) and are pinned by fixtures. The
76-call fetch loop is trivial, regenerated per session, and stays as prose in the skill's
`references/disclosure-hunt.md`. No new code lands under `sources/`; the single exception is
Task 5's one-line User-Agent change to the existing `probe.py`.

**Tech Stack:** Python 3.12, stdlib only (`re`, `dataclasses`, `datetime.date`). `pytest` for
tests. Decoding is already shipped: `sources.screeners.stock_analysis_screener.probe.page_data`.

## Global Constraints

- **Stdlib only.** Zero runtime third-party dependencies. Do not `uv add` anything.
- **`tools/` is pure:** no network, no DB, no clock. Every input is an argument. `coverage()`
  takes `ipo_date` as a parameter; it never fetches it and never calls `date.today()`.
- **ruff `line-length = 100`**; lint rules include `I` (import sort), `B`, `UP`, `SIM`, and
  **`DTZ`** (naive-datetime ban — `DTZ` is *not* ignored outside `tests/*`). `date.fromisoformat`
  is fine; `datetime.now()` is not.
- **mypy covers `tools`** with `check_untyped_defs`, `no_implicit_optional`,
  `warn_unused_ignores`. Annotate every public signature.
- **All four gates must pass before every commit:**
  `uv run pytest && uv run ruff check && uv run ruff format --check && uv run mypy`
  The pre-commit hook (`.githooks/pre-commit`) runs them in ~2s.
- **Do not add yourself as a commit co-author.**
- **The corpus proves presence, never absence.** Zero hits means *"not found in the N calls
  covering `first`–`last`"* — never "never disclosed." This rule is the point of the whole unit;
  do not soften it in prose.
- Test file naming follows `tests/test_reverse_dcf.py` (bare module name, not path-mirrored).

---

## File Structure

| File | Responsibility |
|---|---|
| Create: `tools/research/__init__.py` | empty package marker (mirrors `tools/valuation/__init__.py`) |
| Create: `tools/research/transcripts.py` | pure: `flatten_turn`, `classify_side`, `coverage`, `scan_concepts`, `LEXICON` |
| Create: `tests/test_transcripts.py` | fixtures pinning every trap found by adversarial review |
| Modify: `.claude/skills/research-ticker/references/disclosure-hunt.md` | the fetch loop + the judgment rules |
| Modify: `.claude/skills/research-ticker/SKILL.md` | one Phase 2 pointer |
| Modify: `sources/screeners/stock_analysis_screener/probe.py:19` | one line: descriptive User-Agent |
| Modify: `plans/README.md` | index row |

Task 1 (attribution) and Task 2 (coverage) are independent. Task 3 (lexicon) depends on nothing
in Tasks 1–2 at the type level but is scanned over management-side text, so it reads naturally
after Task 1. Task 4 (prose) depends on all three being named and stable. **Task 5 (User-Agent)
is independent of everything and may be done first** — it is placed last only because it is the
smallest, and it must land before the 77-request loop in Task 4 is used in anger.

---

## Task 1: Attribution and flattening

**Files:**
- Create: `tools/research/__init__.py`
- Create: `tools/research/transcripts.py`
- Test: `tests/test_transcripts.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `flatten_turn(turn: dict) -> str`
  - `classify_side(turn: dict, issuer: str) -> str` returning `"management"`, `"outside"`, or
    `"unattributed"`
  - `issuer_from_turns(turns: Sequence[dict]) -> str | None`
  - `MANAGEMENT = "management"`, `OUTSIDE = "outside"`, `UNATTRIBUTED = "unattributed"`

**Background the implementer needs.** A transcript turn looks like this, decoded:

```python
{"speakerName": "Hans Vestberg", "role": "Chairman and CEO", "company": "Verizon",
 "paragraphs": [[{"text": "We took share.", "startSec": 1.0, "endSec": 2.0},
                 {"text": "A lot of it.",   "startSec": 2.0, "endSec": 3.0}]]}
```

`paragraphs` is **`list[list[dict]]`** — a list of paragraphs, each a list of *sentences*. Two
levels. Writing `p["text"]` raises `TypeError: list indices must be integers`.

Attribution keys on `company`, **never** `role`. Verified against the live feed:
- `role` is free text: `Analyst`, `Managing Director`, `MD - Global Investment Research`,
  `Operator`, `None`.
- `role` is provably wrong — on Verizon's Q1 2022 call, CFO Matt Ellis is tagged
  `role="Analyst", company="Verizon"`.
- On the 76-call VZ corpus, 573 turns have `company is None`: 559 with `role is None` and **14
  with `role="Operator"`**. So `role is None` does *not* identify unattributed turns.

**Name matching is harder than it looks. Three rules were tried; only the third survives.**

*Exact equality* fails: CROX tags its CEO `company="Crocs"` and its CFO `company="Crocs, Inc."`
in the same call.

*Containment in either direction, after stripping legal suffixes,* also fails. Verizon's turns
carry five different strings — `Verizon`, `Verizon Communications`, `Verizon Communications Inc.`,
`Verizon Consumer`, `Verizon Consumer Group`. Pass the long legal name (however you obtained it —
`data/stocks.db` has no name column; see the final-review entry below) and
`"verizon communications"` neither contains nor is contained by `"verizon consumer"`, so **115
turns by Verizon's own Consumer Group CEO classify as analyst questions.** Measured, not guessed.

*Compare the first token, allowing either to be a prefix of the other.* This is the rule. It
captures all five Verizon variants from either issuer spelling, matches `ExxonMobil` against
`Exxon Mobil Corporation`, and — critically — keeps `JPMorgan` out of `Morgan Stanley`, where a
substring test on the first token would fuse them (`"morgan" in "jpmorgan"`), but a prefix test
does not (`"jpmorgan".startswith("morgan")` is False).

Its one known collision: an issuer whose first token is generic. `Bank of New York` classifies as
management on `Bank of America`'s call. Documented, not fixed — pass a distinctive issuer name,
and eyeball the `outside` firm list.

`issuer_from_turns` exists so callers need not guess the spelling at all: the modal `company` on
a call is the issuer, because management speaks far more than any single bank (VZ: 3,234 turns vs
Morgan Stanley's 383).

- [ ] **Step 1: Write the failing test**

Create `tests/test_transcripts.py`:

```python
import pytest

from tools.research.transcripts import (
    MANAGEMENT,
    OUTSIDE,
    UNATTRIBUTED,
    classify_side,
    flatten_turn,
    issuer_from_turns,
)

VZ_LONG = "Verizon Communications Inc."


def turn(company: object, role: object = None, text: str = "hi") -> dict:
    return {
        "speakerName": "X",
        "role": role,
        "company": company,
        "paragraphs": [[{"text": text, "startSec": 0.0, "endSec": 1.0}]],
    }


def test_flatten_joins_sentences_within_a_paragraph() -> None:
    t = {"paragraphs": [[{"text": "We took share."}, {"text": "A lot of it."}]]}
    assert flatten_turn(t) == "We took share. A lot of it."


def test_flatten_separates_paragraphs() -> None:
    t = {"paragraphs": [[{"text": "One."}], [{"text": "Two."}]]}
    assert flatten_turn(t) == "One.\n\nTwo."


def test_flatten_tolerates_a_turn_with_no_paragraphs() -> None:
    assert flatten_turn({"speakerName": "Operator"}) == ""


def test_management_is_recognised_despite_a_mislabelled_role() -> None:
    # Verizon Q1 2022: CFO Matt Ellis is tagged role="Analyst". `company` is the truth.
    assert classify_side(turn("Verizon", role="Analyst"), "Verizon") == MANAGEMENT


def test_legal_suffix_variants_are_the_same_issuer() -> None:
    # CROX tags its CEO "Crocs" and its CFO "Crocs, Inc." in the same call.
    assert classify_side(turn("Crocs"), "Crocs, Inc.") == MANAGEMENT
    assert classify_side(turn("Crocs, Inc."), "Crocs") == MANAGEMENT


def test_a_longer_issuer_name_still_matches() -> None:
    assert classify_side(turn("Verizon"), VZ_LONG) == MANAGEMENT


def test_a_sibling_subsidiary_is_still_management() -> None:
    # "verizon communications" neither contains nor is contained by "verizon consumer".
    # 115 real VZ turns by the Consumer Group CEO hang on this.
    assert classify_side(turn("Verizon Consumer Group"), VZ_LONG) == MANAGEMENT
    assert classify_side(turn("Verizon Consumer"), VZ_LONG) == MANAGEMENT


def test_a_concatenated_issuer_name_matches_the_spaced_one() -> None:
    assert classify_side(turn("ExxonMobil"), "Exxon Mobil Corporation") == MANAGEMENT


def test_an_outside_firm_is_not_management() -> None:
    goldman = turn("Goldman Sachs", role="MD - Global Investment Research")
    assert classify_side(goldman, "Verizon") == OUTSIDE


def test_jpmorgan_is_not_morgan_stanley() -> None:
    # "morgan" is a substring of "jpmorgan"; it is not a prefix of it. Match on prefix.
    assert classify_side(turn("JPMorgan"), "Morgan Stanley") == OUTSIDE
    assert classify_side(turn("J.P. Morgan"), "Morgan Stanley") == OUTSIDE


def test_morgan_stanley_is_management_only_on_its_own_call() -> None:
    ms = turn("Morgan Stanley")
    assert classify_side(ms, "Morgan Stanley") == MANAGEMENT
    assert classify_side(ms, "Verizon") == OUTSIDE


def test_operator_turns_are_unattributed_even_though_role_is_set() -> None:
    # 14 VZ turns carry role="Operator" with company=None. Never key on `role is None`.
    assert classify_side(turn(None, role="Operator"), "Verizon") == UNATTRIBUTED


def test_null_role_and_null_company_is_unattributed() -> None:
    assert classify_side(turn(None, role=None), "Verizon") == UNATTRIBUTED


def test_blank_company_is_unattributed() -> None:
    assert classify_side(turn("   "), "Verizon") == UNATTRIBUTED


def test_classify_requires_a_non_empty_issuer() -> None:
    with pytest.raises(ValueError, match="issuer"):
        classify_side(turn("Verizon"), "")


def test_issuer_from_turns_picks_the_modal_company() -> None:
    turns = [turn("Verizon"), turn("Verizon"), turn("Morgan Stanley"), turn(None)]
    assert issuer_from_turns(turns) == "Verizon"


def test_issuer_from_turns_is_none_when_nobody_is_attributed() -> None:
    assert issuer_from_turns([turn(None), turn("  ")]) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_transcripts.py -q`
Expected: `ModuleNotFoundError: No module named 'tools.research'`

- [ ] **Step 3: Write minimal implementation**

Create `tools/research/__init__.py` as an **empty file** (zero bytes), mirroring
`tools/valuation/__init__.py`.

Create `tools/research/transcripts.py`:

```python
"""Pure helpers for reading a company's earnings-call transcript corpus.

A transcript contains management *and* the analysts interrogating them. A hit for
"market share" is a disclosure if the CFO said it and a question if Goldman asked
it; inverting that inverts the finding. So attribution is the correctness property
of this module, and it keys on ``company`` — never on ``role``, which is free text
and provably wrong (Verizon's CFO is tagged ``role="Analyst"`` on one call).

Pure: no network, no database, no wall clock. Every input is an argument. The fetch
loop that produces these dicts lives in the research-ticker skill's prose, and the
decoding lives in ``stock_analysis_screener.probe``.
"""

import re
from collections import Counter
from collections.abc import Sequence

MANAGEMENT = "management"
"""The issuer's own people. A statement here is a disclosure."""

OUTSIDE = "outside"
"""A sell-side analyst or other non-issuer. A statement here is a question, not a fact."""

UNATTRIBUTED = "unattributed"
"""Operator, moderator, or an unnamed speaker. ``company`` is absent."""

_LEGAL_SUFFIXES = frozenset(
    {
        "inc",
        "incorporated",
        "corp",
        "corporation",
        "co",
        "company",
        "ltd",
        "limited",
        "llc",
        "lp",
        "plc",
        "sa",
        "nv",
        "ag",
        "group",
    }
)
"""Dropped from the tail of a company name before comparison.

(Written exploded because `ruff format` requires it here and `SIM905` forbids the
compact `"...".split()` alternative. Do not "tidy" this.)

Note ``holdings`` is deliberately absent: stockanalysis's ``transcriptMeta.title``
for XOM reads "ExxonMobil Holdings Corporation", which the company is not — never
derive the issuer name from that field, so the suffix never needs stripping.
"""


def flatten_turn(turn: dict) -> str:
    """Join a turn's nested sentences into one string.

    ``paragraphs`` is ``list[list[dict]]`` — a list of paragraphs, each a list of
    sentences ``{text, startSec, endSec}``. Two levels, not one. Sentences join with
    a space, paragraphs with a blank line. A turn with no ``paragraphs`` yields "".
    """
    paragraphs = turn.get("paragraphs") or []
    return "\n\n".join(
        " ".join(sentence["text"] for sentence in paragraph) for paragraph in paragraphs
    )


def _name_key(name: str) -> str:
    """The first significant word of a company name, lowercased.

    Strips punctuation and trailing legal suffixes, then takes the leading token:
    ``"Crocs, Inc."`` and ``"Crocs"`` both key to ``"crocs"``; ``"Verizon Consumer
    Group"`` and ``"Verizon Communications Inc."`` both key to ``"verizon"``.
    """
    words = re.sub(r"[^a-z0-9 ]+", " ", name.lower()).split()
    while words and words[-1] in _LEGAL_SUFFIXES:
        words.pop()
    return words[0] if words else ""


def classify_side(turn: dict, issuer: str) -> str:
    """Return ``MANAGEMENT``, ``OUTSIDE``, or ``UNATTRIBUTED`` for one turn.

    Keys on ``company``. A blank or missing ``company`` means the speaker is the
    operator, a moderator, or unnamed — never assume such a turn is management, and
    never test ``role is None`` (14 Verizon operator turns carry ``role="Operator"``).

    Two names are the same issuer when one's leading word is a prefix of the other's.
    Containment in either direction is not enough: a company's turns carry sibling
    subsidiary names (``"Verizon Consumer Group"`` beside ``"Verizon Communications
    Inc."``) that contain neither each other nor the legal name. Prefix, not substring,
    because ``"morgan"`` is a substring of ``"jpmorgan"`` but not a prefix of it — so
    JPMorgan's analysts stay outside Morgan Stanley's own call.

    Known collision: an issuer whose leading word is generic. ``"Bank of New York"``
    reads as management on ``"Bank of America"``'s call. Pass a distinctive issuer name
    — ``issuer_from_turns`` gives you the one the corpus itself uses — and check the
    ``OUTSIDE`` firm list before trusting a count.

    Raises ValueError on an empty ``issuer``, which would otherwise match everything.
    """
    issuer_key = _name_key(issuer)
    if not issuer_key:
        raise ValueError(f"issuer must be a non-empty company name, got {issuer!r}")

    company = turn.get("company")
    if not isinstance(company, str) or not company.strip():
        return UNATTRIBUTED

    company_key = _name_key(company)
    if not company_key:
        return UNATTRIBUTED
    if issuer_key.startswith(company_key) or company_key.startswith(issuer_key):
        return MANAGEMENT
    return OUTSIDE


def issuer_from_turns(turns: Sequence[dict]) -> str | None:
    """The most common ``company`` across turns — the issuer, or None if nobody is named.

    Management speaks far more than any single bank on its own call (Verizon: 3,234
    management turns against Morgan Stanley's 383), so the mode is the issuer. Use this
    rather than guessing a spelling, and rather than ``transcriptMeta.title``, which is
    wrong for XOM.
    """
    named = Counter(
        turn["company"]
        for turn in turns
        if isinstance(turn.get("company"), str) and turn["company"].strip()
    )
    return named.most_common(1)[0][0] if named else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_transcripts.py -q`
Expected: `17 passed`

- [ ] **Step 5: Run the full gates**

Run: `uv run pytest -q && uv run ruff check && uv run ruff format --check && uv run mypy`
Expected: all pass. If `ruff format --check` fails, run `uv run ruff format` and re-check.

- [ ] **Step 6: Commit**

```bash
git add tools/research/__init__.py tools/research/transcripts.py tests/test_transcripts.py
git commit --no-gpg-sign -m "feat(research): attribute transcript turns by company, never by role"
```

---

## Task 2: Coverage — the honest denominator

**Files:**
- Modify: `tools/research/transcripts.py` (append)
- Test: `tests/test_transcripts.py` (append)

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces:
  - `@dataclass(frozen=True) class Coverage` with fields
    `n_calls: int`, `first: str | None`, `last: str | None`, `ipo_date: str | None`,
    `uncovered_years: float | None`
  - `coverage(index: list[dict], ipo_date: str | None = None) -> Coverage`

**Background.** This is the whole point of the unit. Transcript depth tracks Quartr's onboarding
date, **not** company history, and nothing in the payload admits it — there is no `fullCount`, no
coverage marker, and `?page=2` degrades silently to the `{info}` gate rather than paginating.
Verified live 2026-07-10:

| Ticker | Calls | Earliest |
|---|---|---|
| NVDA | 148 | 2010-05-13 |
| AAPL | 74 | 2011-04-20 |
| VZ | 76 | 2019-04-23 |
| IBM | 40 | 2021-04-19 |
| **T** | **12** | **2021-03-12** |
| BABA, TSM, SAP, SONY | **0** | — (`{info}`; no corpus exists) |

A zero-hit grep over AT&T's twelve calls says nothing about AT&T's history. `coverage()` exists so
the skill can print the denominator before anyone reads a hit list.

Each index row is `{"id": ..., "eventDate": "2026-04-27", "quarterLabel": "Q1 2026",
"detailSlug": "...", "eventTitle": "..."}`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_transcripts.py` (and extend the import block at the top to include
`Coverage` and `coverage`):

```python
def index(*dates: str) -> list[dict]:
    return [{"eventDate": d, "quarterLabel": "Q1", "detailSlug": f"s-{d}"} for d in dates]


def test_coverage_reports_span_and_count() -> None:
    cov = coverage(index("2021-03-12", "2026-06-09", "2023-01-01"))
    assert cov.n_calls == 3
    assert cov.first == "2021-03-12"
    assert cov.last == "2026-06-09"


def test_coverage_of_an_empty_index_is_not_an_error() -> None:
    # BABA, TSM, SAP, SONY have no corpus at all. This is a normal outcome.
    cov = coverage([])
    assert cov == Coverage(n_calls=0, first=None, last=None, ipo_date=None, uncovered_years=None)


def test_uncovered_years_measures_the_gap_from_ipo_to_first_call() -> None:
    # AT&T: 12 calls from 2021, but listed long before.
    cov = coverage(index("2021-03-12"), ipo_date="1983-11-21")
    assert cov.uncovered_years == pytest.approx(37.3, abs=0.1)


def test_uncovered_years_is_none_without_an_ipo_date() -> None:
    assert coverage(index("2021-03-12")).uncovered_years is None


def test_uncovered_years_is_zero_when_coverage_predates_the_ipo() -> None:
    # Never report a negative gap; clamp at zero.
    cov = coverage(index("2010-05-13"), ipo_date="2012-01-01")
    assert cov.uncovered_years == 0.0


def test_uncovered_years_is_none_when_the_index_is_empty() -> None:
    assert coverage([], ipo_date="1983-11-21").uncovered_years is None


def test_coverage_ignores_rows_with_no_event_date() -> None:
    cov = coverage([{"eventDate": "2024-01-01"}, {"detailSlug": "orphan"}])
    assert cov.n_calls == 2
    assert cov.first == cov.last == "2024-01-01"


def test_coverage_rejects_a_malformed_event_date_without_ipo_date() -> None:
    with pytest.raises(ValueError, match="Jul 10, 2026"):
        coverage([{"eventDate": "Jul 10, 2026"}])


def test_coverage_rejects_a_malformed_event_date_with_ipo_date() -> None:
    with pytest.raises(ValueError, match="Jul 10, 2026"):
        coverage([{"eventDate": "Jul 10, 2026"}], ipo_date="1983-11-21")


def test_coverage_rejects_a_non_zero_padded_date_rather_than_misordering_it() -> None:
    # Raw-string sort would put "2024-1-5" after "2024-01-10" (lexicographic '1' > '0'),
    # reporting the wrong `last`. On Python 3.12, date.fromisoformat rejects the
    # non-zero-padded form outright, so the old wrong answer is impossible: it raises.
    with pytest.raises(ValueError, match="2024-1-5"):
        coverage([{"eventDate": "2024-1-5"}, {"eventDate": "2024-01-10"}])


def test_coverage_skips_an_empty_string_event_date_without_raising() -> None:
    cov = coverage([{"eventDate": ""}, {"eventDate": "2024-01-01"}])
    assert cov.n_calls == 2
    assert cov.first == cov.last == "2024-01-01"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_transcripts.py -q`
Expected: `ImportError: cannot import name 'Coverage'`

- [ ] **Step 3: Write minimal implementation**

Add to the imports at the top of `tools/research/transcripts.py`:

```python
from dataclasses import dataclass
from datetime import date
```

Append to `tools/research/transcripts.py`:

```python
_DAYS_PER_YEAR = 365.25


@dataclass(frozen=True)
class Coverage:
    """What the corpus actually spans — the denominator for every search over it."""

    n_calls: int
    first: str | None
    last: str | None
    ipo_date: str | None
    uncovered_years: float | None


def coverage(index: list[dict], ipo_date: str | None = None) -> Coverage:
    """Summarize a transcript index: how many calls, spanning what, missing how much.

    Transcript depth tracks the data provider's onboarding date, not the company's
    history, and the payload does not say so. AT&T returns twelve calls beginning in
    2021; Alibaba returns none at all. A search over such a corpus can establish that
    management *said* something, never that they never did — so callers must print
    this before they print a hit list.

    ``ipo_date`` is supplied by the caller (from ``data/stocks.db``), never fetched:
    this module has no network and no clock. ``uncovered_years`` is None when it is
    absent or when the corpus is empty, and clamps at 0.0 rather than going negative.

    Every truthy ``eventDate`` must be zero-padded ISO-8601 (``YYYY-MM-DD``); a falsy
    one ("", None, or a missing key) is skipped when computing the span but still
    counted in ``n_calls``. A present-but-malformed ``eventDate`` raises ``ValueError``
    naming the offending value. It is never silently skipped, and dates are never
    ordered as raw strings.
    """
    dated = [
        (date.fromisoformat(row["eventDate"]), row["eventDate"])
        for row in index
        if row.get("eventDate")
    ]
    dated.sort(key=lambda pair: pair[0])
    first = dated[0][1] if dated else None
    last = dated[-1][1] if dated else None

    uncovered: float | None = None
    if first is not None and ipo_date:
        gap_days = (date.fromisoformat(first) - date.fromisoformat(ipo_date)).days
        uncovered = max(0.0, gap_days / _DAYS_PER_YEAR)

    return Coverage(
        n_calls=len(index),
        first=first,
        last=last,
        ipo_date=ipo_date,
        uncovered_years=uncovered,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_transcripts.py -q`
Expected: `28 passed`

- [ ] **Step 5: Run the full gates**

Run: `uv run pytest -q && uv run ruff check && uv run ruff format --check && uv run mypy`
Expected: all pass. Note `date.fromisoformat` is not a `DTZ` violation; `datetime.now()` would be.

- [ ] **Step 6: Commit**

```bash
git add tools/research/transcripts.py tests/test_transcripts.py
git commit --no-gpg-sign -m "feat(research): report transcript coverage so absence is never inferred"
```

---

## Task 3: The concept lexicon and the rarity scan

**Files:**
- Modify: `tools/research/transcripts.py` (append)
- Test: `tests/test_transcripts.py` (append)

**Interfaces:**
- Consumes: nothing from Tasks 1–2 at the type level. Callers build `docs` from Task 1's
  `flatten_turn` + `classify_side`.
- Produces:
  - `LEXICON: dict[str, tuple[str, ...]]` — concept name → synonym regex patterns
  - `@dataclass(frozen=True) class ConceptStat` with fields
    `concept: str`, `df: int`, `n_docs: int`, `first: str | None`, `last: str | None`,
    `seasons: int`
  - `scan_concepts(docs: Sequence[tuple[str, str]], lexicon: Mapping[str, Sequence[str]] = LEXICON) -> list[ConceptStat]`
    where each `docs` element is `(event_date, management_side_text_of_one_call)`

**Background — two findings from adversarial review, both measured.**

*Raw hit counts lie.* Management repeats talking points quarterly, near-verbatim, from the same
two or three people. Grep hits are **not independent observations**. A naive grep of the VZ corpus
returns **82 raw hits** for "market share"; the honest figure is **39 documents across 8 years**.
So `scan_concepts` counts *documents* (`df`) and *distinct calendar years* (`seasons`), never hits.
A term repeated five times in one call counts once.

*Open-vocabulary rarity is not a filter.* A reviewer proposed surfacing every n-gram with
`df <= 3` as candidate search terms, to defeat anchoring. Measured on the VZ management corpus,
that selects **86% of bigrams (104,880) and 95% of trigrams** — natural language is Zipfian and
nearly every n-gram is rare. Rarity is meaningful only against a **curated, ticker-independent
lexicon with synonym sets**. That is what `LEXICON` is, and it is why it is code with tests rather
than a markdown table: a wrong synonym set silently prints *"not disclosed."*

Measured output on VZ (76 calls, management-side only), for calibration:

```
CAC                   0/76   -- never --                 ABSENT
unit economics        1/76   2026-04-27                  RARE
wallet share          3/76   2020-11-11 .. 2023-04-25    RARE
"we don't disclose"   3/76   2023-04-25 .. 2025-05-28    RARE
market share         39/76   2019-06-18 .. 2026-05-13    a talking point
churn                71/76   2019-04-23 .. 2026-05-18    constant
```

- [ ] **Step 1: Write the failing test**

By the end of this task the test file's import block must read exactly this (ruff `I001` sorts
`SCREAMING_CASE`, then `PascalCase`, then `snake_case`; `tools` is first-party here, so it takes
its own group after `pytest` — compare `tests/test_reverse_dcf.py`):

```python
import re

import pytest

from tools.research.transcripts import (
    LEXICON,
    MANAGEMENT,
    OUTSIDE,
    UNATTRIBUTED,
    ConceptStat,
    Coverage,
    classify_side,
    coverage,
    flatten_turn,
    issuer_from_turns,
    scan_concepts,
)
```

Append the tests below to `tests/test_transcripts.py`:

```python
def test_scan_counts_documents_not_hits() -> None:
    # "churn" five times in one call is ONE observation, not five.
    docs = [("2024-01-01", "churn churn churn churn churn")]
    (stat,) = scan_concepts(docs, {"churn": [r"churn"]})
    assert stat.df == 1
    assert stat.n_docs == 1


def test_scan_reports_span_and_distinct_seasons() -> None:
    docs = [
        ("2019-06-18", "we took market share"),
        ("2019-11-01", "market share again"),
        ("2026-05-13", "still taking market share"),
        ("2022-01-01", "nothing relevant here"),
    ]
    (stat,) = scan_concepts(docs, {"market share": [r"market share"]})
    assert stat.df == 3
    assert stat.n_docs == 4
    assert stat.first == "2019-06-18"
    assert stat.last == "2026-05-13"
    assert stat.seasons == 2  # 2019 and 2026 — not 3


def test_scan_reports_a_concept_that_never_appears() -> None:
    # An absent concept must still be reported, with df=0. Silence is the finding.
    docs = [("2024-01-01", "we discuss churn constantly")]
    (stat,) = scan_concepts(docs, {"CAC": [r"\bcac\b", r"customer acquisition cost"]})
    assert stat.df == 0
    assert stat.first is None
    assert stat.last is None
    assert stat.seasons == 0


def test_scan_matches_any_synonym_in_the_set() -> None:
    docs = [("2024-01-01", "our share of wallet is growing")]
    (stat,) = scan_concepts(docs, {"wallet share": [r"share of wallet", r"wallet share"]})
    assert stat.df == 1


def test_scan_is_case_insensitive() -> None:
    docs = [("2024-01-01", "Market Share leadership")]
    (stat,) = scan_concepts(docs, {"market share": [r"market share"]})
    assert stat.df == 1


def test_scan_orders_results_rarest_first() -> None:
    docs = [("2024-01-01", "churn"), ("2025-01-01", "churn and market share")]
    stats = scan_concepts(docs, {"churn": [r"churn"], "market share": [r"market share"]})
    assert [s.concept for s in stats] == ["market share", "churn"]


def test_scan_over_an_empty_corpus_reports_every_concept_as_absent() -> None:
    stats = scan_concepts([], {"churn": [r"churn"]})
    assert stats == [ConceptStat("churn", df=0, n_docs=0, first=None, last=None, seasons=0)]


def test_default_lexicon_covers_the_disclosure_probes() -> None:
    assert "market share" in LEXICON
    assert "we don't disclose" in LEXICON
    assert all(patterns for patterns in LEXICON.values())


def test_default_lexicon_patterns_all_compile() -> None:
    patterns = [p for ps in LEXICON.values() for p in ps]
    compiled = [re.compile(p) for p in patterns]
    assert len(compiled) == len(patterns)


def test_lexicon_separates_market_share_from_wallet_share() -> None:
    # A firm may disclose one and not the other; conflating them hides that.
    docs = [("2024-01-01", "our share of wallet grew")]
    stats = {s.concept: s.df for s in scan_concepts(docs, LEXICON)}
    assert stats["wallet share"] == 1
    assert stats["market share"] == 0
```

Add `import re` to the top of `tests/test_transcripts.py`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_transcripts.py -q`
Expected: `ImportError: cannot import name 'LEXICON'`

- [ ] **Step 3: Write minimal implementation**

Add `Mapping` to the existing `collections.abc` import at the top of
`tools/research/transcripts.py` (Task 1 already imported `Sequence`):

```python
from collections.abc import Mapping, Sequence
```

Append to `tools/research/transcripts.py`:

```python
LEXICON: dict[str, tuple[str, ...]] = {
    "market share": (r"market share", r"share of (?:the )?market", r"share gain"),
    "wallet share": (r"share of wallet", r"wallet share"),
    "penetration": (r"penetration",),
    "churn": (r"churn",),
    "ARPU": (r"\barpu\b", r"average revenue per (?:user|account|subscriber)"),
    "take rate": (r"take rate",),
    "attach rate": (r"attach rate", r"attachment rate"),
    "pricing power": (r"pricing power", r"price increase", r"pricing action"),
    "unit economics": (r"unit economics",),
    "cohort": (r"cohort",),
    "lifetime value": (r"lifetime value", r"\bltv\b", r"customer lifetime"),
    "CAC": (r"\bcac\b", r"customer acquisition cost"),
    "capacity utilization": (r"utilization",),
    "backlog": (r"backlog",),
    "retention": (r"retention",),
    "we don't disclose": (
        r"(?:don't|do not|won't|will not) (?:disclose|break out|provide)",
        r"no longer (?:report|disclose|break out)",
    ),
}
"""Curated, ticker-independent disclosure concepts, each with its synonym set.

Fixed before any ticker is seen, so a scan cannot be anchored by what an agent
noticed earlier in the session. Synonyms live inside the concept so that a zero
result means zero across the whole set — not zero for the one word somebody
guessed. `market share` and `wallet share` are separate entries on purpose: a
company may disclose one and not the other.
"""


@dataclass(frozen=True)
class ConceptStat:
    """How often a concept appears across a corpus — in documents, never in hits."""

    concept: str
    df: int
    n_docs: int
    first: str | None
    last: str | None
    seasons: int


def scan_concepts(
    docs: Sequence[tuple[str, str]],
    lexicon: Mapping[str, Sequence[str]] = LEXICON,
) -> list[ConceptStat]:
    """Count, for each concept, how many documents mention it — rarest first.

    ``docs`` is a sequence of ``(event_date, text)``; pass one entry per call, with
    ``text`` being that call's management-side turns only (see ``classify_side``).

    Reports document frequency, not hit counts. Management repeats talking points
    quarterly, so hits are not independent observations: a naive grep of Verizon's
    corpus finds 82 mentions of "market share" where the honest figure is 39 calls
    across 8 years. ``seasons`` counts distinct calendar years, collapsing repeats.

    A concept with ``df == 0`` is still returned. That silence is the finding — but
    read it against ``coverage()``: absent from the corpus is not absent from history.
    """
    stats: list[ConceptStat] = []
    for concept, patterns in lexicon.items():
        matcher = re.compile("|".join(patterns), re.IGNORECASE)
        hit_dates = sorted(event_date for event_date, text in docs if matcher.search(text))
        stats.append(
            ConceptStat(
                concept=concept,
                df=len(hit_dates),
                n_docs=len(docs),
                first=hit_dates[0] if hit_dates else None,
                last=hit_dates[-1] if hit_dates else None,
                seasons=len({event_date[:4] for event_date in hit_dates}),
            )
        )
    return sorted(stats, key=lambda stat: (stat.df, stat.concept))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_transcripts.py -q`
Expected: `38 passed`

- [ ] **Step 5: Run the full gates**

Run: `uv run pytest -q && uv run ruff check && uv run ruff format --check && uv run mypy`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add tools/research/transcripts.py tests/test_transcripts.py
git commit --no-gpg-sign -m "feat(research): scan a curated concept lexicon by document frequency"
```

---

## Task 4: The prose — fetch loop and the rules that keep it honest

**Files:**
- Modify: `.claude/skills/research-ticker/references/disclosure-hunt.md`
- Modify: `.claude/skills/research-ticker/SKILL.md`

**Interfaces:**
- Consumes: `flatten_turn`, `classify_side`, `MANAGEMENT`, `coverage`, `scan_concepts`, `LEXICON`
  from Tasks 1–3, with the exact signatures given there.
- Produces: nothing importable.

**Why prose and not code.** The fetch loop is ~25 lines, has one consumer (an agent following this
skill), touches the network, and is regenerated fresh each session against a live endpoint it
would break loudly against. `tools/` forbids network, and the four-file rule governs screener
packages, so it has no legal home as a module — and it needs none.

- [ ] **Step 1: Append the corpus section to `disclosure-hunt.md`**

Insert this immediately after the "Earnings-call transcripts" bullet in section 1, replacing that
bullet's terse text with a pointer, then add the section below at the end of section 2.

Replace this bullet:

```markdown
- **Earnings-call transcripts.** For a deep look, read many years. The point
  is not the quarter; it is learning what management has and has not ever said.
```

with:

```markdown
- **Earnings-call transcripts.** For a deep look, search many years — do not read
  them; the corpus is ~650k tokens. See *Searching the transcript corpus* below.
  The point is not the quarter. But read the coverage warning there before you
  conclude anything from silence.
```

Then append to the end of the file:

```markdown
## Searching the transcript corpus

`/stocks/{T}/transcripts/` indexes a company's earnings calls and conference
presentations; `/stocks/{T}/transcripts/{detailSlug}/` returns one in full. A big
corpus is ~76 calls, ~2.6M characters, ~650k tokens. **You cannot read it.** Search
it, and read only what matches.

### First, the coverage warning — this is not optional

Transcript depth tracks the data provider's onboarding date, **not the company's
history**, and nothing in the payload says so. There is no `fullCount`, no coverage
marker, and `?page=2` silently returns the `{info}` gate rather than more rows.

| Ticker | Calls | Earliest |
|---|---|---|
| NVDA | 148 | 2010 |
| AAPL | 74 | 2011 |
| VZ | 76 | 2019 |
| IBM | 40 | 2021 |
| T | **12** | **2021** |
| BABA · TSM · SAP · SONY | **0** | no corpus exists |

So:

- **The corpus proves presence.** "Management said X on 2024-10-22" is citable.
- **The corpus never proves absence.** Zero hits means *"not found in the N calls
  covering `first`–`last`, which excludes this company's first M years as a filer."*
  Write that sentence, with the numbers. **Never** write "management has never
  discussed X." That is a confident falsehood wearing the authority of a search.
- **Rarity only means something when coverage ≈ company history.** Copart naming its
  market share twice in twenty years is a finding. The same silence across AT&T's
  twelve calls since 2021 is nothing at all.

Call `coverage(index, ipo_date)` and print it *before* any hit list. Read `ipo_date`
with a plain, read-only query — the skill never writes to `data/*.db`:

```
sqlite3 data/stocks.db "SELECT ipoDate FROM v_latest WHERE symbol='VZ';"
-- 2000-07-03
```

`ipoDate` is NULL for roughly 45% of the 5,601-row universe — **including AT&T, this
section's own headline example** — because stockanalysis itself returns `ipoDate: None`
for those tickers. It is not a gap in this repo's screener:

```
sqlite3 data/stocks.db "SELECT ipoDate FROM v_latest WHERE symbol='T';"
-- (empty)
```

Treat a ticker missing from `v_latest` entirely the same way. Either case, pass
`ipo_date=None`; `coverage()` then returns `uncovered_years=None` instead of a number.
When that happens, report the corpus span (`n_calls`, `first`, `last`) and say plainly
that the pre-corpus history is unquantified. Never imply the corpus is complete, and
never write "management never said X" — that is the binding rule above, applied to the
missing-`ipoDate` case.

### The loop

```python
import time
from collections import Counter
from sources.screeners.stock_analysis_screener.probe import page_data
from tools.research.transcripts import (
    LEXICON, MANAGEMENT, OUTSIDE, classify_side, coverage, flatten_turn,
    issuer_from_turns, scan_concepts,
)

TICKER = "VZ"
ISSUER_NAME = None   # set this yourself only if you already know the legal name —
                      # data/stocks.db has no company-name column, so there is no
                      # local source of truth to read it from

index = page_data(f"/stocks/{TICKER}/transcripts/")
if not isinstance(index, dict) or "transcripts" not in index:
    raise SystemExit(f"{TICKER}: no transcript corpus exists")   # BABA, TSM, SAP, SONY, pre-IPO SPACs
rows = index["transcripts"]

print(coverage(rows, ipo_date="2000-07-03"))   # PRINT THIS FIRST. From a read-only
                                                # sqlite3 SELECT against data/stocks.db;
                                                # pass None if the row is NULL or absent

calls = []
for row in rows:
    try:
        body = page_data(f"/stocks/{TICKER}/transcripts/{row['detailSlug']}/")
        turns = body["transcriptQuarter"]["transcriptTurns"]   # KeyError on {info} — intended
    except Exception as exc:                         # noqa: BLE001
        print(f"skip {row['eventDate']}: {type(exc).__name__}")   # never str(exc) — it carries the URL
        continue
    calls.append((row["eventDate"], turns))
    time.sleep(0.7)                                  # unofficial endpoint; be a polite client

# Elect the issuer ONCE, after every call is fetched, from turns POOLED across all of
# them — never inside the loop above, and never from a single call.
# issuer_from_turns is the PRIMARY source: pooled across every fetched call it is
# live-verified correct, and the print below lets you eyeball it. Set ISSUER_NAME
# above only when you already know the legal name; never derive it from
# transcriptMeta.title — XOM's reads "ExxonMobil Holdings Corporation", and the
# company has no "Holdings", so matching on it would silently exclude its own turns.
pooled_turns = [t for _, turns in calls for t in turns]
issuer = ISSUER_NAME or issuer_from_turns(pooled_turns)

print("issuer:", issuer, "| pooled mode:", issuer_from_turns(pooled_turns))
sides = Counter(classify_side(t, issuer) for _, turns in calls for t in turns)
print(sides)
print("outside firms:", sorted({t["company"] for _, ts in calls for t in ts
                                if classify_side(t, issuer) == OUTSIDE}))

docs = [
    (date, " ".join(flatten_turn(t) for t in turns
                    if classify_side(t, issuer) == MANAGEMENT))   # analysts ask; management discloses
    for date, turns in calls
]
for stat in scan_concepts(docs, LEXICON):
    print(stat)
```

~78 seconds for a 76-call corpus. Write the JSONL to your scratchpad if you want to
re-search without re-fetching; never to `data/` and never to `research/`.

**Check the `issuer` and the `outside firms` list before you trust any count.** If a
division of the company ("Verizon Consumer Group") shows up under *outside firms*, the
issuer string is wrong and every `df` below it is understated.

### Reading the result

- **`classify_side` is the correctness property.** A hit for "market share" is a
  *disclosure* if the CFO said it and a *question* if Goldman asked it. Filter to
  `MANAGEMENT` before you count anything, or you will cite an analyst's premise as
  the company's own claim.
- **Report `df` and seasons, never hit counts.** Management reads the same script
  every quarter. Verizon's corpus has 82 raw mentions of "market share" and 39
  documents across 8 years; the first number is not evidence of anything.
- **`LEXICON` is fixed before you see the ticker.** That is deliberate — it cannot be
  anchored by what you already noticed. Add ticker-specific probes *after* running
  it, as a supplement, never as a replacement. You cannot generate the question you
  do not know to ask; the fixed list is what covers for that, imperfectly.

### Quartr, not EDGAR

These are *transcriptions*, produced by a third party. The words are management's;
the text is not.

- Qualitative framing, tone, and emphasis are usable, cited as **primary, transcribed**.
- **Any number** that is load-bearing for the thesis must be corroborated against the
  printed filing — the earnings release, the slides, the 10-Q — before it counts as a
  fact. A misheard "15%" for "50%" is silent, and it does not look like colour. It
  looks like a quote.
- `summaryShort` and `summaryLongHtml` are AI-generated. Low-confidence, always.
```

- [ ] **Step 2: Add the Phase 2 pointer in `SKILL.md`**

In `SKILL.md`, replace:

```markdown
Use `references/disclosure-hunt.md` for *where to look*. Its three questions,
in order: does the information exist; can it be triangulated or found
elsewhere; and if not, does its absence kill the thesis?
```

with:

```markdown
Use `references/disclosure-hunt.md` for *where to look*. Its three questions,
in order: does the information exist; can it be triangulated or found
elsewhere; and if not, does its absence kill the thesis?

When a thread turns on what management has said over the years, search the
transcript corpus rather than reading it — see *Searching the transcript corpus*
there. Print its coverage before you print a hit, and remember the corpus can
show you that something **was** said, never that it never was.
```

- [ ] **Step 3: Verify the loop in the prose actually runs**

This is documentation, so the gates will not catch a typo in it. Run the code block
end-to-end against a small corpus and confirm it prints coverage then concept stats:

Run:
```bash
uv run python -c "
from sources.screeners.stock_analysis_screener.probe import page_data
from tools.research.transcripts import LEXICON, MANAGEMENT, classify_side, coverage, flatten_turn, scan_concepts
idx = page_data('/stocks/CROX/transcripts/')['transcripts'][:3]
print(coverage(idx, ipo_date='2006-02-08'))
docs=[]
for row in idx:
    q = page_data(f\"/stocks/CROX/transcripts/{row['detailSlug']}/\")['transcriptQuarter']
    docs.append((row['eventDate'], ' '.join(flatten_turn(t) for t in q['transcriptTurns'] if classify_side(t,'Crocs, Inc.')==MANAGEMENT)))
for s in scan_concepts(docs, LEXICON)[:4]: print(s)
"
```
Expected: a `Coverage(n_calls=3, ...)` line, then four `ConceptStat(...)` lines with
`df <= 3`. If every `df` is 0, `classify_side` is rejecting management turns — check
the issuer string against the corpus's actual `company` values.

- [ ] **Step 4: Run the full gates**

Run: `uv run pytest -q && uv run ruff check && uv run ruff format --check && uv run mypy`
Expected: all pass (docs-only change; this confirms no regression).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/research-ticker/references/disclosure-hunt.md .claude/skills/research-ticker/SKILL.md
git commit --no-gpg-sign -m "docs(skills): search the transcript corpus, and never infer absence from it"
```

---

## Task 5: Stop the fetch loop spoofing a browser

**Files:**
- Modify: `sources/screeners/stock_analysis_screener/probe.py:19`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing importable. `probe._UA` changes value; its type and every call site are
  unchanged.

**Why.** Task 4's loop issues 77 requests through `probe.page_data`, which sends
`{"User-Agent": "Mozilla/5.0"}` — a spoof that identifies nobody. The catalog's own access note
says *"Be a polite client (sane rate, real User-Agent)"*, and this repo's one real example is
`sources/screeners/edgar_screener/fetch.py:84`:
`{"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}`. Pacing without identification is
half of politeness. Do this before shipping a loop that multiplies the requests by 77.

`probe._UA` is read by `fetch_data_json`, which backs both `page_data` and
`catalog.fetch_catalog` (the shipped `stocks` screener). Changing the header changes no types and
no call sites; stockanalysis.com enforces no UA policy, so the shipped screener is unaffected.

- [ ] **Step 1: Change the header**

In `sources/screeners/stock_analysis_screener/probe.py`, replace:

```python
_UA = {"User-Agent": "Mozilla/5.0"}
```

with:

```python
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
"""Descriptive, per the catalog's "real User-Agent" note and edgar_screener's precedent.

Not a browser spoof: the research corpus loop issues ~77 requests per session, and a
polite client says who it is. stockanalysis.com enforces no UA policy either way.
"""
```

- [ ] **Step 2: Verify the endpoint still answers under the new identity**

The suite is offline and cannot catch a rejected header. Check live:

Run:
```bash
uv run python -c "
from sources.screeners.stock_analysis_screener.probe import page_data
d = page_data('/stocks/AAPL/statistics/')
print('ok, blocks:', len(d))
"
```
Expected: `ok, blocks: 20`. A `403` or `HTTPError` means the site does enforce a UA policy —
revert to `Mozilla/5.0`, and record the finding in `docs/stockanalysis_data_json_catalog.md`.

- [ ] **Step 3: Run the full gates**

Run: `uv run pytest -q && uv run ruff check && uv run ruff format --check && uv run mypy`
Expected: all pass. The 1174 existing tests do not touch `_UA` (the network wrapper is untested by
design), so a failure here means something unrelated broke.

- [ ] **Step 4: Commit**

```bash
git add sources/screeners/stock_analysis_screener/probe.py
git commit --no-gpg-sign -m "fix(probe): say who we are instead of spoofing a browser"
```

---

## Task 6: Index the plan

**Files:**
- Modify: `plans/README.md`

- [ ] **Step 1: Add the status row**

Append to the status table in `plans/README.md`, after plan 006's row:

```markdown
| 007 | [Research corpus (Unit 3)](007-research-corpus.md) | P2 | S–M | 006 | **TODO** |
```

- [ ] **Step 2: Flip to DONE and record what review broke**

After Tasks 1–5 are merged, change `**TODO**` to `**DONE**` and add one line to the
"What happened" narrative noting that four adversarial reviewers refuted the unit's premise
before implementation: transcript depth is the provider's onboarding date, not company history,
so the corpus proves presence and never absence.

- [ ] **Step 3: Commit**

```bash
git add plans/README.md
git commit --no-gpg-sign -m "docs(plans): index 007, the research corpus"
```

---

## What adversarial review broke

- **Task 4 shipped a CRITICAL defect, and the implementer talked itself out of it.** The documented fetch
  loop elected the issuer inside the per-call loop (`issuer = issuer or issuer_from_turns(turns)`), i.e.
  from `rows[0]`, the most recent event. The transcripts index interleaves earnings calls with **conference
  presentations**, and a conference is a 1:1 dialogue in which the host bank ties or beats management on
  turn count. Measured on VZ, newest-first: `JPMorgan` (19 v 19 — a tie broken by dict insertion order),
  `MoffettNathanson` (46 v 46), `Deutsche Bank` (39 v 38), `Morgan Stanley` (38 v 37). Five of six recent
  calls elected a bank; only the one real earnings call elected `Verizon`. With a bank as issuer,
  `classify_side` inverts every turn, every `df` collapses, and the session concludes "management never
  said X" — the precise falsehood this unit exists to prevent. Fixed in `c1b1d45`: elect once, from turns
  pooled across all calls, preferring an explicit caller-supplied issuer name when one is given; three
  tests pin the hazard. (That fix's own comment claimed the explicit name would come from `data/stocks.db`'s
  `n` column — see the final-review entry below: no such column exists.)
  Root cause was the plan's own `issuer_from_turns` docstring, which asserted management out-speaks any
  bank "on its own call". False for conference presentations. This also promoted Task 1's tie-break Minor:
  ties are not theoretical, they occur on the newest call.

- **Task 2, as first written, was wrong.** `coverage()` sorted `eventDate` as raw strings and never
  validated them. A malformed date (`"Jul 10, 2026"`) was silently accepted into `first`/`last` when
  `ipo_date` was absent, and raised only when it was present — an inconsistent failure mode in the one
  function whose entire job is to stop silent degradation. Lexicographic sort also reported
  `last == "2024-1-5"` over `"2024-01-10"`. Fixed in `5808de9`: parse every date before sorting, raise
  on anything non-ISO, and say so in the docstring. Four regression tests added.
  (Same hazard class CLAUDE.md already documents for `prune`: string comparison of timestamps is only
  correct because every writer stores a fixed-width `isoformat()`.)
- The fix brief asserted `date.fromisoformat("2024-1-5")` succeeds on Python 3.11+. It does not — 3.11
  relaxed ISO-8601 parsing but never allowed unpadded components. The fix subagent caught this and
  asserted the observed `ValueError` instead of the assumed success. Verify interpreter behavior; do not
  reason about it from release notes.

- **Final whole-branch review: `data/stocks.db`'s `n` column was fabricated, and it survived four task
  reviews.** Every draft of this plan and of `disclosure-hunt.md` asserted `ISSUER_NAME = "..."` came from
  `data/stocks.db` `n` — "authoritative" — and told the agent to "take `ipo_date`" from the same source.
  Verified live: `metrics`/`v_latest` has no `n` column and no company-name column at all (columns are
  `snapshot_id, symbol, marketCap, ..., ipoDate, ...`). `n` is a stockanalysis payload field that this repo
  never persists. An agent following the doc as written runs `SELECT n ...` and gets `no such column: n`.
  There is no reliable local company-name source; `sec_fundamentals.db`'s `companies` table exists but
  holds only 52 rows and does not include VZ, T, CROX, or XOM. Fixed by making `issuer_from_turns` the
  stated primary source in the prose (it already was, functionally — the docstring says so — but the
  worked example told the reader to override it with a column that isn't there), with `ISSUER_NAME = None`
  the default. Also found in the same pass: `ipoDate` **is** a real column, but it is NULL for 2,519 of
  5,601 rows (~45%) — including AT&T, the coverage table's own headline example of a thin corpus. That is
  upstream (stockanalysis returns `ipoDate: None` for those tickers), not a bug in this repo's screener.
  `disclosure-hunt.md` now shows the real read-only query, states the ~45% NULL rate plainly, and says what
  to write when `uncovered_years` comes back `None`: report the corpus span and call the pre-corpus history
  unquantified — never "management never said X." Lesson: a claim about a schema needs to be checked against
  the schema, not carried forward by four separate reviewers who each trusted the previous draft.

## Out of scope (do not build)

- **Storing the corpus.** No cross-name or cross-time comparison exists to make. Scratchpad only.
- **A `sources/` package, a `registry.py` entry, a launchd slot, or any schema.** This is
  read-time only.
- **A `get=`/`opener=` seam on `probe.py`.** It needs none: the repo's pattern is to test pure
  parsers (`parse_catalog`) and inject network wrappers at the caller
  (`fetch_catalog=fake_catalog`), never to test the wrapper. Everything in
  `tools/research/transcripts.py` is pure, so it needs no seam either. Task 5's one-line
  User-Agent change is the *only* sanctioned edit to `probe.py` in this plan.
- **Phase 0's leverage gate.** `"heavy leverage relative to its cash generation"` has no
  threshold, though `debtFcf`, `netDebtEbitda` and `interestCoverage` sit in the payload Phase 0
  already fetches. Quantifying it decides which companies ever get researched, and the repo's
  `composite-calibration-lesson` warns against thresholds set before real data exists. Separate
  decision, separate plan.
- **`/filings/` PDFs and `/metrics/{metric}` segment splits.** Reachable today via
  `probe.page_data`; they want prose, not code, and not in this plan.

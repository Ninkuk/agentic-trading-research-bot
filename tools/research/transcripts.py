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
from dataclasses import dataclass
from datetime import date

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
    """
    dates = sorted(row["eventDate"] for row in index if row.get("eventDate"))
    first = dates[0] if dates else None
    last = dates[-1] if dates else None

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

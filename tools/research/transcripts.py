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
from collections.abc import Mapping, Sequence
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

    Pooled across many calls, management dominates the turn count (Verizon: 3,234
    management turns against Morgan Stanley's 383), so the mode is the issuer. Pass
    turns pooled from many calls, never a single call's turns.

    ``/stocks/{T}/transcripts/`` interleaves earnings calls (many-to-one: many
    analysts, one management team — management wins the count) with conference
    presentations (one-to-one: a host bank's moderator and one executive — the bank
    ties or beats management on turn count). Electing an issuer from one conference
    call is unsafe: on Verizon's 2026-05-18 JPMorgan conference this returns
    "JPMorgan" (19 turns each, a tie), not "Verizon". Ties resolve by
    ``Counter.most_common``'s first-seen insertion order — deterministic, but
    arbitrary, and not a signal that the tied name is correct.

    Use this rather than guessing a spelling, and rather than ``transcriptMeta.title``,
    which is wrong for XOM. Prefer an explicit issuer name from the caller (e.g.
    ``data/stocks.db``'s ``n`` column) when one is available; treat this function as
    the fallback / cross-check, not the primary source.
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

    Every truthy ``eventDate`` must be zero-padded ISO-8601 (``YYYY-MM-DD``); a falsy
    one ("", None, or a missing key) is skipped when computing the span but still
    counted in ``n_calls``. A present-but-malformed ``eventDate`` — including a
    non-zero-padded one like ``"2024-1-5"`` — raises ``ValueError`` (via
    ``date.fromisoformat``) naming the offending value. It is never silently skipped,
    and dates are never ordered as raw strings: lexicographic sort gets non-zero-padded
    or otherwise irregular dates chronologically wrong.
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

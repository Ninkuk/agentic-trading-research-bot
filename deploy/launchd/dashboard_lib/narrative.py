"""Plain-English bands, verdict chips, caveat lines, and hero bullets.

PURE module: every function is (values in) -> (dicts/strings out). No
sqlite, no clock, no file I/O, no imports beyond stdlib typing — `data.py`
does the fetching and hands this module plain values/dicts.

`hero_bullets` inputs are plain dicts assembled by `data.py`:
- `regime`: `{"regime": str | None, "streak_nights": int, "vix": float | None}`
- `book`: `{"heat_pct": float | None, "positions": int}` — `heat_pct` here is
  PERCENT-scale (already multiplied by 100 by the caller), matching
  `book_verdict`'s contract.
- `disagreements`: list of holding symbols whose signal has turned against
  them (already computed by `data.py`).
- `flagged`: list of tonight's flagged tickers, strongest-agreement first.

Sentence logic and thresholds are ported from the `_hero_*_clause` functions
in `sections.py` (the legacy server-rendered HTML page); all HTML markup is
dropped here — callers render tone into chip styling themselves.
"""

from typing import Literal

Tone = Literal["on", "off", "mid"]
Bullet = dict[str, str]


# --- Band thresholds -------------------------------------------------------
# Each is a deliberate cutoff carried over from the legacy hero clauses /
# advisor-book conventions, not a vibe. Ranges are inclusive on the lower
# bound, i.e. `lo <= value < hi`.

_VIX_BANDS: tuple[tuple[float, str], ...] = (
    (15.0, "calm"),  # below the VIX's long-run median-ish floor
    (20.0, "normal"),  # legacy hero clause's "calm" cutoff (elevated >= 20)
    (30.0, "nervous"),  # >=30 is the classic "stressed markets" VIX level
)
_VIX_STRESSED = "stressed"

# book_heat_pct: PERCENT-scale (see book_verdict docstring for the unit trap).
_BOOK_HEAT_BANDS: tuple[tuple[float, str], ...] = (
    (1.5, "comfortable"),  # single-digit-of-equity heat reads as low risk
    (3.0, "moderate"),  # advisor's own default heat ceiling is ~3%
)
_BOOK_HEAT_ELEVATED = "elevated"

# t10y2y: the classic recession-signal sign flip; no gray zone.
_T10Y2Y_INVERTED_BELOW = 0.0

_HY_SPREAD_BANDS: tuple[tuple[float, str], ...] = (
    (4.0, "calm"),  # tight high-yield spreads
    (6.0, "wide"),  # spread widening that credit desks start flagging
)
_HY_SPREAD_STRESSED = "stressed"


def qualitative_band(metric: str, value: float) -> str | None:
    """Map a raw metric value to its plain-English band. Unknown metric ->
    None (never raises, never guesses a band for a metric we don't know)."""
    if metric == "vix":
        for hi, label in _VIX_BANDS:
            if value < hi:
                return label
        return _VIX_STRESSED
    if metric == "book_heat_pct":
        for hi, label in _BOOK_HEAT_BANDS:
            if value < hi:
                return label
        return _BOOK_HEAT_ELEVATED
    if metric == "t10y2y":
        return "inverted" if value < _T10Y2Y_INVERTED_BELOW else "normal"
    if metric == "hy_spread":
        for hi, label in _HY_SPREAD_BANDS:
            if value < hi:
                return label
        return _HY_SPREAD_STRESSED
    return None


def verdict(text: str, tone: Tone) -> dict:
    """The chip shape every verdict/bullet function below returns."""
    return {"text": text, "tone": tone}


def _ordinal(n: int) -> str:
    """1st/2nd/3rd/4th.../11th/12th/13th/21st..."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


_REGIME_LABEL = {"risk_on": "Risk-on", "risk_off": "Risk-off"}
_REGIME_TONE: dict[str, Tone] = {"risk_on": "on", "risk_off": "off"}


def regime_verdict(regime: str | None, streak_nights: int) -> dict | None:
    """Regime chip: "Risk-on, 4th night". Unknown/missing regime label falls
    back to "Mixed" with a mid tone (mirrors the legacy hero clause's mixed
    wording); `regime is None` opts out entirely (nothing computed yet)."""
    if regime is None:
        return None
    label = _REGIME_LABEL.get(regime, "Mixed")
    tone: Tone = _REGIME_TONE.get(regime, "mid")
    return verdict(f"{label}, {_ordinal(streak_nights)} night", tone)


def book_verdict(heat_pct: float | None) -> dict | None:
    """Book-heat chip from the qualitative band. Takes PERCENT, not the
    view's fraction: `v_book_heat.heat_pct` in advisor.db is a FRACTION
    (heat_dollars / equity, live value ~0.0196 = 1.96%), but the band
    thresholds above are percent-scale. Callers must multiply the view's
    value by 100 before calling this. `heat_pct is None` (no book captured
    yet) opts out."""
    if heat_pct is None:
        return None
    band = qualitative_band("book_heat_pct", heat_pct)
    tone: Tone = "off" if band == _BOOK_HEAT_ELEVATED else "on"
    return verdict(f"Book heat {band}", tone)


def efficacy_verdict(keep: int, watch: int, anti: int) -> dict | None:
    """Signal-efficacy summary chip: how many flags are KEEP/WATCH/ANTI
    tonight. All-zero (nothing graded yet) opts out."""
    if keep == 0 and watch == 0 and anti == 0:
        return None
    tone: Tone = "on" if keep >= anti else ("off" if anti > keep else "mid")
    return verdict(f"{keep} keep / {watch} watch / {anti} anti-signal", tone)


def hero_bullets(
    regime: dict | None = None,
    book: dict | None = None,
    disagreements: list[str] | None = None,
    flagged: list[str] | None = None,
) -> list[Bullet]:
    """At most three bullets for tonight's read: market mood, your book,
    attention (disagreements first, else flagged tickers). Every argument is
    optional; a missing input just skips that bullet — this never raises."""
    bullets: list[Bullet] = []

    if regime is not None:
        r = regime.get("regime")
        streak = regime.get("streak_nights", 0)
        mood = {
            "risk_on": "leaning into risky assets",
            "risk_off": "pulling back from risk",
        }.get(r or "", "sending mixed signals")
        tone: Tone = _REGIME_TONE.get(r or "", "mid")
        label = _REGIME_LABEL.get(r or "", "Mixed")
        vix = regime.get("vix")
        vix_txt = "" if vix is None else f", VIX {qualitative_band('vix', vix)} at {vix:.1f}"
        bullets.append(
            {
                "text": f"{label}: {mood}, {_ordinal(streak)} night in a row{vix_txt}.",
                "tone": tone,
            }
        )

    if book is not None:
        heat_pct = book.get("heat_pct")
        positions = book.get("positions", 0)
        pos_word = "position" if positions == 1 else "positions"
        if heat_pct is None:
            bullets.append(
                {
                    "text": f"Your book holds {positions} {pos_word}; heat not available.",
                    "tone": "mid",
                }
            )
        else:
            band = qualitative_band("book_heat_pct", heat_pct)
            book_tone: Tone = "off" if band == _BOOK_HEAT_ELEVATED else "on"
            bullets.append(
                {
                    "text": (
                        f"Your book holds {positions} {pos_word}, heat {band} at {heat_pct:.1f}%."
                    ),
                    "tone": book_tone,
                }
            )

    if disagreements:
        if len(disagreements) == 1:
            text = f"{disagreements[0]} is worth a look; its signal has turned against it."
        else:
            text = f"{len(disagreements)} holdings are worth a look; see Disagreements below."
        bullets.append({"text": text, "tone": "mid"})
    elif flagged:
        if len(flagged) == 1:
            text = f"{flagged[0]} is flagged tonight and worth a look."
        else:
            text = f"{', '.join(flagged[:3])} are flagged tonight and worth a look."
        bullets.append({"text": text, "tone": "mid"})

    return bullets[:3]


CAVEATS: dict[str, str] = {
    "signal-efficacy": (
        "Small sample; windows overlap, so one hot week can flatter several "
        "signals at once. Grades firm up as distinct composite dates accumulate."
    ),
    "bucket-performance": (
        "Buckets group flags by strength, not by independence; the same "
        "overlapping-episode caveat applies within each bucket. Read the count "
        "before trusting a bucket's average."
    ),
    "human-filter": (
        "Compares acted-on vs. passed-on flags from a still-small decision "
        "journal. A handful of trades can swing the comparison either way."
    ),
    "regime-performance": (
        "Regime windows are contiguous stretches rather than independent draws; "
        "a single risk-on run dominates the sample until more regimes accumulate."
    ),
    "pending": (
        "These flags haven't reached their grading horizon yet, so nothing "
        "here is a result; it's a worklist."
    ),
    "cot-tails": (
        "A tail marks a market to watch, not a trade: identical washouts "
        "have resolved violently or sat unchanged for months. No measured "
        "forward-return evidence yet."
    ),
    "plan-001-report": (
        "A backtest replay against ALFRED vintages, not live trading. Read "
        "excess and beats-baseline rather than hit-rate alone, and remember "
        "this is one history, not a distribution."
    ),
    "plan-004-scorecard": (
        "Grades the human's own decisions from the journal. Coverage is "
        "whatever got journaled, not a random sample of every flag shown."
    ),
    "candidate-efficacy": (
        "Episodes are few and overlap early. The view carries plain averages "
        "with no confidence interval, so read n before believing any row."
    ),
}

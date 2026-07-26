"""The candidates reporter is a SELECT-only quality-first screen over
stocks.db. Every exclusion below exists because an adversarial review found
the corresponding defect in the raw data (2026-07-26) — see the module
docstring in sources/combiners/composite/candidates.py."""

import sqlite3

import pytest

from sources.combiners.composite import candidates

NOW = "2026-07-26T04:05:00+00:00"

# Column subset the screen reads; the real v_latest has ~280.
_COLS = (
    "symbol TEXT, marketCap REAL, dollarVolume REAL, isPrimaryListing TEXT,"
    " isin TEXT, sector TEXT, roic REAL, roic5y REAL, fcfYield REAL,"
    " revenueGrowth3Y REAL, netDebtEbitda REAL, sharesYoY REAL, fScore REAL,"
    " rsi REAL, ch6m REAL, priceDate TEXT"
)

# A name that passes every gate. Tests mutate one field at a time off this.
_CLEAN = dict(
    symbol="GOOD",
    marketCap=20e9,
    dollarVolume=50e6,
    isPrimaryListing="1",
    isin="US1111111111",
    sector="Technology",
    roic=25.0,
    roic5y=20.0,
    fcfYield=6.0,
    revenueGrowth3Y=9.0,
    netDebtEbitda=0.5,
    sharesYoY=-1.0,
    fScore=7.0,
    rsi=38.0,
    ch6m=-20.0,
    priceDate="2026-07-24",
)


def _stocks_db(tmp_path, *rows, name="stocks.db"):
    path = str(tmp_path / name)
    conn = sqlite3.connect(path)
    conn.execute(f"CREATE TABLE v_latest ({_COLS})")
    for r in rows:
        merged = {**_CLEAN, **r}
        cols = ", ".join(merged)
        marks = ", ".join("?" * len(merged))
        conn.execute(f"INSERT INTO v_latest ({cols}) VALUES ({marks})", tuple(merged.values()))
    conn.commit()
    return conn


def _symbols(conn):
    return [r["symbol"] for r in candidates.screen(conn)]


def test_clean_quality_name_passes(tmp_path):
    conn = _stocks_db(tmp_path, {})
    assert _symbols(conn) == ["GOOD"]


# ----------------------------------------------------- quality gates ----
# One test per gate. Each names the single field that disqualifies the row,
# so a dropped or sign-flipped clause fails exactly one test.


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("marketCap", 5e8),  # sub-$2B
        ("dollarVolume", 20_000.0),  # TAP.A: $7.5B "cap", $14k traded
        ("roic", 4.0),  # not a quality business
        ("roic5y", 2.0),  # quality is not durable
        ("fcfYield", 1.0),  # not cheap on cash
        ("revenueGrowth3Y", 0.5),  # not growing
        ("netDebtEbitda", 6.0),  # levered
        ("sharesYoY", 8.0),  # diluting
        ("fScore", 3.0),  # falling knife, not oversold quality
        ("rsi", 72.0),  # no dislocation to enter on
    ],
)
def test_gate_excludes(tmp_path, field, bad_value):
    conn = _stocks_db(tmp_path, {"symbol": "BAD", field: bad_value})
    assert _symbols(conn) == []


def test_excludes_roic_denominator_blowup(tmp_path):
    """NTES reads roic=376% because net cash nearly equals equity, collapsing
    invested capital. A bare `roic > 12` admits the artifact, not the quality."""
    conn = _stocks_db(tmp_path, {"symbol": "BLOWUP", "roic": 376.5})
    assert _symbols(conn) == []


def test_excludes_nonpositive_rsi(tmp_path):
    """26 rows carry rsi <= 0 — out of domain for a 0-100 oscillator. The
    composite catalog already guards `rsi > 0` on this same column."""
    conn = _stocks_db(tmp_path, {"symbol": "ZERO", "rsi": 0.0})
    assert _symbols(conn) == []


@pytest.mark.parametrize(
    "field,edge,passes",
    [
        ("roic", candidates.ROIC_MAX, True),  # BETWEEN is inclusive
        ("roic", candidates.ROIC_MIN, True),
        ("rsi", candidates.RSI_MAX, False),  # `<` is exclusive
        ("sharesYoY", candidates.SHARES_YOY_MAX, False),
        ("netDebtEbitda", candidates.NET_DEBT_EBITDA_MAX, False),
        ("fScore", candidates.FSCORE_MIN, True),  # `>=` is inclusive
        ("fcfYield", candidates.FCF_YIELD_MIN, True),
    ],
)
def test_threshold_boundaries_are_pinned(tmp_path, field, edge, passes):
    """Pins inclusive-vs-exclusive on every gate; an operator swap fails here."""
    conn = _stocks_db(tmp_path, {"symbol": "EDGE", field: edge})
    assert (_symbols(conn) == ["EDGE"]) is passes


def test_thresholds_are_on_the_percent_scale(tmp_path):
    """stockanalysis.com stores roic=27.09 to mean 27.09%. If the gates were
    ever read as fractions, a genuinely excellent business reads as a failure."""
    conn = _stocks_db(tmp_path, {"symbol": "FRAC", "roic": 0.25, "fcfYield": 0.06})
    assert _symbols(conn) == []


def test_null_leverage_is_admitted_not_dropped(tmp_path):
    """netDebtEbitda is the sparsest field read here (2860/5597). Dropping
    NULLs would silently halve the universe, so absent leverage is not
    disqualifying; present-and-bad is."""
    conn = _stocks_db(tmp_path, {"symbol": "NOLEV", "netDebtEbitda": None})
    assert _symbols(conn) == ["NOLEV"]


@pytest.mark.parametrize(
    "field", ["marketCap", "dollarVolume", "roic", "roic5y", "fcfYield", "fScore", "rsi"]
)
def test_null_on_a_required_gate_drops_the_row(tmp_path, field):
    """Documents the deliberate asymmetry with netDebtEbitda above: these
    fields are densely populated, so a NULL is missing evidence, not a
    sparse-by-nature field, and the screen declines to guess."""
    conn = _stocks_db(tmp_path, {"symbol": "NULLED", field: None})
    assert _symbols(conn) == []


# ------------------------------------------------ one row per company ----


def test_share_classes_collapse_to_one_row(tmp_path):
    """BRK.A/BRK.B inherit a near-identical whole-company marketCap and share
    CUSIP issuer 084670, so a cap screen would otherwise count one company
    twice. The more liquid line wins."""
    conn = _stocks_db(
        tmp_path,
        {"symbol": "BRK.A", "isin": "US0846701086", "isPrimaryListing": "0", "dollarVolume": 93e6},
        {"symbol": "BRK.B", "isin": "US0846707026", "isPrimaryListing": "0", "dollarVolume": 1.4e9},
    )
    assert _symbols(conn) == ["BRK.B"]


def test_flagged_primary_listing_wins_over_raw_volume(tmp_path):
    conn = _stocks_db(
        tmp_path,
        {"symbol": "AAA", "isin": "US0846701086", "isPrimaryListing": "1", "dollarVolume": 20e6},
        {"symbol": "AAB", "isin": "US0846707026", "isPrimaryListing": "0", "dollarVolume": 90e6},
    )
    assert _symbols(conn) == ["AAA"]


def test_liquid_foreign_adr_with_us_isin_is_kept(tmp_path):
    """SAP/GFI/NICE are isPrimaryListing='0' but carry US ADR ISINs and trade
    hundreds of millions a day. A bare isPrimaryListing filter drops ~418
    legitimate names; this one must survive."""
    conn = _stocks_db(
        tmp_path,
        {"symbol": "SAP", "isin": "US8030542042", "isPrimaryListing": "0", "dollarVolume": 645e6},
    )
    assert _symbols(conn) == ["SAP"]


def test_distinct_foreign_companies_sharing_an_isin_prefix_are_not_merged(tmp_path):
    """THE trap. Non-US numbering agencies assign ISIN blocks sequentially
    across issuers, not per company: IL|001082 covers 11 unrelated Israeli
    firms INCLUDING CHKP, and NL|001500 covers 14 including Ferrari, Stellantis
    and QIAGEN. Keying on a foreign ISIN prefix would delete real candidates."""
    conn = _stocks_db(
        tmp_path,
        {"symbol": "CHKP", "isin": "IL0010824113", "isPrimaryListing": "0"},
        {"symbol": "QGEN", "isin": "NL0015001WM6", "isPrimaryListing": "0"},
        {"symbol": "STLA", "isin": "NL00150001Q9", "isPrimaryListing": "0"},
    )
    assert sorted(_symbols(conn)) == ["CHKP", "QGEN", "STLA"]


def test_tracking_stock_families_sharing_a_cik_stay_separate(tmp_path):
    """Liberty Media's Braves / Formula One / Live families share ONE cik
    (0001560385) but are three businesses. CIK identifies the registrant, not
    the security family — so the key is the CUSIP issuer number, not the cik."""
    conn = _stocks_db(
        tmp_path,
        {"symbol": "BATRK", "isin": "US0477261046", "isPrimaryListing": "0"},
        {"symbol": "FWONK", "isin": "US5312291005", "isPrimaryListing": "0"},
        {"symbol": "LLYVK", "isin": "US5309091005", "isPrimaryListing": "0"},
    )
    assert sorted(_symbols(conn)) == ["BATRK", "FWONK", "LLYVK"]


def test_preferred_shares_are_excluded(tmp_path):
    """Preferreds are not common equity and carry no cik/isin here."""
    conn = _stocks_db(tmp_path, {"symbol": "PSA.PRT", "isin": None})
    assert _symbols(conn) == []


def test_missing_isin_still_screens_on_its_own_symbol(tmp_path):
    """A name with no isin must not collapse into some other name's group."""
    conn = _stocks_db(tmp_path, {"symbol": "AAA", "isin": None}, {"symbol": "BBB", "isin": None})
    assert sorted(_symbols(conn)) == ["AAA", "BBB"]


# ------------------------------------------------------- report shape ----


def test_rows_are_ordered_by_fcf_yield_then_roic(tmp_path):
    conn = _stocks_db(
        tmp_path,
        {"symbol": "LOW", "isin": "US1000000001", "fcfYield": 4.5},
        {"symbol": "HIGH", "isin": "US2000000002", "fcfYield": 11.0},
        {"symbol": "MID", "isin": "US3000000003", "fcfYield": 7.0},
    )
    assert _symbols(conn) == ["HIGH", "MID", "LOW"]


def test_field_names_map_to_the_right_values(tmp_path):
    """_FIELDS is zipped positionally onto the SELECT list; a reorder of either
    would silently print roic5y's value under the roic header."""
    conn = _stocks_db(tmp_path, {"symbol": "MAP", "roic": 33.0, "roic5y": 22.0, "rsi": 41.0})
    row = candidates.screen(conn)[0]
    assert row["symbol"] == "MAP"
    assert row["roic"] == 33.0
    assert row["roic5y"] == 22.0
    assert row["rsi"] == 41.0


def test_report_renders_empty_without_crash(tmp_path):
    conn = _stocks_db(tmp_path, {"symbol": "TRAP", "fScore": 1.0})
    report = candidates.build_report(conn, NOW)
    assert "no candidates" in report.lower()


def test_report_disclaims_recommendation(tmp_path):
    """This is a screen feeding research-ticker, not a buy list. The report must
    say so on its face — nothing downstream grades it and nobody should trade it."""
    conn = _stocks_db(tmp_path, {})
    report = candidates.build_report(conn, NOW)
    assert "not a recommendation" in report.lower()
    assert "GOOD" in report


def test_report_states_the_screen_is_ungraded(tmp_path):
    """No forward-return evidence exists for this screen. Saying so is the
    difference between a candidate list and an invented edge."""
    assert "ungraded" in candidates.build_report(_stocks_db(tmp_path, {}), NOW).lower()


def test_report_columns_do_not_overflow_on_wide_negatives(tmp_path):
    """A strong-net-cash name formats netDebtEbitda as e.g. -12.34 (6 chars);
    the column must be wide enough or the whole table misaligns."""
    conn = _stocks_db(tmp_path, {"symbol": "CASHY", "netDebtEbitda": -12.34})
    lines = [ln for ln in candidates.build_report(conn, NOW).splitlines() if "|" in ln]
    assert len({len(ln) for ln in lines}) == 1, "header and rows must be the same width"


def test_report_shows_every_gated_quality_field(tmp_path):
    """A reader must be able to audit why a name cleared each gate; roic5y was
    gated but not rendered in the first cut."""
    conn = _stocks_db(tmp_path, {})
    header = next(ln for ln in candidates.build_report(conn, NOW).splitlines() if "symbol" in ln)
    for label in ("roic", "roic5y", "fcfy", "rev3y", "fS", "rsi"):
        assert label in header


def test_report_uses_the_phoenix_calendar_date(tmp_path):
    """UTC 04:05 is 21:05 the PREVIOUS day in Phoenix. Slicing the timestamp
    would date this report a day ahead — the repo-wide clock invariant."""
    report = candidates.build_report(_stocks_db(tmp_path, {}), "2026-07-26T04:05:00+00:00")
    assert "2026-07-25" in report


# ------------------------------------------------------- connection ----


def test_connect_ro_cannot_write(tmp_path):
    """The reporter's core safety property: it must be structurally unable to
    mutate a source DB, not merely disciplined about it."""
    _stocks_db(tmp_path, {}).close()
    conn = candidates.connect_ro(str(tmp_path / "stocks.db"))
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM v_latest")
    finally:
        conn.close()


def test_connect_ro_rejects_a_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        candidates.connect_ro(str(tmp_path / "absent.db"))


def test_run_reads_a_real_file_end_to_end(tmp_path):
    _stocks_db(tmp_path, {}).close()
    assert "GOOD" in candidates.run(str(tmp_path / "stocks.db"), NOW)


def test_company_key_is_the_hoisted_catalog_constant():
    """The screen and composite's stocks_rsi signal must never disagree about
    what counts as the same business, so both read one hoisted expression."""
    from sources.combiners.composite import catalog

    assert candidates._COMPANY_KEY is catalog.STOCKS_COMPANY_KEY
    assert candidates._PRIMARY_FIRST is catalog.STOCKS_PRIMARY_FIRST
    by_id = {s["signal_id"]: s for s in catalog.SIGNALS}
    assert catalog.STOCKS_COMPANY_KEY in by_id["stocks_rsi"]["sql"]
    assert catalog.STOCKS_PRIMARY_FIRST in by_id["stocks_rsi"]["sql"]
    assert candidates.STOCKS_COMPANY_KEY in candidates._SCREEN_SQL

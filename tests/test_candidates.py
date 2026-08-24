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
    " rsi REAL, ch6m REAL, high52ch REAL, zScore REAL, interestCoverage REAL,"
    " priceDate TEXT, netIncome REAL, operatingCF REAL, assets REAL"
)

# A name that passes every gate. Tests mutate one field at a time off this.
# high52ch is deliberately ABOVE the dislocation branch's bar, so a row here
# qualifies through the RSI branch alone and gate tests stay single-field.
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
    high52ch=-20.0,
    zScore=6.0,
    interestCoverage=12.0,
    priceDate="2026-07-24",
    netIncome=1000.0,
    operatingCF=1500.0,
    assets=10000.0,
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


def test_excludes_roic5y_denominator_blowup(tmp_path):
    """The artifact ceiling applies to the 5y average too: where history
    exists it is gated, NULL-tolerance notwithstanding."""
    conn = _stocks_db(tmp_path, {"symbol": "BLOWUP5", "roic5y": 376.5})
    assert _symbols(conn) == []


def test_excludes_nonpositive_rsi(tmp_path):
    """26 rows carry rsi <= 0 — out of domain for a 0-100 oscillator. The
    composite catalog already guards `rsi > 0` on this same column."""
    conn = _stocks_db(tmp_path, {"symbol": "ZERO", "rsi": 0.0})
    assert _symbols(conn) == []


# ------------------------------------------------- dislocation branches ----
# The dislocation gate is momentum (rsi) OR price level (52w drawdown):
# measured 2026-07-29, a pure-RSI gate kills 113 of the 122 names passing
# every quality gate while missing exactly the large-cap price dislocations
# the screen exists for — 14-day RSI mean-reverts in days, the price stays
# down for months.


def test_deep_52w_drawdown_admits_a_stabilized_name(tmp_path):
    """INTU on 2026-07-29: 61% off its high, fcf yield 9.1, fScore 8 — and
    RSI 62, invisible to a pure-RSI gate because the fall had stabilized."""
    conn = _stocks_db(tmp_path, {"symbol": "INTU", "rsi": 62.0, "high52ch": -45.0})
    assert _symbols(conn) == ["INTU"]


def test_shallow_drawdown_with_high_rsi_is_still_excluded(tmp_path):
    """Neither branch: not oversold, not far off the high — no dislocation."""
    conn = _stocks_db(tmp_path, {"symbol": "FAIR", "rsi": 62.0, "high52ch": -10.0})
    assert _symbols(conn) == []


def test_52w_branch_boundary_is_inclusive(tmp_path):
    conn = _stocks_db(
        tmp_path,
        {"symbol": "EDGE", "rsi": 55.0, "high52ch": candidates.HIGH52_DISLOCATION_MAX},
    )
    assert _symbols(conn) == ["EDGE"]


def test_nonpositive_rsi_is_excluded_even_with_a_deep_drawdown(tmp_path):
    """The rsi > 0 domain guard covers BOTH dislocation branches: a junk
    rsi=0 row must not slip in through the 52w-high door (26 such rows
    exist; unguarded, a $702B phantom qualifies)."""
    conn = _stocks_db(tmp_path, {"symbol": "JUNK", "rsi": 0.0, "high52ch": -60.0})
    assert _symbols(conn) == []


def test_null_high52ch_still_screens_on_rsi(tmp_path):
    """high52ch is an OR branch (1,990/1,991 populated); a NULL there must
    not drop a row that already qualifies on RSI."""
    conn = _stocks_db(tmp_path, {"symbol": "NOHI", "high52ch": None})
    assert _symbols(conn) == ["NOHI"]


def test_null_high52ch_is_not_itself_a_dislocation(tmp_path):
    """The converse pin: when RSI does NOT qualify, a missing high52ch must
    exclude the row, not admit it. Guards against a plausible future
    'NULL-tolerance by analogy' edit (COALESCE-style) copied from the
    roic5y/netDebtEbitda gates two clauses up — SQL's False-OR-NULL already
    does the right thing, and this test keeps it that way."""
    conn = _stocks_db(tmp_path, {"symbol": "NODATA", "rsi": 62.0, "high52ch": None})
    assert _symbols(conn) == []


def test_median_fscore_is_not_admitted(tmp_path):
    """The universe median fScore is 5 (p50, 2026-07-29), and a bar at the
    median binds nothing (N-1 audit: 0 marginal kills of 122) — decorative.
    The bar is 6; Piotroski's own 'high' is 8-9."""
    conn = _stocks_db(tmp_path, {"symbol": "MEDIAN", "fScore": 5.0})
    assert _symbols(conn) == []


@pytest.mark.parametrize(
    "field,edge,passes",
    [
        ("roic", candidates.ROIC_MAX, True),  # BETWEEN is inclusive
        ("roic", candidates.ROIC_MIN, True),
        ("roic5y", candidates.ROIC_MAX, True),  # shares roic's artifact ceiling
        ("roic5y", candidates.ROIC5Y_MIN, True),
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


def test_null_roic5y_is_admitted_like_null_leverage(tmp_path):
    """roic5y is absent for 365 of 1,991 eligible companies — every listing
    younger than five years, including $251B spinoffs (GEV: roic 41%,
    rsi 38.7) — and adds little where present: roic x roic5y correlate
    +0.72. Same policy as netDebtEbitda: absent is not disqualifying,
    present-and-bad is (see test_gate_excludes)."""
    conn = _stocks_db(tmp_path, {"symbol": "SPINCO", "roic5y": None})
    assert _symbols(conn) == ["SPINCO"]


@pytest.mark.parametrize(
    "field", ["marketCap", "dollarVolume", "roic", "fcfYield", "fScore", "rsi"]
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
    conn = _stocks_db(
        tmp_path,
        {"symbol": "MAP", "roic": 33.0, "roic5y": 22.0, "rsi": 41.0, "high52ch": -33.0},
    )
    row = candidates.screen(conn)[0]
    assert row["symbol"] == "MAP"
    assert row["roic"] == 33.0
    assert row["roic5y"] == 22.0
    assert row["rsi"] == 41.0
    assert row["high52ch"] == -33.0


def test_report_renders_empty_without_crash(tmp_path):
    conn = _stocks_db(tmp_path, {"symbol": "TRAP", "fScore": 1.0})
    report = candidates.build_report(conn, NOW)
    assert "no candidates" in report.lower()


def test_report_disclaims_recommendation(tmp_path):
    """This is a screen feeding research-ticker, not a buy list. The report must
    say so on its face — grading is calibration-only and nobody should trade it."""
    conn = _stocks_db(tmp_path, {})
    report = candidates.build_report(conn, NOW)
    assert "not a recommendation" in report.lower()
    assert "GOOD" in report


def test_report_states_grading_is_calibration_only(tmp_path):
    """The scorer grades list entries, but only to calibrate the screen —
    saying so on the report's face is the difference between a candidate
    list and an invented edge."""
    report = candidates.build_report(_stocks_db(tmp_path, {}), NOW).lower()
    assert "calibration" in report
    assert "nothing feeds back" in report


def test_report_columns_do_not_overflow_on_wide_negatives(tmp_path):
    """A strong-net-cash name formats netDebtEbitda as e.g. -12.34 (6 chars);
    the column must be wide enough or the whole table misaligns."""
    conn = _stocks_db(tmp_path, {"symbol": "CASHY", "netDebtEbitda": -12.34})
    lines = [ln for ln in candidates.build_report(conn, NOW).splitlines() if "|" in ln]
    assert len({len(ln) for ln in lines}) == 1, "header and rows must be the same width"


def test_report_columns_hold_the_annotation_extremes(tmp_path):
    """zScore and interestCoverage are UNGATED annotations, so their widths
    must fit the live distribution's tails, not just typical values — the
    2026-07-29 base universe reaches interestCoverage 176,266.99 and
    zScore -36.46 (near-zero denominators, same artifact family as roic)."""
    conn = _stocks_db(
        tmp_path,
        {"symbol": "WIDE", "zScore": -36.4624, "interestCoverage": 176266.98676},
    )
    lines = [ln for ln in candidates.build_report(conn, NOW).splitlines() if "|" in ln]
    assert len({len(ln) for ln in lines}) == 1, "header and rows must be the same width"


def test_report_shows_every_gated_quality_field(tmp_path):
    """A reader must be able to audit why a name cleared each gate — every
    gated column, including the off52w dislocation branch, must render."""
    conn = _stocks_db(tmp_path, {})
    header = next(ln for ln in candidates.build_report(conn, NOW).splitlines() if "symbol" in ln)
    for label in ("roic", "roic5y", "fcfy", "rev3y", "fS", "rsi", "off52w"):
        assert label in header


def test_report_annotates_ungated_risk_columns(tmp_path):
    """zScore and interestCoverage are ANNOTATIONS, never gates — printed so
    the reader sees the leverage dimension netDebtEbitda can miss (TIMB on
    2026-07-29: interest coverage 0.49 beside nde 0.24) without shrinking the
    funnel. No forward-return data exists to justify gating them."""
    conn = _stocks_db(tmp_path, {})
    header = next(ln for ln in candidates.build_report(conn, NOW).splitlines() if "symbol" in ln)
    labels = [c.strip() for c in header.split("|")]
    assert "z" in labels
    assert "intCov" in labels


def test_report_survives_null_annotations(tmp_path):
    """Annotation columns are NULL-tolerant by definition; a None must render
    as n/a, not TypeError inside the CLI report's formatting."""
    conn = _stocks_db(tmp_path, {"zScore": None, "interestCoverage": None, "high52ch": None})
    report = candidates.build_report(conn, NOW)
    assert "GOOD" in report
    assert "n/a" in report


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


# ---------------------------------------------- data-age disclosure ----
# stocks.db does not run at weekends, so every consumer (CLI report, nightly
# push, dashboard) must date its data identically. One helper, one semantics.


def _db_with_snapshot(tmp_path, captured_at, name="s.db"):
    path = tmp_path / name
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE snapshots (id INTEGER PRIMARY KEY, captured_at TEXT)")
    if captured_at is not None:
        conn.execute("INSERT INTO snapshots VALUES (1, ?)", (captured_at,))
    conn.commit()
    return conn


def test_snapshot_date_is_the_phoenix_date_of_the_newest_snapshot(tmp_path):
    """11:00 UTC is 04:00 Phoenix the SAME day; a naive slice would agree here,
    so the fixture below straddles the rollover to make the difference bite."""
    conn = _db_with_snapshot(tmp_path, "2026-07-24T11:00:00+00:00")
    assert candidates.snapshot_date(conn) == "2026-07-24"


def test_snapshot_date_respects_the_phoenix_rollover(tmp_path):
    """04:12 UTC is 21:12 the PREVIOUS day in Phoenix."""
    conn = _db_with_snapshot(tmp_path, "2026-07-25T04:12:00+00:00", name="r.db")
    assert candidates.snapshot_date(conn) == "2026-07-24"


def test_snapshot_date_is_none_without_a_snapshots_table(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "bare.db"))
    conn.execute("CREATE TABLE v_latest (symbol TEXT)")
    assert candidates.snapshot_date(conn) is None


def test_snapshot_date_is_none_on_an_unparseable_timestamp(tmp_path):
    """phx_date raises ValueError on junk, which `except sqlite3.Error` alone
    would not catch — and this function is a dependency of the nightly health
    alert."""
    conn = _db_with_snapshot(tmp_path, "not-a-timestamp", name="junk.db")
    assert candidates.snapshot_date(conn) is None


def test_data_age_label_marks_stale_data(tmp_path):
    assert "2d old" in candidates.data_age_label("2026-07-24", "2026-07-27T04:15:00+00:00")


def test_data_age_label_is_bare_when_current(tmp_path):
    # 04:15 UTC on the 27th is 21:15 Phoenix on the 26th -> same day, no age.
    assert candidates.data_age_label("2026-07-26", "2026-07-27T04:15:00+00:00") == "2026-07-26"


def test_data_age_label_flags_data_dated_ahead_of_the_clock(tmp_path):
    """Clock skew or a restored backup. A bare future date reads as fresh."""
    label = candidates.data_age_label("2026-07-30", "2026-07-27T04:15:00+00:00")
    assert "2026-07-30" in label and "ahead" in label.lower()


def test_data_age_label_handles_a_missing_date(tmp_path):
    assert "unknown" in candidates.data_age_label(None, "2026-07-27T04:15:00+00:00").lower()


def test_data_age_label_degrades_on_an_unparseable_clock(tmp_path):
    """The bare date still informs; never raise inside the health-alert path."""
    assert "2026-07-24" in candidates.data_age_label("2026-07-24", "junk")


# ------------------------------------------------ research context columns ----
# scorer.db is optional input: the ownership call (research_verdicts) and the
# on-list quality trend (v_candidate_quality_trend) annotate the list; the
# screen itself never reads them.


def _scorer_db(tmp_path, verdicts=(), appearances=()):
    from sources.combiners.scorer import db as scorer_db

    conn = scorer_db.connect(str(tmp_path / "scorer.db"))
    scorer_db.ensure_schema(conn)
    for symbol, verdict, date in verdicts:
        conn.execute(
            "INSERT INTO research_verdicts (symbol, verdict, verdict_date, recorded_at)"
            " VALUES (?, ?, ?, ?)",
            (symbol, verdict, date, NOW),
        )
    for symbol, date, fscore in appearances:
        scorer_db.record_appearances(
            conn, [{"symbol": symbol, "fscore": fscore}], date, candidates.SCREEN_VERSION, NOW
        )
    conn.commit()
    return conn


def test_newest_verdict_per_symbol_wins(tmp_path):
    sc = _scorer_db(
        tmp_path,
        verdicts=[
            ("GOOD", "pass", "2026-07-01"),
            ("GOOD", "buy", "2026-07-20"),
            ("X", "pass", "2026-07-05"),
        ],
    )
    assert candidates.newest_verdicts(sc) == {
        "GOOD": ("buy", "2026-07-20"),
        "X": ("pass", "2026-07-05"),
    }


def test_annotate_marks_researched_and_unresearched_rows():
    rows = [{"symbol": "GOOD"}, {"symbol": "NEW"}]
    out = candidates.annotate(
        rows,
        {"GOOD": ("pass", "2026-07-20")},
        {"GOOD": {"days_on_list": 12, "n_sightings": 9, "fscore_entry": 7.0}},
    )
    assert out[0]["verdict"] == "pass" and out[0]["verdict_date"] == "2026-07-20"
    assert out[0]["days_on_list"] == 12 and out[0]["fscore_entry"] == 7.0
    assert out[1]["verdict"] is None and out[1]["days_on_list"] is None
    assert rows[0] == {"symbol": "GOOD"}  # input untouched


def test_report_shows_call_and_tenure_columns(tmp_path):
    conn = _stocks_db(tmp_path, {}, {"symbol": "NEW", "isin": "US2222222222"})
    sc = _scorer_db(
        tmp_path,
        verdicts=[("GOOD", "pass", "2026-07-20")],
        appearances=[("GOOD", "2026-07-10", 8.0), ("GOOD", "2026-07-16", 7.0)],
    )
    report = candidates.build_report(conn, NOW, scorer_conn=sc)
    good = next(line for line in report.splitlines() if line.lstrip().startswith("GOOD"))
    new = next(line for line in report.splitlines() if line.lstrip().startswith("NEW"))
    assert "pass 07-20" in good and "6d/2" in good
    assert "pass" not in new and "—" in new
    assert "call" in report and "tenure" in report


def test_report_summarises_agreement(tmp_path):
    """The pass rows are the screen-says-yes/research-says-no set — the
    disagreement count is the reason the column exists."""
    conn = _stocks_db(
        tmp_path,
        {},
        {"symbol": "B", "isin": "US2222222222"},
        {"symbol": "N", "isin": "US3333333333"},
    )
    sc = _scorer_db(tmp_path, verdicts=[("GOOD", "pass", "2026-07-20"), ("B", "buy", "2026-07-21")])
    report = candidates.build_report(conn, NOW, scorer_conn=sc)
    assert "2 researched: 1 buy, 1 pass; 1 un-researched" in report


def test_report_degrades_without_scorer_db(tmp_path):
    conn = _stocks_db(tmp_path, {})
    report = candidates.build_report(conn, NOW)
    good = next(line for line in report.splitlines() if line.lstrip().startswith("GOOD"))
    assert "—" in good
    assert "scorer.db not read" in report


def test_run_accepts_optional_scorer_db(tmp_path):
    _stocks_db(tmp_path, {}).close()
    _scorer_db(tmp_path, verdicts=[("GOOD", "buy", "2026-07-20")]).close()
    report = candidates.run(str(tmp_path / "stocks.db"), NOW, scorer_db=str(tmp_path / "scorer.db"))
    assert "buy 07-20" in report
    assert "—" in candidates.run(str(tmp_path / "stocks.db"), NOW)


def test_report_tolerates_scorer_db_without_the_trend_view(tmp_path):
    """A scorer.db the nightly run has not migrated yet has research_verdicts
    but no v_candidate_quality_trend; the reporter is read-only and cannot
    create it, so the call column still renders and tenure degrades."""
    conn = _stocks_db(tmp_path, {})
    sc = _scorer_db(tmp_path, verdicts=[("GOOD", "buy", "2026-07-20")])
    sc.execute("DROP VIEW v_candidate_quality_trend")
    report = candidates.build_report(conn, NOW, scorer_conn=sc)
    good = next(line for line in report.splitlines() if line.lstrip().startswith("GOOD"))
    assert "buy 07-20" in good
    assert "trend view absent" in report


# ----------------------------------------------------- accruals annotation ----
# (net income - operating cash flow) / total assets, in percent. Sloan (1996):
# earnings running ahead of cash mean-revert. NEGATIVE is the healthy sign.
# Annotation only until v_candidate_efficacy shows high-accrual entries
# underperform; setting the bar before measuring it is the recorded mistake.


def test_accruals_sign_convention_negative_means_cash_ahead_of_earnings(tmp_path):
    conn = _stocks_db(tmp_path, {"netIncome": 100.0, "operatingCF": 150.0, "assets": 1000.0})
    assert candidates.screen(conn)[0]["accrualsPctAssets"] == -5.0


def test_accruals_is_null_without_assets_or_cash_flow(tmp_path):
    conn = _stocks_db(tmp_path, {"assets": None})
    assert candidates.screen(conn)[0]["accrualsPctAssets"] is None
    conn = _stocks_db(tmp_path, {"assets": 0.0}, name="z.db")
    assert candidates.screen(conn)[0]["accrualsPctAssets"] is None


def test_accruals_is_an_annotation_not_a_gate(tmp_path):
    conn = _stocks_db(tmp_path, {"netIncome": 5000.0, "operatingCF": 100.0, "assets": 10000.0})
    assert _symbols(conn) == ["GOOD"]  # +49% of assets still passes


def test_report_shows_accruals_column(tmp_path):
    report = candidates.build_report(_stocks_db(tmp_path, {}), NOW)
    assert "accr" in report
    good = next(line for line in report.splitlines() if line.lstrip().startswith("GOOD"))
    assert "-5.0" in good

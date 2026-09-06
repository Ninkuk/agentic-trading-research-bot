"""Batch-2 label pass on the Sources cards that scored 3 in the card audit:
words instead of glyphs and codes, units beside numbers, detail columns
folded. Every field the old cards exported is still exported."""

import sqlite3

from dashboard_lib import sources_views

NOW = "2026-07-09T04:12:00+00:00"


def _mem(ddl: str) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ddl)
    return conn


def _view(name: str, cols: list[str], rows: list[tuple]) -> str:
    t = f"t_{name}"
    ddl = f"CREATE TABLE {t}({', '.join(cols)});\n"
    for r in rows:
        vals = ", ".join("NULL" if v is None else repr(v) for v in r)
        ddl += f"INSERT INTO {t} VALUES ({vals});\n"
    return ddl + f"CREATE VIEW {name} AS SELECT * FROM {t};\n"


def _section(sid: str):
    return next(s for s in sources_views.SECTIONS if s[0] == sid)


def _labels(sec):
    return {c["key"]: c["label"] for c in sec["columns"]}


def _hidden(sec):
    return {c["key"] for c in sec["columns"] if c.get("hidden")}


def _keys(sec):
    return [c["key"] for c in sec["columns"]]


# --- Dark pools ----------------------------------------------------------------


def test_dark_pools_tiles_are_captioned_and_the_share_count_is_abbreviated():
    conn = _mem(
        _view(
            "v_top_dark_pools",
            ["ats_name", "mpid", "total_shares", "total_trades"],
            [("INCR INTELLIGENT CROSS LLC", "INCR", 74370826, 948228)],
        )
        + _view(
            "v_latest_off_exchange",
            ["symbol", "total_shares", "total_trades"],
            [("HYG", 437952179, 1), ("SPY", 1, 1)],
        )
    )
    sec = sources_views.dark_pools(conn, NOW)
    tiles = {t["label"]: t for t in sec["tiles"]}
    assert tiles["Venues reporting"]["value"] == 1
    assert tiles["Venues reporting"]["band"] == "last week"
    assert tiles["Symbols traded off exchange"]["value"] == 2
    assert tiles["Shares traded off exchange"]["value"] == "438M"
    assert _labels(sec)["mpid"] == "Venue code"
    assert "mpid" in _hidden(sec)


# --- Energy inventories --------------------------------------------------------


def test_energy_inventories_carry_a_unit_column_and_fold_category():
    conn = _mem(
        _view(
            "v_weekly_change",
            [
                "series_id",
                "label",
                "category",
                "latest_period",
                "latest",
                "prior",
                "change_abs",
                "change_pct",
            ],
            [
                (
                    "crude",
                    "Crude oil stocks (ex-SPR)",
                    "crude",
                    "2026-08-28",
                    424460.0,
                    428910.0,
                    -4450.0,
                    -1.04,
                )
            ],
        )
        + _view(
            "v_series_history",
            ["series_id", "label", "category", "unit", "period", "value"],
            [
                (
                    "crude",
                    "Crude oil stocks (ex-SPR)",
                    "crude",
                    "thousand barrels",
                    "2026-08-21",
                    428910.0,
                )
            ],
        )
    )
    sec = sources_views.energy_inventories(conn, NOW)
    assert sec["rows"][0]["unit"] == "thousand barrels"
    labels = _labels(sec)
    assert labels["label"] == "What"
    assert labels["unit"] == "Unit"
    assert _keys(sec).index("unit") == _keys(sec).index("latest") + 1
    assert "category" in _hidden(sec)


# --- Federal debt --------------------------------------------------------------


def test_federal_debt_tiles_read_in_dollars_with_a_90_day_change():
    conn = _mem(
        _view(
            "v_debt_trend",
            ["record_date", "tot_pub_debt_out"],
            [("2026-06-01", 39.0e12), ("2026-09-03", 40.1029e12)],
        )
        + _view(
            "v_tga_trend",
            ["record_date", "close_balance"],
            [("2026-06-01", 950.0e3), ("2026-09-03", 903.928e3)],
        )
    )
    sec = sources_views.federal_debt(conn, NOW)
    tiles = {t["label"]: t for t in sec["tiles"]}
    assert tiles["National debt"]["value"] == "$40.1T"
    assert tiles["National debt"]["band"] == "90-day change +2.8%"
    assert tiles["Treasury cash"]["value"] == "$904B"
    assert tiles["Treasury cash"]["band"] == "90-day change −4.8%"
    assert len(tiles["National debt"]["history"]) == 2


def test_federal_debt_band_falls_back_to_the_date_with_one_point():
    conn = _mem(
        _view("v_debt_trend", ["record_date", "tot_pub_debt_out"], [("2026-09-03", 40.1e12)])
        + _view("v_tga_trend", ["record_date", "close_balance"], [])
    )
    sec = sources_views.federal_debt(conn, NOW)
    assert [t["label"] for t in sec["tiles"]] == ["National debt"]
    assert sec["tiles"][0]["band"] == "2026-09-03"


# --- FRED --------------------------------------------------------------------


def _fred_conn(zs):
    return _mem(
        _view(
            "v_yoy_change",
            ["series_id", "title", "theme", "latest_date", "latest", "year_ago", "change_pct"],
            [
                (f"S{i}", f"Series {i}", "benchmark", "2026-09-04", 1.0, 1.0, 0.0)
                for i in range(len(zs))
            ],
        )
        + _view("v_zscore", ["series_id", "zscore"], [(f"S{i}", z) for i, z in enumerate(zs)])
        + _view(
            "v_regime_signals",
            ["t10y2y", "yield_curve_inverted", "hy_spread", "fed_funds", "unemployment"],
            [(0.41, 0, 2.65, 3.63, 4.1)],
        )
    )


def test_fred_chip_and_unusual_words_replace_the_sigma():
    sec = sources_views.fred_series(_fred_conn([0.4, -1.5, 2.46, 3.2, None]), NOW)
    assert sec["verdict"] == {
        "text": "2 series unusually far from their own history",
        "tone": "mid",
    }
    assert [r["unusual"] for r in sec["rows"]] == ["normal", "notable", "unusual", "extreme", None]
    keys = _keys(sec)
    assert keys.index("unusual") == keys.index("zscore") - 1
    assert "zscore" in _hidden(sec)
    labels = _labels(sec)
    assert labels["unusual"] == "How unusual"
    assert labels["change_pct"] == "Change, 1 year %"
    assert "σ" not in sec["verdict"]["text"]


# --- EDGAR filings -------------------------------------------------------------


def _filings_conn(view, rows):
    return _mem(_view(view, ["filed_date", "ticker", "company", "form"], rows))


def test_filings_carry_the_form_in_words_and_fold_the_code():
    sec = sources_views.offerings(
        _filings_conn(
            "v_offerings",
            [
                ("2026-09-04", "ACR", "ACRES", "424B5"),
                ("2026-09-04", "ZZZ", "Zed", "S-1"),
                ("2026-09-03", "QQQ", "Q", "S-3ASR"),
                ("2026-09-03", "XYZ", "X", "F-10"),
            ],
        ),
        NOW,
    )
    words = {r["ticker"]: r["form_words"] for r in sec["rows"]}
    assert words == {
        "ACR": "prospectus supplement",
        "ZZZ": "registration statement",
        "QQQ": "registration statement",
        "XYZ": "F-10",
    }
    keys = _keys(sec)
    assert keys.index("form_words") == keys.index("form") + 1
    assert "form" in _hidden(sec)
    assert _labels(sec)["form_words"] == "What was filed"


def test_event_and_stake_filings_name_their_forms():
    events = sources_views.recent_filings(
        _filings_conn("v_events", [("2026-09-04", "ACA", "Arcosa", "8-K")]), NOW
    )
    assert events["rows"][0]["form_words"] == "event report"
    stakes = sources_views.stakes(
        _filings_conn(
            "v_stakes",
            [("2026-09-04", "A", "A", "SC 13D"), ("2026-09-04", "B", "B", "SC 13G/A")],
        ),
        NOW,
    )
    assert [r["form_words"] for r in stakes["rows"]] == ["activist stake", "passive stake"]
    assert (
        _section("stakes")[5]
        == "Someone just crossed 5% ownership, on purpose (13D) or passively (13G)."
    )


# --- Options-market mood -------------------------------------------------------


def test_options_sentiment_tiles_are_named_in_words():
    conn = _mem(
        _view(
            "v_latest_sentiment",
            ["vix_date", "vix_close", "pcr_date", "equity_pcr", "total_pcr", "backwardation"],
            [("2026-09-04", 14.53, "2026-09-03", 0.47, 0.76, 0)],
        )
        + _view(
            "v_vix_term_structure",
            ["date", "close", "vix3m", "vix_vix3m_ratio", "backwardation"],
            [("2026-09-04", 14.53, 17.6, 0.825, 0)],
        )
        + _view(
            "v_pcr_extremes",
            ["date", "equity_pcr_pctile", "equity_flag"],
            [("2026-09-03", 0.08, "complacency")],
        )
    )
    sec = sources_views.options_sentiment(conn, NOW)
    tiles = {t["label"]: t for t in sec["tiles"]}
    assert tiles["Near vs 3-month fear"]["band"] == "contango — calm"
    assert tiles["How rare today's put/call is"]["value"] == 8
    assert tiles["How rare today's put/call is"]["band"] == "complacency"
    assert "VIX ÷ VIX3M" not in tiles and "equity put/call percentile" not in tiles


# --- Reddit ---------------------------------------------------------------------


def test_reddit_headers_say_change_and_fold_upvotes_and_community():
    conn = _mem(
        _view(
            "v_trending",
            [
                "ticker",
                "name",
                "filter",
                "rank",
                "mentions",
                "mention_delta",
                "mention_pct_change",
                "rank_delta",
                "upvotes",
            ],
            [("LULU", "lululemon", "all-stocks", 2, 286, 184, 1.8, 34, 6126)],
        )
        + _view("v_history", ["ticker", "filter", "mentions", "captured_at"], [])
    )
    sec = sources_views.reddit_trending(conn, NOW)
    labels = _labels(sec)
    assert labels["mention_delta"] == "Change in mentions"
    assert labels["mention_pct_change"] == "Change in mentions %"
    assert labels["rank_delta"] == "Rank change"
    assert not any("Δ" in lab for lab in labels.values())
    assert {"upvotes", "filter"} <= _hidden(sec)


# --- SEC XBRL --------------------------------------------------------------------


def test_sec_revisions_name_the_line_item_and_the_form():
    conn = _mem(
        _view(
            "v_revisions",
            ["ticker", "tag", "period_end", "form", "filed", "value", "value_delta"],
            [
                ("FAC", "Assets", "2026-03-31", "S-1", "2026-06-30", 62391000.0, -223996703.0),
                ("FAC", "NetIncomeLoss", "2026-03-31", "10-Q", "2026-06-30", 1.0, 1.0),
                ("FAC", "OperatingLeaseLiability", "2026-03-31", "10-K", "2026-06-30", 1.0, 1.0),
            ],
        )
    )
    sec = sources_views.sec_revisions(conn, NOW)
    tags = [r["tag"] for r in sec["rows"]]
    assert tags == ["Total assets", "Net income", "Operating lease liability"]
    assert [r["form_words"] for r in sec["rows"]] == [
        "registration statement",
        "quarterly report",
        "annual report",
    ]
    assert "form" in _hidden(sec)


def test_sec_screener_headers_are_plain_words():
    conn = _mem(
        _view(
            "v_screener",
            [
                "ticker",
                "name",
                "revenues",
                "net_income",
                "net_margin",
                "roe",
                "debt_to_equity",
                "eps_diluted",
            ],
            [],
        )
    )
    labels = _labels(sources_views.sec_screener(conn, NOW))
    assert labels["roe"] == "Return on equity"
    assert labels["debt_to_equity"] == "Debt vs equity"
    assert labels["eps_diluted"] == "Earnings per share"
    assert labels["net_margin"] == "Profit margin"


# --- Futures positioning follow-up ---------------------------------------------


def _cot_conn(rows):
    cols = [
        "code",
        "name",
        "asset_class",
        "report_date",
        "net_noncomm",
        "cot_index",
        "pct_oi_noncomm_long",
        "pct_oi_noncomm_short",
        "chg_noncomm_long",
        "chg_noncomm_short",
        "chg_oi",
    ]
    return _mem(
        _view("v_positioning", cols, rows)
        + _view("v_extremes", ["code"], [])
        + _view("v_cot_index", ["code", "cot_index", "report_date"], [])
    )


def test_cot_asset_classes_read_as_words_and_five_columns_open():
    conn = _cot_conn(
        [
            ("C1", "CORN", "ags", "2026-09-01", 1, 50.0, 1.0, 1.0, 1, 1, 1),
            ("C2", "YEN", "fx", "2026-09-01", 1, 50.0, 1.0, 1.0, 1, 1, 1),
            ("C3", "RUSSELL", "equity_index", "2026-09-01", 1, 50.0, 1.0, 1.0, 1, 1, 1),
            ("C4", "GOLD", "metals", "2026-09-01", 1, 50.0, 1.0, 1.0, 1, 1, 1),
            ("C5", "ODD", "odd_thing", "2026-09-01", 1, 50.0, 1.0, 1.0, 1, 1, 1),
        ]
    )
    sec = sources_views.cot_positioning(conn, NOW)
    classes = {r["name"]: r["asset_class"] for r in sec["rows"]}
    assert classes == {
        "CORN": "Agriculture",
        "YEN": "Currencies",
        "RUSSELL": "Equity index",
        "GOLD": "Metals",
        "ODD": "Odd thing",
    }
    shown = [c["key"] for c in sec["columns"] if not c.get("hidden")]
    assert shown == ["name", "net", "cot_index", "history", "extreme"]
    assert {"asset_class", "report_date"} <= _hidden(sec)

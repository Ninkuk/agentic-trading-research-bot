"""Beginner-readability rebuild of the Sources cards that scored lowest in
the card audit: grain balance sheets, funding markets, the three COT
positioning cards, unusual options and WASDE. Every field the old cards
exported is still exported; what changes is the headline (tiles/chip), the
column labels, and which columns open folded (`hidden`)."""

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


# --- Grain balance sheets ------------------------------------------------------


def _ag_conn(latest=None, history=None, stocks=None):
    return _mem(
        _view(
            "v_stocks_to_use",
            ["commodity", "period", "ending_stocks", "total_use", "stocks_to_use"],
            stocks
            or [
                ("CORN", "2025", 4.0e9, None, None),
                ("CORN", "2026", 5.29e9, None, None),
                ("WHEAT", "2025", 1.0e9, None, None),
                ("WHEAT", "2026", 0.92e9, None, None),
            ],
        )
        + _view("v_series_history", ["commodity", "metric", "period", "value"], history or [])
        + _view(
            "v_latest_balance",
            ["commodity", "metric", "period", "value", "unit"],
            latest
            or [
                ("CORN", "ENDING_STOCKS", "2026", 5.29e9, "BU"),
                ("CORN", "PRODUCTION", "2026", 16.0e9, "BU"),
                ("WHEAT", "ENDING_STOCKS", "2026", 0.92e9, "BU"),
            ],
        )
    )


def test_ag_balance_tiles_speak_in_crops_and_bushels():
    sec = sources_views.ag_balance(_ag_conn(), NOW)
    tiles = {t["label"]: t for t in sec["tiles"]}
    assert tiles["Corn stockpile"]["value"] == "5.29B bushels"
    assert tiles["Corn stockpile"]["band"] == "2026 crop year"
    assert tiles["Corn harvest"]["value"] == "16.0B bushels"
    assert tiles["Wheat stockpile"]["value"] == "920M bushels"
    assert "ENDING_STOCKS" not in " ".join(tiles)


def test_ag_balance_chip_compares_stockpiles_with_last_year():
    sec = sources_views.ag_balance(_ag_conn(), NOW)
    assert sec["verdict"] == {
        "text": "Stockpiles bigger than last year for 1 of 2 crops",
        "tone": "mid",
    }
    rows = {r["commodity"]: r for r in sec["rows"]}
    assert set(rows) == {"Corn", "Wheat"}
    assert rows["Corn"]["vs_last_year"] > 0 and rows["Wheat"]["vs_last_year"] < 0
    labels = [c["label"] for c in sec["columns"]]
    assert "Crop year" in labels and "Marketing year" not in labels


def test_ag_balance_has_no_chip_without_a_prior_year():
    sec = sources_views.ag_balance(_ag_conn(stocks=[("CORN", "2026", 5.29e9, None, None)]), NOW)
    assert sec["verdict"] is None
    assert sec["rows"][0]["vs_last_year"] is None


# --- Funding markets -----------------------------------------------------------


def _funding_conn(iorb=None, spread=None):
    return _mem(
        _view(
            "v_sofr_latest",
            ["effective_date", "percent_rate", "volume_bn", "iorb", "sofr_iorb_spread"],
            [("2026-07-08", 3.66, 2949.0, iorb, spread)],
        )
        + _view("v_soma_runoff", ["as_of_date", "par_value"], [("2026-07-07", 6.36e12)])
        + _view("v_rrp_trend", ["operation_date", "take_up"], [("2026-07-08", 0.675e9)])
    )


def test_funding_markets_tiles_are_named_in_words():
    sec = sources_views.funding_markets(_funding_conn(iorb=3.65, spread=0.01), NOW)
    labels = [t["label"] for t in sec["tiles"]]
    assert labels == [
        "Overnight lending rate (SOFR)",
        "Rate the Fed pays banks (IORB)",
        "Gap between them",
        "Overnight lending volume",
        "Fed's holdings",
        "Reverse repo parked at the Fed",
    ]
    tiles = {t["label"]: t for t in sec["tiles"]}
    assert tiles["Gap between them"]["band"] == "calm" and tiles["Gap between them"]["tone"] == "on"
    assert tiles["Overnight lending volume"]["band"] == "$bn · 2026-07-08"
    assert tiles["Fed's holdings"]["band"] == "$T · 2026-07-07"
    assert tiles["Reverse repo parked at the Fed"]["band"] == "$B · 2026-07-08"


def test_funding_markets_omits_tiles_with_no_value():
    sec = sources_views.funding_markets(_funding_conn(), NOW)
    labels = [t["label"] for t in sec["tiles"]]
    assert "Rate the Fed pays banks (IORB)" not in labels
    assert "Gap between them" not in labels
    assert all(t["value"] is not None for t in sec["tiles"])


def test_funding_markets_about_has_one_block_per_number():
    about = _section("funding-markets")[6]
    headings = [h for h, _ in about]
    assert headings == [
        "Overnight lending rate",
        "Rate the Fed pays banks",
        "Gap between them",
        "Overnight lending volume",
        "Fed's holdings",
        "Reverse repo",
    ]


# --- Futures positioning (three COT cards) -------------------------------------


def _cot_columns(sid: str):
    fn = _section(sid)[3]
    conn = _mem(
        _view(
            {
                "cot-positioning": "v_positioning",
                "cot-disaggregated": "v_disagg_positioning",
                "cot-financial": "v_leveraged_funds_positioning",
            }[sid],
            [
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
                "net_mm",
                "pct_oi_mm_long",
                "pct_oi_mm_short",
                "chg_mm_long",
                "chg_mm_short",
                "net_lev",
                "pct_oi_lev_long",
                "pct_oi_lev_short",
                "chg_lev_long",
                "chg_lev_short",
            ],
            [],
        )
        + _view("v_extremes", ["code"], [])
        + _view("v_managed_money_extremes", ["code"], [])
        + _view("v_leveraged_funds_extremes", ["code"], [])
        + _view("v_cot_index", ["code", "cot_index", "report_date"], [])
        + _view("v_disagg_cot_index", ["code", "cot_index", "report_date"], [])
        + _view("v_tff_cot_index", ["code", "cot_index", "report_date"], [])
        + _view("v_disagg_cot_index_commercial_latest", ["code", "cot_index"], [])
        + _view("v_tff_cot_index_dealer_latest", ["code", "cot_index"], [])
    )
    return fn(conn, NOW)["columns"]


def test_cot_cards_open_with_five_plain_columns_and_fold_the_rest():
    for sid in ("cot-positioning", "cot-disaggregated", "cot-financial"):
        cols = _cot_columns(sid)
        shown = [c["key"] for c in cols if not c.get("hidden")]
        assert shown == ["name", "net", "cot_index", "history", "extreme"]
        hidden = {c["key"] for c in cols if c.get("hidden")}
        assert {
            "asset_class",
            "report_date",
            "pct_long",
            "pct_short",
            "chg_long",
            "chg_short",
            "chg_oi",
        } <= hidden
        labels = {c["key"]: c["label"] for c in cols}
        assert labels["cot_index"] == "How stretched (0–100)"
        assert labels["chg_long"] == "Change in longs"
        assert labels["pct_long"] == "Long share of open interest"
        assert not any("Δ" in lab or "% OI" in lab for lab in labels.values())


def test_cot_secondary_index_is_folded_and_the_legacy_card_is_retitled():
    assert "secondary_index" in {c["key"] for c in _cot_columns("cot-financial") if c.get("hidden")}
    assert _section("cot-positioning")[1] == "Futures positioning — all contracts"


# --- Unusual options and WASDE -------------------------------------------------


def test_unusual_options_headers_and_about_speak_plainly():
    labels = {c["key"]: c["label"] for c in sources_views._UNUSUAL_COLUMNS}
    assert labels["vol_oi_ratio"] == "Today's volume vs contracts held"
    assert labels["iv"] == "Implied volatility"
    about = " ".join(b for _, b in _section("unusual-options")[6]).lower()
    assert "implied volatility" in about and "contracts held" in about


def test_wasde_is_titled_and_labelled_in_words():
    assert _section("wasde")[1] == "World grain supply"
    labels = {c["key"]: c["label"] for c in sources_views._WASDE_COLUMNS}
    assert labels["market_year"] == "Crop year"
    assert labels["stocks_to_use"] == "In storage vs a year's use"
    assert sources_views._WASDE_COLUMNS[5]["term"] == "Stocks-to-use"
    about = " ".join(b for _, b in _section("wasde")[6]).lower()
    assert "storage" in about

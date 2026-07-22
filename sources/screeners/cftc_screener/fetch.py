# cftc_screener/fetch.py
import json
import time
import urllib.parse

import sources.common.http_client as http_client

_HOST = "https://publicreporting.cftc.gov/resource/{}.json"
_LEGACY_DATASET = "6dca-aqww"
API_URL = _HOST.format(_LEGACY_DATASET)  # legacy default; back-compat
_UA = {"User-Agent": "agentic-trading-research-bot ninadk.dev@gmail.com"}

_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})  # Socrata throttles with 429
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_LIMIT = 50000  # Socrata max; > full weekly history for any market

# (db_column, socrata_field) for integer-valued columns. All "_all" (all
# contracts) except the spread field, which the API names WITHOUT the suffix.
_INT_FIELDS = [
    ("open_interest", "open_interest_all"),
    ("noncomm_long", "noncomm_positions_long_all"),
    ("noncomm_short", "noncomm_positions_short_all"),
    ("noncomm_spread", "noncomm_positions_spread"),
    ("comm_long", "comm_positions_long_all"),
    ("comm_short", "comm_positions_short_all"),
    ("nonrept_long", "nonrept_positions_long_all"),
    ("nonrept_short", "nonrept_positions_short_all"),
    ("chg_oi", "change_in_open_interest_all"),
    ("chg_noncomm_long", "change_in_noncomm_long_all"),
    ("chg_noncomm_short", "change_in_noncomm_short_all"),
    ("chg_comm_long", "change_in_comm_long_all"),
    ("chg_comm_short", "change_in_comm_short_all"),
    ("traders_total", "traders_tot_all"),
    ("traders_noncomm_long", "traders_noncomm_long_all"),
    ("traders_noncomm_short", "traders_noncomm_short_all"),
    ("traders_comm_long", "traders_comm_long_all"),
    ("traders_comm_short", "traders_comm_short_all"),
]
_FLOAT_FIELDS = [
    ("pct_oi_noncomm_long", "pct_of_oi_noncomm_long_all"),
    ("pct_oi_noncomm_short", "pct_of_oi_noncomm_short_all"),
    ("pct_oi_comm_long", "pct_of_oi_comm_long_all"),
    ("pct_oi_comm_short", "pct_of_oi_comm_short_all"),
    ("conc_net_4_long", "conc_net_le_4_tdr_long_all"),
    ("conc_net_8_long", "conc_net_le_8_tdr_long_all"),
    ("conc_net_4_short", "conc_net_le_4_tdr_short_all"),
    ("conc_net_8_short", "conc_net_le_8_tdr_short_all"),
]

_urlopen = http_client.make_opener(_UA)  # default opener, no app token

# Unified (db_column, socrata_field, cast) triples. Legacy is assembled from the
# existing int/float lists so its field names live in exactly one place.
LEGACY_FIELDS = [(c, api, int) for c, api in _INT_FIELDS] + [
    (c, api, float) for c, api in _FLOAT_FIELDS
]

# Disaggregated Futures-Only (72hh-3qpy). Producer/Merchant + Swap Dealers
# (hedgers); Managed Money + Other Reportables (speculators); Nonreportable.
# 🟡 socrata field names follow CFTC's published Disaggregated schema — confirm
# live (Step 8).
DISAGG_FIELDS = [
    ("open_interest", "open_interest_all", int),
    ("prod_merc_long", "prod_merc_positions_long", int),
    ("prod_merc_short", "prod_merc_positions_short", int),
    ("swap_long", "swap_positions_long_all", int),
    # NOTE: the live 72hh-3qpy schema really does spell swap short/spread with a
    # DOUBLE underscore ("swap__positions_...") while swap long uses a single
    # one. Verified live 2026-07-03 — do NOT "fix" the typo, or these store NULL.
    ("swap_short", "swap__positions_short_all", int),
    ("swap_spread", "swap__positions_spread_all", int),
    ("mm_long", "m_money_positions_long_all", int),
    ("mm_short", "m_money_positions_short_all", int),
    ("mm_spread", "m_money_positions_spread", int),
    ("other_rept_long", "other_rept_positions_long", int),
    ("other_rept_short", "other_rept_positions_short", int),
    ("other_rept_spread", "other_rept_positions_spread", int),
    ("nonrept_long", "nonrept_positions_long_all", int),
    ("nonrept_short", "nonrept_positions_short_all", int),
    ("chg_oi", "change_in_open_interest_all", int),
    ("chg_mm_long", "change_in_m_money_long_all", int),
    ("chg_mm_short", "change_in_m_money_short_all", int),
    ("chg_swap_long", "change_in_swap_long_all", int),
    ("chg_swap_short", "change_in_swap_short_all", int),
    ("pct_oi_mm_long", "pct_of_oi_m_money_long_all", float),
    ("pct_oi_mm_short", "pct_of_oi_m_money_short_all", float),
    ("pct_oi_swap_long", "pct_of_oi_swap_long_all", float),
    ("pct_oi_swap_short", "pct_of_oi_swap_short_all", float),
    ("traders_total", "traders_tot_all", int),
    ("traders_mm_long", "traders_m_money_long_all", int),
    ("traders_mm_short", "traders_m_money_short_all", int),
    ("conc_net_4_long", "conc_net_le_4_tdr_long_all", float),
    ("conc_net_8_long", "conc_net_le_8_tdr_long_all", float),
    ("conc_net_4_short", "conc_net_le_4_tdr_short_all", float),
    ("conc_net_8_short", "conc_net_le_8_tdr_short_all", float),
]

# Traders in Financial Futures (gpe5-46if). Dealer/Intermediary (sell-side);
# Asset Manager/Institutional; Leveraged Funds (the key gauge); Other
# Reportables; Nonreportable. 🟡 confirm field names live (Step 8).
TFF_FIELDS = [
    ("open_interest", "open_interest_all", int),
    ("dealer_long", "dealer_positions_long_all", int),
    ("dealer_short", "dealer_positions_short_all", int),
    ("dealer_spread", "dealer_positions_spread_all", int),
    ("asset_mgr_long", "asset_mgr_positions_long", int),
    ("asset_mgr_short", "asset_mgr_positions_short", int),
    ("asset_mgr_spread", "asset_mgr_positions_spread", int),
    ("lev_long", "lev_money_positions_long", int),
    ("lev_short", "lev_money_positions_short", int),
    ("lev_spread", "lev_money_positions_spread", int),
    ("other_rept_long", "other_rept_positions_long", int),
    ("other_rept_short", "other_rept_positions_short", int),
    ("other_rept_spread", "other_rept_positions_spread", int),
    ("nonrept_long", "nonrept_positions_long_all", int),
    ("nonrept_short", "nonrept_positions_short_all", int),
    ("chg_oi", "change_in_open_interest_all", int),
    ("chg_lev_long", "change_in_lev_money_long", int),
    ("chg_lev_short", "change_in_lev_money_short", int),
    ("chg_asset_mgr_long", "change_in_asset_mgr_long", int),
    ("chg_asset_mgr_short", "change_in_asset_mgr_short", int),
    ("pct_oi_lev_long", "pct_of_oi_lev_money_long", float),
    ("pct_oi_lev_short", "pct_of_oi_lev_money_short", float),
    ("pct_oi_asset_mgr_long", "pct_of_oi_asset_mgr_long", float),
    ("pct_oi_asset_mgr_short", "pct_of_oi_asset_mgr_short", float),
    ("traders_total", "traders_tot_all", int),
    ("traders_lev_long", "traders_lev_money_long_all", int),
    ("traders_lev_short", "traders_lev_money_short_all", int),
    ("conc_net_4_long", "conc_net_le_4_tdr_long_all", float),
    ("conc_net_8_long", "conc_net_le_8_tdr_long_all", float),
    ("conc_net_4_short", "conc_net_le_4_tdr_short_all", float),
    ("conc_net_8_short", "conc_net_le_8_tdr_short_all", float),
]


def _build_url(
    code: str, dataset_id: str = _LEGACY_DATASET, since=None, start=None, limit: int = _LIMIT
) -> str:
    """Socrata SODA query for one market on ``dataset_id``, ordered by report date
    ascending. ``since`` (YYYY-MM-DD) fetches strictly newer weeks; else ``start``
    sets an inclusive floor; else full history."""
    clauses = [f"cftc_contract_market_code='{code}'"]
    if since:
        clauses.append(f"report_date_as_yyyy_mm_dd > '{since}T00:00:00'")
    elif start:
        clauses.append(f"report_date_as_yyyy_mm_dd >= '{start}T00:00:00'")
    params = {
        "$where": " AND ".join(clauses),
        "$order": "report_date_as_yyyy_mm_dd",
        "$limit": limit,
    }
    return f"{_HOST.format(dataset_id)}?{urllib.parse.urlencode(params)}"


def _headers(app_token=None) -> dict:
    """Request headers; add the Socrata app token when present."""
    return {**_UA, "X-App-Token": app_token} if app_token else dict(_UA)


def _make_opener(app_token=None):
    """Opener that attaches X-App-Token when a token is given; else the default
    (identity-comparable to _urlopen)."""
    return http_client.make_opener(_headers(app_token)) if app_token else _urlopen


def _http_get(
    url: str,
    opener=_urlopen,
    attempts: int = _MAX_ATTEMPTS,
    base_delay: float = _BASE_DELAY,
    sleep=time.sleep,
) -> str:
    """GET with bounded backoff, retrying Socrata throttling (429) and transient
    5xx/network errors. Other HTTP errors raise immediately."""
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts, base_delay, sleep)


def _num(raw, cast):
    if raw is None or raw == "":
        return None
    try:
        return cast(raw)
    except (TypeError, ValueError):
        return None


def parse_rows(records: list, field_map=LEGACY_FIELDS) -> list[dict]:
    """Map Socrata records to curated rows using ``field_map`` — a list of
    (db_column, socrata_field, cast) triples. Coerce numeric strings, absent
    cells to None, and truncate the report timestamp to YYYY-MM-DD. Records
    missing a code or report date are skipped."""
    out = []
    for rec in records:
        code = rec.get("cftc_contract_market_code")
        raw_date = rec.get("report_date_as_yyyy_mm_dd")
        if not code or not raw_date:
            continue
        row = {
            "code": code,
            "report_date": raw_date[:10],
            "name": rec.get("market_and_exchange_names"),
        }
        for col, api, cast in field_map:
            row[col] = _num(rec.get(api), cast)
        out.append(row)
    return out


def fetch_market_rows(
    code: str,
    dataset_id: str = _LEGACY_DATASET,
    field_map=LEGACY_FIELDS,
    app_token=None,
    since=None,
    start=None,
    get=_http_get,
    opener=None,
) -> list[dict]:
    """Fetch one market's COT rows from ``dataset_id`` using ``field_map``
    (incremental when ``since`` given)."""
    op = opener if opener is not None else _make_opener(app_token)
    url = _build_url(code, dataset_id, since=since, start=start)
    return parse_rows(json.loads(get(url, opener=op)), field_map)

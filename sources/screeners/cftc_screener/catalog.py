from collections.abc import Iterable
from dataclasses import dataclass

from sources.screeners.cftc_screener import fetch


@dataclass(frozen=True)
class Market:
    code: str  # cftc_contract_market_code — the stable key
    name: str  # human label (canonical name refreshed from newest row at write time)
    asset_class: str  # equity_index|rates|fx|metals|energy|ags|softs


# Curated COT reader. Codes verified live against the Socrata API on
# 2026-07-03; any that return no rows at implementation time are dropped or
# corrected here (see Task 1 Step 4).
CATALOG: list[Market] = [
    # equity_index
    Market("13874A", "E-Mini S&P 500", "equity_index"),
    Market("209742", "E-Mini Nasdaq-100", "equity_index"),
    Market("239742", "E-Mini Russell 2000", "equity_index"),
    Market("124603", "E-Mini Dow ($5)", "equity_index"),
    Market("1170E1", "VIX Futures", "equity_index"),
    # rates
    Market("042601", "2-Year T-Note", "rates"),
    Market("044601", "5-Year T-Note", "rates"),
    Market("043602", "10-Year T-Note", "rates"),
    Market("020601", "U.S. Treasury Bond", "rates"),
    Market("045601", "30-Day Fed Funds", "rates"),
    # fx
    Market("099741", "Euro FX", "fx"),
    Market("097741", "Japanese Yen", "fx"),
    Market("096742", "British Pound", "fx"),
    Market("092741", "Swiss Franc", "fx"),
    Market("090741", "Canadian Dollar", "fx"),
    Market("232741", "Australian Dollar", "fx"),
    Market("098662", "U.S. Dollar Index", "fx"),
    # metals
    Market("088691", "Gold", "metals"),
    Market("084691", "Silver", "metals"),
    Market("085692", "Copper", "metals"),
    Market("076651", "Platinum", "metals"),
    # energy
    Market("067651", "WTI Crude Oil", "energy"),
    Market("023651", "Natural Gas (Henry Hub)", "energy"),
    Market("111659", "RBOB Gasoline", "energy"),
    Market("022651", "NY Harbor ULSD", "energy"),
    # ags
    Market("002602", "Corn", "ags"),
    Market("005602", "Soybeans", "ags"),
    Market("001602", "Chicago Wheat (SRW)", "ags"),
    Market("007601", "Soybean Oil", "ags"),
    Market("057642", "Live Cattle", "ags"),
    Market("054642", "Lean Hogs", "ags"),
    # softs
    Market("080732", "Sugar No. 11", "softs"),
    Market("083731", "Coffee C", "softs"),
    Market("033661", "Cotton No. 2", "softs"),
    Market("073732", "Cocoa", "softs"),
]


# The legacy catalog cleanly partitions by asset class: physical commodities are
# reported under Disaggregated, financial futures under TFF. Deriving the
# per-family catalogs from CATALOG keeps the verified contract codes in one place.
_PHYSICAL = {"metals", "energy", "ags", "softs"}
_FINANCIAL = {"equity_index", "rates", "fx"}
DISAGG_CATALOG: list[Market] = [m for m in CATALOG if m.asset_class in _PHYSICAL]
TFF_CATALOG: list[Market] = [m for m in CATALOG if m.asset_class in _FINANCIAL]


@dataclass(frozen=True)
class Family:
    name: str  # legacy | disaggregated | tff
    dataset_id: str  # Socrata resource id
    catalog: list  # list[Market] the family reports
    fact_table: str  # cot | cot_disagg | cot_tff
    field_map: list  # (db_column, socrata_field, cast) triples for this family


LEGACY = Family("legacy", fetch._LEGACY_DATASET, CATALOG, "cot", fetch.LEGACY_FIELDS)
DISAGG = Family("disaggregated", "72hh-3qpy", DISAGG_CATALOG, "cot_disagg", fetch.DISAGG_FIELDS)
TFF = Family("tff", "gpe5-46if", TFF_CATALOG, "cot_tff", fetch.TFF_FIELDS)

# SUPPLEMENTAL (Commodity Index Traders, 13 ag markets, combined F&O) is a
# non-goal for this cut: its dataset id and columns are unconfirmed. Add a fourth
# Family here (and a `cot_supp` table + views in db.py) once verified live.
FAMILIES: dict[str, Family] = {f.name: f for f in (LEGACY, DISAGG, TFF)}


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list[str]:
    """Resolve the ordered, de-duplicated codes to fetch: ``only`` (or the full
    catalog) minus ``exclude``, then any ``add`` codes appended. Tokens are
    stripped; blanks and duplicates are dropped."""
    ids = list(only) if only else list(all_ids)
    ex = {e.strip() for e in (exclude or ())}
    out, seen = [], set()
    for i in list(ids) + list(add or ()):
        i = i.strip()
        if not i or i in ex or i in seen:
            continue
        seen.add(i)
        out.append(i)
    return out

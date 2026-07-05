"""The deterministic promotion gates, G1..G6 + sizing. Pure functions over
plain dicts — no I/O — so every gate is independently testable. Each gate
returns (passed, rejections); every kill carries its gate name (auditability
is the point of a deterministic funnel)."""
import json
import math

from pipeline.promote import catalog


def normalize_det_score(lead: dict):
    """det_score in [0,1] as DIRECTIONAL EXTREMITY (spec pin): a short at COT
    index 5 scores 0.95 — shorts compete on equal footing. Unknown signals
    normalize to None (excluded from the group mean)."""
    direction = lead["direction"]
    if lead["signal"] == "cot_commercial_extreme":
        if lead["score"] is None:
            return None
        frac = lead["score"] / 100.0
        return frac if direction == "long" else 1.0 - frac
    if lead["signal"] == "quality_composite":
        pct = lead.get("rank_pct")
        if pct is None:
            return None
        return pct if direction == "long" else 1.0 - pct
    return None


def group_leads(leads: list) -> tuple:
    """G1: one working row per (instrument, direction). det_score =
    equal-weight mean of member scores (1/N; "learned weights beat 1/N" was
    refuted). horizon_band = longest member band; as_of_date = max member."""
    grouped = {}
    for lead in leads:
        key = (lead["instrument"], lead["direction"])
        det = normalize_det_score(lead)
        member = {"signal": lead["signal"], "det_score": det,
                  "as_of_date": lead["as_of_date"]}
        try:
            detail = json.loads(lead.get("details") or "{}")
        except ValueError:
            detail = {}
        g = grouped.setdefault(key, {
            "instrument": lead["instrument"],
            "instrument_kind": lead["instrument_kind"],
            "direction": lead["direction"],
            "members": [], "details": []})
        g["members"].append(member)
        g["details"].append(detail)
        band = lead["horizon_band"]
        if ("horizon_band" not in g or catalog.HORIZON_ORDER.get(band, 0)
                > catalog.HORIZON_ORDER.get(g["horizon_band"], 0)):
            g["horizon_band"] = band
        g["as_of_date"] = max(g.get("as_of_date", ""), lead["as_of_date"])

    groups, rejections = [], []
    for g in grouped.values():
        scored = [m for m in g["members"] if m["det_score"] is not None]
        if not scored:
            rejections.append({"instrument": g["instrument"],
                               "direction": g["direction"],
                               "gate": "data_missing",
                               "reason": "no normalizable signal"})
            continue
        g["det_score"] = sum(m["det_score"] for m in scored) / len(scored)
        g["signals"] = scored
        del g["members"]
        groups.append(g)
    return groups, rejections


def _reject(g, gate, reason):
    return {"instrument": g["instrument"], "direction": g["direction"],
            "gate": gate, "reason": reason}


def gate_direction(groups, allow_short: bool) -> tuple:
    """G2: cash-account reality — shorts drop unless enabled."""
    if allow_short:
        return list(groups), []
    passed = [g for g in groups if g["direction"] == "long"]
    rejections = [_reject(g, "direction", "allow_short=False")
                  for g in groups if g["direction"] != "long"]
    return passed, rejections


def gate_liquidity(groups, liquidity_by_kind: dict, cfg) -> tuple:
    """G3: price + dollar-volume floors. Survivors get their liquidity fields
    attached; a lead with no row in the relevant DB is data_missing (every
    kill is logged, not just printed). ETF sector = the lead's asset_class
    (Stage 1 D2 contract); ETFs have no earnings date."""
    passed, rejections = [], []
    for g in groups:
        liq = (liquidity_by_kind.get(g["instrument_kind"]) or {}).get(
            g["instrument"])
        if liq is None or liq.get("price") is None:
            rejections.append(_reject(
                g, "data_missing",
                f"no {g['instrument_kind']} liquidity row"))
            continue
        price = liq["price"]
        dollar_volume = liq.get("dollarVolume") or 0.0
        if price < cfg.price_floor:
            rejections.append(_reject(
                g, "liquidity", f"price {price} < {cfg.price_floor}"))
            continue
        if dollar_volume < cfg.dollar_volume_floor:
            rejections.append(_reject(
                g, "liquidity",
                f"dollar_volume {dollar_volume} < {cfg.dollar_volume_floor}"))
            continue
        g = dict(g)
        g["price"] = price
        g["atr"] = liq.get("atr")
        g["average_volume"] = liq.get("averageVolume") or 0.0
        g["dollar_volume"] = dollar_volume
        if g["instrument_kind"] == "etf":
            g["sector"] = next((d.get("asset_class") for d in g["details"]
                                if d.get("asset_class")), None)
            g["next_earnings_date"] = None
        else:
            g["sector"] = liq.get("sector")
            g["next_earnings_date"] = liq.get("nextEarningsDate")
        passed.append(g)
    return passed, rejections


def gate_crowding(groups, crowding: dict, cfg) -> tuple:
    """G3b: pump defense — kill when retail attention is extreme relative to
    the name's OWN baseline (board rank <= N AND mentions >= X * trailing
    norm; absolute mentions can't work — SPY is always chattered about, and
    the per-name norm means ETFs need no special case). Absence from
    reddit.db or a thin baseline = calm = pass free. Survivors with a usable
    baseline get retail_attention_z appended to details — the Tier 2 metric
    that crosses the Stage 3 mask as data (never identity)."""
    passed, rejections = [], []
    for g in groups:
        c = crowding.get(g["instrument"])
        if (c is None or c["n"] < cfg.crowding_min_n
                or not c["baseline_mean"]):
            passed.append(g)
            continue
        mentions = c["mentions"] or 0
        if (c["rank"] is not None and c["rank"] <= cfg.crowding_rank_max
                and mentions >= cfg.crowding_mult * c["baseline_mean"]):
            rejections.append(_reject(
                g, "crowding",
                f"rank {c['rank']} <= {cfg.crowding_rank_max} and mentions "
                f"{mentions} >= {cfg.crowding_mult}x baseline "
                f"{c['baseline_mean']:.1f}"))
            continue
        if c["baseline_std"]:
            g = dict(g)
            g["details"] = list(g["details"]) + [{
                "retail_attention_z": round(
                    (mentions - c["baseline_mean"]) / c["baseline_std"], 2)}]
        passed.append(g)
    return passed, rejections


def gate_confluence(groups, cfg) -> tuple:
    """G4: >= 2 distinct signals, OR a single signal at strong extreme.
    (In v1 the two legs cover disjoint instruments, so promotion reduces to
    the strong-extreme arm — the multi-signal arm is future-proofing for the
    momentum/carry legs, by design.)"""
    passed, rejections = [], []
    for g in groups:
        distinct_signals = {m["signal"] for m in g["signals"]}
        if len(distinct_signals) >= 2 or g["det_score"] >= cfg.strong_extreme:
            passed.append(g)
        else:
            rejections.append(_reject(
                g, "confluence",
                f"single signal, det_score {g['det_score']:.3f} "
                f"< {cfg.strong_extreme}"))
    return passed, rejections


def gate_sector_cap(groups, cfg) -> tuple:
    """G5: max N per sector/asset_class (the v1 same-bet proxy for |rho|>0.70
    clustering). Deterministic: keep highest det_score, ties by instrument."""
    ordered = sorted(groups, key=lambda g: (-g["det_score"], g["instrument"]))
    counts, passed, rejections = {}, [], []
    for g in ordered:
        sector = g.get("sector") or "unknown"
        if counts.get(sector, 0) < cfg.sector_cap:
            counts[sector] = counts.get(sector, 0) + 1
            passed.append(g)
        else:
            rejections.append(_reject(
                g, "sector_cap", f"{sector} already has {cfg.sector_cap}"))
    return passed, rejections


def gate_max_positions(groups, cfg) -> tuple:
    """G6: hard cap — top N by det_score (ties by instrument)."""
    ordered = sorted(groups, key=lambda g: (-g["det_score"], g["instrument"]))
    passed = ordered[:cfg.max_positions]
    rejections = [_reject(g, "max_positions",
                          f"rank > {cfg.max_positions}")
                  for g in ordered[cfg.max_positions:]]
    return passed, rejections


def _floor_shares(x: float, fractional: bool):
    """Round DOWN to the order increment: whole shares, or the 1e-6 quantum
    Robinhood accepts for fractional equity orders. Mirrored in
    pipeline/gate/resolve.py — keep the two in lockstep (replay re-derives
    with the gate copy)."""
    if fractional:
        return math.floor(x * 1_000_000 + 1e-6) / 1_000_000
    return math.floor(x)


def gate_notional_book(candidates: list, equity: float) -> tuple:
    """Cohort-level overdraft guard: whole-candidate cuts, ascending
    (det_score, instrument) — mirroring Stage 3's heat_cut — until cumulative
    shares*price fits inside equity (cash-account buying power proxy until
    portfolio.db supplies real cash). Runs AFTER sizing."""
    total = sum(c["shares"] * c["price"] for c in candidates)
    cuts, rejections = set(), []
    for c in sorted(candidates, key=lambda c: (c["det_score"],
                                               c["instrument"])):
        if total <= equity:
            break
        total -= c["shares"] * c["price"]
        cuts.add((c["instrument"], c["direction"]))
        rejections.append(_reject(
            c, "notional",
            f"cohort notional exceeds equity {equity:.2f}"))
    passed = [c for c in candidates
              if (c["instrument"], c["direction"]) not in cuts]
    return passed, rejections


def size_candidate(group: dict, equity: float, regime_scalar: float,
                   cfg) -> tuple:
    """Fixed-fractional / ATR sizing with the sqrt-law participation cap.
    Kelly is explicitly NOT used (p/b too noisy on slow signals). Notional
    is capped at equity (a cash account cannot overdraft on one order) and
    dust under min_notional is rejected rather than ordered. Returns
    (candidate_row, None) or (None, rejection). Portfolio heat is Stage 3's
    job, after the LLM clamp; the cohort-level notional check is
    gate_notional_book's."""
    atr = group.get("atr") or 0.0
    stop_distance = atr * cfg.atr_mult
    if stop_distance <= 0:
        return None, _reject(group, "size_zero",
                             f"degenerate stop (atr={atr})")
    price = group["price"]
    risk_dollars = equity * cfg.risk_fraction * regime_scalar
    raw = risk_dollars / stop_distance
    raw = min(raw, cfg.participation_cap * group["average_volume"])
    notional_cap = equity / price if price > 0 else 0.0
    clamped_by_notional = raw > notional_cap
    raw = min(raw, notional_cap)
    shares = _floor_shares(raw, cfg.fractional_shares)
    if shares <= 0 or shares * price < cfg.min_notional:
        if clamped_by_notional or shares > 0:
            return None, _reject(
                group, "notional",
                f"notional {shares * price:.2f} vs equity {equity:.2f} / "
                f"min_notional {cfg.min_notional}")
        return None, _reject(group, "size_zero",
                             "floor/participation cap left 0 shares")
    stop_price = (price - stop_distance if group["direction"] == "long"
                  else price + stop_distance)
    return {
        "instrument": group["instrument"],
        "instrument_kind": group["instrument_kind"],
        "direction": group["direction"],
        "det_score": group["det_score"],
        "horizon_band": group["horizon_band"],
        "signals": json.dumps(group["signals"], separators=(",", ":")),
        "price": price, "atr": group.get("atr"),
        "sector": group.get("sector"),
        "next_earnings_date": group.get("next_earnings_date"),
        "shares": shares, "stop_price": stop_price,
        "stop_distance": stop_distance, "risk_dollars": risk_dollars,
        "realized_risk": shares * stop_distance,
        "size_lo": 0, "size_hi": shares,   # reduce-only: LLM can never add
        "as_of_date": group["as_of_date"],
        "details": json.dumps(group["details"], separators=(",", ":")),
    }, None

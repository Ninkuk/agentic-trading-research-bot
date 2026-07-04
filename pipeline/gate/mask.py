"""Data-layer masking (spec: prompt-level guardrails provably fail) + the
canonical hashing used for input pinning. The mask table (real <-> alias)
exists only in Python. Known residual, accepted and documented: sector +
metric shape can still fingerprint a mega-cap or flagship ETF — data-layer
masking reduces memorized-ticker bias, it cannot eliminate it."""
import hashlib
from datetime import date, datetime

from pipeline.gate import catalog


def sha256_canonical(obj) -> str:
    return hashlib.sha256(catalog.canonical_json(obj).encode()).hexdigest()


def parse_input_row(row: dict) -> dict:
    """Reparse the TEXT JSON columns so hashing/checkpointing never depends on
    stored-text formatting (hash the DATA, not the serialization)."""
    import json
    out = dict(row)
    for col in ("signals", "details"):
        raw = out.get(col)
        if isinstance(raw, str):
            try:
                out[col] = json.loads(raw)
            except ValueError:
                out[col] = []
    return out


def build_mask(instruments: list) -> dict:
    """instrument -> CAND_A/CAND_B/... in sorted order (deterministic)."""
    aliases = {}
    for i, inst in enumerate(sorted(set(instruments))):
        # 26+ candidates never happens (Stage 2 caps at 10), but be total:
        aliases[inst] = "CAND_" + chr(ord("A") + i % 26) + (
            str(i // 26) if i >= 26 else "")
    return aliases


def masked_view(input_row: dict, alias: str, now_iso: str) -> dict:
    """The explicit field whitelist — everything else is excluded by
    construction, not by filtering."""
    view = {
        "alias": alias,
        "direction": input_row["direction"],
        "horizon_band": input_row["horizon_band"],
        "det_score": input_row["det_score"],
        "sector": input_row.get("sector"),
        "atr_pct": (round(input_row["atr"] / input_row["price"], 4)
                    if input_row.get("atr") and input_row.get("price")
                    else None),
        "signals": [{"signal": s.get("signal"),
                     "det_score": s.get("det_score")}
                    for s in input_row.get("signals") or []],
        "metrics": {k: v
                    for d in (input_row.get("details") or []) if isinstance(d, dict)
                    for k, v in d.items() if k in catalog.MASK_DETAIL_KEYS},
    }
    ned = input_row.get("next_earnings_date")
    if ned:
        days = (date.fromisoformat(ned[:10])
                - datetime.fromisoformat(now_iso).date()).days
        if days >= 0:
            view["days_to_earnings"] = days
    return view


def render_user_prompt(masked: dict) -> str:
    return ("Review this candidate and reply with exactly one JSON object "
            "per the grammar:\n" + catalog.canonical_json(masked))


def prompt_hash(system: str, user: str) -> str:
    return hashlib.sha256((system + "\n" + user).encode()).hexdigest()

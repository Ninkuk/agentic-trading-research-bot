import dataclasses
import hashlib
import json


@dataclasses.dataclass(frozen=True)
class GateConfig:
    """Every promotion threshold, frozen. All numeric values are 🔵 defaults —
    calibrate via Stage 6 trials; every value tried gets a trial-registry
    entry. Changing one is a code change that shows in every audit row via
    config_hash."""
    price_floor: float = 5.0                # G3: sub-$5 names drop
    dollar_volume_floor: float = 10_000_000.0   # G3: avg daily $ volume
    strong_extreme: float = 0.95            # G4(b): single-signal promotion bar
    sector_cap: int = 2                     # G5: max candidates per sector/asset_class
    max_positions: int = 10                 # G6: hard cap by det_score
    risk_fraction: float = 0.01             # 1% of equity at risk per trade
    atr_mult: float = 2.0                   # stop_distance = atr * atr_mult
    participation_cap: float = 0.01         # shares <= 1% of averageVolume
    allow_short: bool = False               # G2: cash-account reality


DEFAULT_CONFIG = GateConfig()


def config_hash(cfg: GateConfig) -> str:
    """sha256 of the canonical JSON of the config — snapshot provenance and
    Stage 4's guardrail_config_version input."""
    canon = json.dumps(dataclasses.asdict(cfg), sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


# Data-point ids each liquidity DB must expose (stockanalysis metrics columns
# are dynamic — fail with a clear list, not `no such column`).
REQUIRED_STOCK_POINTS = ("price", "averageVolume", "dollarVolume", "atr",
                         "sector", "nextEarningsDate")
REQUIRED_ETF_POINTS = ("price", "averageVolume", "dollarVolume", "atr")

# Longest horizon wins when signals with different bands group (G1).
HORIZON_ORDER = {"weeks": 0, "months": 1}

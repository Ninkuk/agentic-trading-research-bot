"""Monte-Carlo permutation test (MCPT) for the replay's significance flags.

v_replay_efficacy's Wilson interval treats overlapping forward windows as
independent, and its ~60 graded cells carry nominal, uncorrected 95%
flags (the neutral rows are reported but never flagged). This
pass prices both defects in one null: the FLAGS are held fixed and each
benchmark spine's daily log returns are shuffled whole-series — the return
multiset (hence total drift, the v_benchmark_baseline null) is preserved —
then every cell's hit rate is recomputed under the shuffled spine exactly
as the view computes it: same first-as-of observation dedupe, same
maturity cutoff, so each permutation carries the same overlap structure
and the SAME n as the real data.

The per-cell statistic is EXCESS — the cell's hit rate minus that same
dataset's own drift baseline (the view's `excess` on the real side; hit
rate minus that permutation's own p_up/p_down on the permuted side) —
NOT the raw hit rate. Measured live,
raw hit rates lit broad-coverage cells up at p = 0.001 on +0.3pp excess:
a cell flagging half of all days inherits its hit rate from the spine,
and the real market's ORDERING (clustered runs the shuffle destroys)
beats a shuffled ordering — arrangement, not window selection. Excess
cancels each dataset's own drift and arrangement level, isolating what
the flag actually chose.

p = (1 + #{permutations with perm excess >= real excess}) / (1 + n_perms)
— the inclusive convention: the real sample counts as its own permutation
and p can never be 0. `hit` is direction-adjusted in the view (a bearish
hit is the benchmark FALLING), so >= is the favorable tail for every cell
— no per-direction inequality flip is needed. Read p near 1 as "no better
than any shuffle, ties included" — NOT by itself as evidence of
anti-prediction: the statistic is discrete and the inclusive >= puts
exact ties in the favorable tail, so a zero-skill broad-coverage cell
reads p = 1.0 without being anti-predictive (1 − p is not a left-tail p).

One family row (FAMILY_KEY) prices multiplicity by the max-statistic: per
permutation T = max over graded cells of (perm hit rate - that
permutation's own drift baseline), compared against the real max excess.
It answers "is the best cell better than the best cell of a skill-free
scoreboard" with one corrected p. The statistic is UN-studentized: cell n
spans ~53-1,357 live, so the null max is dominated by the small-n cells'
high-variance excess and the family p has real power only against
small-n-sized effects — exact under the global null (cannot
false-positive), but a modest large-n effect can essentially never beat
it. Read a large family p as "the max is unremarkable", never as "no
cell survives correction". Westfall-Young studentization is the recorded
follow-up alongside the block-shuffle variant below.

Caveat: a whole-series shuffle destroys
autocorrelation and volatility clustering, so cells whose flags key on
vol regimes (cboe_vix, cboe_vix_backwardation) get an optimistically
biased null — failing even this null is death; passing it is a lead, not
a result. A block-shuffle robustness variant is the recorded follow-up.

Determinism: random.Random(seed) with the seed injected through run(...);
no wall-clock, no network, stdlib only.
"""

import math
import random
from itertools import accumulate

# The one corrected-for-multiplicity row in replay_null. '*' can never
# collide with a signal_id, so the efficacy view's LEFT JOIN skips it.
FAMILY_KEY = ("*", "*", 0)


def harvest(conn):
    """The permutation's fixed inputs, read once.

    Returns (spines, groups, real):
      spines: benchmark -> list of closes in rn order (v_spine).
      groups: [(signal_id, benchmark, direction, [asof rn, ...])] — one rn
        per OBSERVATION (first as-of date per source_date, the view's
        dedupe; the bare `score` rides SQLite's MIN-row guarantee exactly
        like the view's bare columns do). Neutral groups are dropped.
      real: (signal_id, direction, horizon) -> (hit_rate, excess, n_bench)
        from v_replay_efficacy — the pass never recomputes the real
        statistic, it compares against the view's own numbers.
    """
    spines: dict[str, list[float]] = {}
    rn_of: dict[tuple[str, str], int] = {}
    for benchmark, date, close, rn in conn.execute(
        "SELECT benchmark, date, close, rn FROM v_spine ORDER BY benchmark, rn"
    ):
        spines.setdefault(benchmark, []).append(close)
        rn_of[(benchmark, date)] = rn
    grouped: dict[tuple[str, str, str], list[int]] = {}
    for signal_id, benchmark, first_asof, direction in conn.execute(
        "SELECT signal_id, benchmark, MIN(asof_date),"
        "       CASE WHEN score < 0 THEN 'bearish'"
        "            WHEN score > 0 THEN 'bullish' ELSE 'neutral' END"
        " FROM v_replay_flags GROUP BY signal_id, benchmark, source_date"
    ):
        if direction == "neutral":
            continue
        grouped.setdefault((signal_id, benchmark, direction), []).append(
            rn_of[(benchmark, first_asof)]
        )
    groups = [(s, b, d, sorted(rns)) for (s, b, d), rns in sorted(grouped.items())]
    real = {
        (r[0], r[1], r[2]): (r[3], r[4], r[5])
        for r in conn.execute(
            "SELECT signal_id, direction, horizon, hit_rate, excess, n_bench"
            " FROM v_replay_efficacy WHERE direction != 'neutral' AND n_bench > 0"
        )
    }
    return spines, groups, real


def permutation_null(conn, n_perms: int, seed: int) -> list[tuple]:
    """Run the pass; returns replay_null rows
    (signal_id, direction, horizon, n_perms, p_value), family row included.
    Empty when nothing is graded. Raises if the replicated population ever
    disagrees with the view's n_bench — a p for a different statistic must
    never be published silently."""
    from sources.combiners.backtest import catalog

    if n_perms < 1:
        # 0 would "compute" p = 1.0 everywhere without permuting anything;
        # negatives divided by zero or wrote p = -1.0 rows. run.py skips
        # the pass on 0; anything else non-positive is a caller error.
        raise ValueError(f"n_perms must be >= 1, got {n_perms}")

    spines, groups, real = harvest(conn)
    logret = {b: [math.log(c[i] / c[i - 1]) for i in range(1, len(c))] for b, c in spines.items()}
    # Cell = (key, benchmark, bullish?, matured obs rns). Window for as-of
    # rn a: entry rn a+1, exit rn a+1+h; with P = prefix sums of the log
    # returns (P[0] = 0), the window's log return is P[a+h] - P[a], matured
    # iff a <= N-1-h — index arithmetic identical to v_replay_returns.
    cells = []
    for signal_id, benchmark, direction, rns in groups:
        n = len(spines[benchmark])
        for h in catalog.HORIZONS:
            key = (signal_id, direction, h)
            if key not in real:
                continue
            obs = [a for a in rns if a <= n - 1 - h]
            if len(obs) != real[key][2]:
                raise RuntimeError(
                    f"mcpt population drifted from v_replay_efficacy for {key}:"
                    f" {len(obs)} obs vs n_bench {real[key][2]}"
                )
            cells.append((key, benchmark, direction == "bullish", obs))
    cells = [c for c in cells if c[3]]
    if not cells:
        return []

    horizons = sorted({key[2] for key, _, _, _ in cells})
    t_real = max(real[key][1] for key, _, _, _ in cells)
    exceed = dict.fromkeys((key for key, _, _, _ in cells), 0)
    family_exceed = 0
    rng = random.Random(seed)
    for _ in range(n_perms):
        prefix: dict[str, list[float]] = {}
        base: dict[tuple[str, int], tuple[float, float]] = {}
        for b, returns in logret.items():
            rng.shuffle(returns)
            p = [0.0, *accumulate(returns)]
            prefix[b] = p
            n = len(p)
            for h in horizons:
                up = down = 0
                for a in range(1, n - h):
                    d = p[a + h] - p[a]
                    if d > 0:
                        up += 1
                    elif d < 0:
                        down += 1
                windows = n - 1 - h
                base[(b, h)] = (up / windows, down / windows) if windows > 0 else (0.0, 0.0)
        t_perm = None
        for key, benchmark, bullish, obs in cells:
            p = prefix[benchmark]
            h = key[2]
            if bullish:
                hits = sum(1 for a in obs if p[a + h] - p[a] > 0)
            else:
                hits = sum(1 for a in obs if p[a + h] - p[a] < 0)
            excess = hits / len(obs) - base[(benchmark, h)][0 if bullish else 1]
            if excess >= real[key][1]:
                exceed[key] += 1
            if t_perm is None or excess > t_perm:
                t_perm = excess
        if t_perm is not None and t_perm >= t_real:
            family_exceed += 1

    rows = [
        (key[0], key[1], key[2], n_perms, (1 + count) / (1 + n_perms))
        for key, count in sorted(exceed.items())
    ]
    rows.append((*FAMILY_KEY, n_perms, (1 + family_exceed) / (1 + n_perms)))
    return rows

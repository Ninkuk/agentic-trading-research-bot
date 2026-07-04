"""Pure math for the trial harness — no I/O of any kind (the stats layer
replaces fetch.py in the four-file shape). Deflated Sharpe Ratio per Bailey &
Lopez de Prado, computed with stdlib only.

Kurtosis convention: RAW (Pearson) fourth standardized moment, normal = 3 —
the published PSR/DSR denominator assumes it; an excess-kurtosis (normal = 0)
slip flips the term's sign at normality and corrupts every DSR."""
import math
from statistics import NormalDist

EULER_GAMMA = 0.5772156649


def mean(xs):
    return sum(xs) / len(xs)


def sample_stdev(xs):
    n = len(xs)
    if n < 2:
        return None
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def sharpe(xs):
    """Un-annualized mean/sample-stdev of the per-lead return series
    (heterogeneous horizons make annualization dishonest). None if
    uncomputable."""
    sd = sample_stdev(xs)
    if not sd:
        return None
    return mean(xs) / sd


def _central_moments(xs):
    n = len(xs)
    m = mean(xs)
    m2 = sum((x - m) ** 2 for x in xs) / n
    m3 = sum((x - m) ** 3 for x in xs) / n
    m4 = sum((x - m) ** 4 for x in xs) / n
    return m2, m3, m4


def skewness(xs):
    """Population skew m3/m2^1.5. None for degenerate series."""
    if len(xs) < 2:
        return None
    m2, m3, _m4 = _central_moments(xs)
    if m2 == 0:
        return None
    return m3 / m2 ** 1.5


def kurtosis_raw(xs):
    """Population RAW kurtosis m4/m2^2 (normal = 3, NOT excess)."""
    if len(xs) < 2:
        return None
    m2, _m3, m4 = _central_moments(xs)
    if m2 == 0:
        return None
    return m4 / m2 ** 2


def max_drawdown(xs):
    """Max peak-to-trough fraction of the compounded equity curve."""
    eq = peak = 1.0
    mdd = 0.0
    for r in xs:
        eq *= 1.0 + r
        peak = max(peak, eq)
        mdd = max(mdd, (peak - eq) / peak)
    return mdd


def expected_max_sharpe(n_trials, sd_sr):
    """SR0 — the expected max SR of n_trials random trials (B&LdP):
    SR0 = sd_SR * ((1-gamma)*Phi^-1(1 - 1/N) + gamma*Phi^-1(1 - 1/(N*e))).
    None when N < 2 or sd_SR is 0/None (never a fake baseline)."""
    if n_trials < 2 or not sd_sr:
        return None
    nd = NormalDist()
    return sd_sr * ((1 - EULER_GAMMA) * nd.inv_cdf(1 - 1 / n_trials)
                    + EULER_GAMMA * nd.inv_cdf(1 - 1 / (n_trials * math.e)))


def deflated_sharpe(sr, n_obs, skew, kurt, n_trials, sd_sr):
    """DSR = Phi((SR - SR0) * sqrt(T-1) / sqrt(1 - skew*SR + ((kurt-1)/4)*SR^2)).
    kurt is RAW (normal = 3). Any uncomputable input -> None, never 1.0."""
    sr0 = expected_max_sharpe(n_trials, sd_sr)
    if sr0 is None or sr is None or skew is None or kurt is None or n_obs < 2:
        return None
    denom_sq = 1 - skew * sr + ((kurt - 1) / 4) * sr * sr
    if denom_sq <= 0:
        return None
    return NormalDist().cdf((sr - sr0) * math.sqrt(n_obs - 1)
                            / math.sqrt(denom_sq))

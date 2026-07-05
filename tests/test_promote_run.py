import json

import pytest

from pipeline.promote import db as pdb
from pipeline.promote import run as prun
from pipeline.leads import db as leads_db
from sources.screeners.stock_analysis_screener import db as stocks_db_mod

NOW = "2026-07-04T21:00:00+00:00"
COLS = {"price": "REAL", "averageVolume": "REAL", "dollarVolume": "REAL",
        "atr": "REAL", "sector": "TEXT", "nextEarningsDate": "TEXT"}


def _lead(**over):
    lead = {"instrument": "GLD", "instrument_kind": "etf",
            "signal": "cot_commercial_extreme", "direction": "long",
            "signal_type": "mean_reversion", "implementation": "cross_sectional",
            "horizon_band": "weeks", "score": 96.0, "rank_pct": None,
            "as_of_date": "2026-06-30",
            "details": '{"asset_class":"metals"}'}
    lead.update(over)
    return lead


def _make_leads(path, rows, scalar=1.0):
    conn = leads_db.connect(path)
    leads_db.ensure_schema(conn)
    sid = leads_db.write_snapshot(conn, NOW)
    leads_db.write_leads(conn, sid, rows)
    leads_db.write_regime(conn, sid, {
        "as_of_date": "2026-06-01", "cpi_yoy": 2.0, "unrate": 5.0,
        "yield_curve_inverted": 0, "hy_spread": 3.0, "late_cycle": 0,
        "exposure_scalar": scalar, "regime_incomplete": 0})
    conn.close()


def _make_prices(path, quotes):
    conn = stocks_db_mod.connect(path)
    stocks_db_mod.ensure_schema(conn, COLS)
    stocks_db_mod.write_snapshot(conn, NOW, "test", quotes, list(COLS))
    conn.close()


def _world(tmp_path):
    paths = {"cand": str(tmp_path / "candidates.db"),
             "leads": str(tmp_path / "leads.db"),
             "stocks": str(tmp_path / "stocks.db"),
             "etfs": str(tmp_path / "etfs.db")}
    _make_leads(paths["leads"], [
        _lead(),                                             # promotable ETF
        _lead(instrument="SOYB", score=97.0,
              details='{"asset_class":"ags"}'),              # under $ floor
        _lead(instrument="WIN", instrument_kind="stock",
              signal="quality_composite", signal_type="quality",
              horizon_band="months", score=2.0, rank_pct=0.97,
              details="{}"),                                 # promotable stock
        _lead(instrument="MID", instrument_kind="stock",
              signal="quality_composite", signal_type="quality",
              horizon_band="months", score=1.0, rank_pct=0.80,
              details="{}"),                                 # fails confluence
    ])
    _make_prices(paths["etfs"], {
        "GLD": {"price": 200.0, "averageVolume": 5e6, "dollarVolume": 1e9,
                "atr": 4.0, "sector": None, "nextEarningsDate": None},
        "SOYB": {"price": 22.0, "averageVolume": 6e4, "dollarVolume": 1.1e6,
                 "atr": 0.3, "sector": None, "nextEarningsDate": None}})
    _make_prices(paths["stocks"], {
        "WIN": {"price": 50.0, "averageVolume": 2e6, "dollarVolume": 8e7,
                "atr": 2.0, "sector": "Technology",
                "nextEarningsDate": "2026-08-01"},
        "MID": {"price": 40.0, "averageVolume": 2e6, "dollarVolume": 6e7,
                "atr": 1.5, "sector": "Technology",
                "nextEarningsDate": None}})
    return paths


def test_run_end_to_end_promotes_and_logs_kills(tmp_path):
    paths = _world(tmp_path)
    sid, n_cand, n_rej = prun.run(paths["cand"], leads_db=paths["leads"],
                                  stocks_db=paths["stocks"],
                                  etfs_db=paths["etfs"],
                                  equity=100_000.0, now_iso=NOW)
    assert n_cand == 2 and n_rej == 2
    conn = pdb.connect(paths["cand"])
    cands = {r[0]: r for r in conn.execute(
        "SELECT instrument, shares, stop_price, sector, next_earnings_date "
        "FROM v_latest_candidates")}
    assert set(cands) == {"GLD", "WIN"}
    # GLD: risk 1000, stop_distance 8 -> floor(125) shares; ADV cap 50k -> 125
    assert cands["GLD"][1] == 125 and cands["GLD"][2] == pytest.approx(192.0)
    assert cands["GLD"][3] == "metals"                 # asset_class as sector
    assert cands["WIN"][4] == "2026-08-01"             # earnings date carried
    rejects = dict(conn.execute(
        "SELECT instrument, gate FROM rejections WHERE snapshot_id=?",
        (sid,)).fetchall())
    assert rejects == {"SOYB": "liquidity", "MID": "confluence"}
    header = conn.execute(
        "SELECT equity, regime_scalar, config_hash FROM snapshots WHERE id=?",
        (sid,)).fetchone()
    assert header[0] == 100_000.0 and header[1] == 1.0 and len(header[2]) == 64
    conn.close()


def test_run_regime_scalar_flows_into_sizing(tmp_path):
    paths = _world(tmp_path)
    _make_leads(paths["leads"], [_lead()], scalar=0.5)
    prun.run(paths["cand"], leads_db=paths["leads"],
             stocks_db=paths["stocks"], etfs_db=paths["etfs"],
             equity=100_000.0, now_iso=NOW)
    conn = pdb.connect(paths["cand"])
    row = conn.execute("SELECT risk_dollars, shares "
                       "FROM v_latest_candidates").fetchone()
    assert row[0] == pytest.approx(500.0)              # halved by the dial
    assert row[1] == 62                                # floor(500/8)
    conn.close()


def test_run_equity_env_fallback_and_hard_error(tmp_path, monkeypatch):
    paths = _world(tmp_path)
    monkeypatch.setenv("PIPELINE_EQUITY", "50000")
    sid, n, _ = prun.run(paths["cand"], leads_db=paths["leads"],
                         stocks_db=paths["stocks"], etfs_db=paths["etfs"],
                         now_iso=NOW)
    conn = pdb.connect(paths["cand"])
    assert conn.execute("SELECT equity FROM snapshots WHERE id=?",
                        (sid,)).fetchone()[0] == 50000.0
    conn.close()
    monkeypatch.delenv("PIPELINE_EQUITY")
    with pytest.raises(ValueError):
        prun.run(str(tmp_path / "c2.db"), leads_db=paths["leads"],
                 stocks_db=paths["stocks"], etfs_db=paths["etfs"], now_iso=NOW)
    import os.path
    assert not os.path.exists(str(tmp_path / "c2.db"))   # error BEFORE any write


def test_run_missing_price_db_logs_data_missing(tmp_path, capsys):
    paths = _world(tmp_path)
    sid, n_cand, _ = prun.run(paths["cand"], leads_db=paths["leads"],
                              stocks_db=str(tmp_path / "absent.db"),
                              etfs_db=paths["etfs"],
                              equity=100_000.0, now_iso=NOW)
    err = capsys.readouterr().err
    assert "OperationalError" in err and "absent.db" not in err
    conn = pdb.connect(paths["cand"])
    gates_hit = {r[0] for r in conn.execute(
        "SELECT gate FROM rejections WHERE snapshot_id=? AND instrument='WIN'",
        (sid,))}
    assert gates_hit == {"data_missing"}
    conn.close()


def test_run_missing_leads_db_is_hard_error(tmp_path):
    with pytest.raises(ValueError):
        prun.run(str(tmp_path / "c.db"), leads_db=str(tmp_path / "no.db"),
                 stocks_db=str(tmp_path / "s.db"),
                 etfs_db=str(tmp_path / "e.db"),
                 equity=1000.0, now_iso=NOW)


def test_main_cli_smoke(tmp_path, capsys):
    paths = _world(tmp_path)
    prun.main(["--db", paths["cand"], "--leads-db", paths["leads"],
               "--stocks-db", paths["stocks"], "--etfs-db", paths["etfs"],
               "--equity", "100000"])
    out = capsys.readouterr().out
    assert "candidates" in out


# --- fractional sizing + cohort notional (DEFENSES_ROADMAP) ---

def test_run_fractional_small_account_promotes_fractional_shares(tmp_path):
    # the 2026-07-05 first-live-run scenario: $200.37, risk-off -> whole
    # shares all die size_zero; fractional=True must produce a real book
    paths = _world(tmp_path)
    _make_leads(paths["leads"], [_lead()], scalar=0.5)
    sid, n_cand, _ = prun.run(paths["cand"], leads_db=paths["leads"],
                              stocks_db=paths["stocks"],
                              etfs_db=paths["etfs"], equity=200.37,
                              fractional=True, now_iso=NOW)
    assert n_cand == 1
    conn = pdb.connect(paths["cand"])
    shares, frac = conn.execute(
        "SELECT c.shares, s.fractional FROM candidates c "
        "JOIN snapshots s ON s.id=c.snapshot_id WHERE s.id=?",
        (sid,)).fetchone()
    assert 0 < shares < 1 and frac == 1
    conn.close()


def test_run_fractional_env_fallback(tmp_path, monkeypatch):
    paths = _world(tmp_path)
    _make_leads(paths["leads"], [_lead()], scalar=0.5)
    monkeypatch.setenv("PIPELINE_FRACTIONAL", "1")
    sid, n_cand, _ = prun.run(paths["cand"], leads_db=paths["leads"],
                              stocks_db=paths["stocks"],
                              etfs_db=paths["etfs"], equity=200.37,
                              now_iso=NOW)
    assert n_cand == 1
    conn = pdb.connect(paths["cand"])
    assert conn.execute("SELECT fractional FROM snapshots WHERE id=?",
                        (sid,)).fetchone()[0] == 1
    conn.close()


def test_run_whole_share_small_account_still_dies_size_zero(tmp_path):
    paths = _world(tmp_path)
    _make_leads(paths["leads"], [_lead()], scalar=0.5)
    sid, n_cand, n_rej = prun.run(paths["cand"], leads_db=paths["leads"],
                                  stocks_db=paths["stocks"],
                                  etfs_db=paths["etfs"], equity=200.37,
                                  now_iso=NOW)
    assert n_cand == 0 and n_rej == 1


def test_run_cohort_notional_cut_logged(tmp_path):
    # two fractional candidates each near the equity ceiling: the cohort
    # gate must cut the lower-scored one and log gate='notional'
    paths = _world(tmp_path)
    _make_leads(paths["leads"], [
        _lead(),                                             # GLD det 0.96
        _lead(instrument="SLV", score=95.5,
              details='{"asset_class":"metals2"}')])
    _make_prices(paths["etfs"], {
        "GLD": {"price": 200.0, "averageVolume": 5e6, "dollarVolume": 1e9,
                "atr": 0.05, "sector": None, "nextEarningsDate": None},
        "SLV": {"price": 200.0, "averageVolume": 5e6, "dollarVolume": 1e9,
                "atr": 0.05, "sector": None, "nextEarningsDate": None}})
    # tiny atr -> huge risk-driven size -> each clamps to ~equity notional
    sid, n_cand, _ = prun.run(paths["cand"], leads_db=paths["leads"],
                              stocks_db=paths["stocks"],
                              etfs_db=paths["etfs"], equity=1000.0,
                              fractional=True, now_iso=NOW)
    assert n_cand == 1
    conn = pdb.connect(paths["cand"])
    rejects = dict(conn.execute(
        "SELECT instrument, gate FROM rejections WHERE snapshot_id=?",
        (sid,)).fetchall())
    assert rejects.get("SLV") == "notional"
    conn.close()

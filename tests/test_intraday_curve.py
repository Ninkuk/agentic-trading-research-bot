"""tools/book/intraday_curve: positions × 5-minute bars → $100-rebased book vs SPY."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.book import intraday_curve as ic

DATE = "2026-10-22"


def _bar(t: str, close: float, interpolated: bool = False) -> dict[str, object]:
    b: dict[str, object] = {"begins_at": t, "close_price": f"{close:.6f}", "session": "reg"}
    if interpolated:
        b["interpolated"] = True
    return b


def _historicals(sym: str, interval: str, bars: list[dict[str, object]]) -> dict[str, object]:
    return {"data": {"results": [{"symbol": sym, "interval": interval, "bars": bars}]}}


def _positions(**qty: float) -> dict[str, object]:
    return {
        "data": {
            "positions": [{"symbol": s, "quantity": str(q), "type": "long"} for s, q in qty.items()]
        }
    }


TIMES = ic.session_times(DATE, 3)


@pytest.fixture
def world() -> tuple[dict[str, float], dict[str, dict[str, float]], dict[str, float]]:
    positions = ic.load_positions(_positions(AAA=2.0, BBB=1.0))
    intraday, daily = ic.load_historicals(
        [
            _historicals(
                "AAA", "5minute", [_bar(TIMES[0], 11.0), _bar(TIMES[1], 12.0), _bar(TIMES[2], 12.0)]
            ),
            # BBB prints late and has one gap-filled bar: it must carry the prior close, then its last real print.
            _historicals(
                "BBB", "5minute", [_bar(TIMES[1], 20.0), _bar(TIMES[2], 20.0, interpolated=True)]
            ),
            _historicals(
                "SPY",
                "5minute",
                [_bar(TIMES[0], 101.0), _bar(TIMES[1], 99.0), _bar(TIMES[2], 100.0)],
            ),
            _historicals(
                "AAA",
                "day",
                [_bar("2026-10-21T00:00:00Z", 10.0), _bar("2026-10-20T00:00:00Z", 9.0)],
            ),
            _historicals("BBB", "day", [_bar("2026-10-21T00:00:00Z", 20.0)]),
            _historicals(
                "SPY",
                "day",
                [_bar("2026-10-21T00:00:00Z", 100.0), _bar(DATE + "T00:00:00Z", 999.0)],
            ),
        ]
    )
    return positions, intraday, ic.prior_closes(daily, DATE)


def test_prior_close_is_last_daily_bar_strictly_before_date(world):
    _, _, prev = world
    assert prev == {"AAA": 10.0, "BBB": 20.0, "SPY": 100.0}  # today's partial day bar is ignored


def test_interpolated_bars_are_dropped(world):
    _, intraday, _ = world
    assert TIMES[2] not in intraday["BBB"]


def test_rebases_book_and_benchmark_to_100_at_prior_close(world):
    positions, intraday, prev = world
    c = ic.build_curve(DATE, positions, intraday, prev, session_bars=3)
    pts = c["points"]
    assert pts[0] == {"t": "06:30", "label": "Prev close", "book": 100.0, "spy": 100.0}
    # bar 1: AAA 11 (2 sh) + BBB carried at prior close 20 → 42 / 40
    assert pts[1]["book"] == pytest.approx(105.0)
    assert pts[1]["spy"] == pytest.approx(101.0)
    assert pts[1]["label"] == "6:35 AM"  # bar END, Phoenix clock
    # bar 3: BBB's interpolated bar is ignored, last real print (20) carries
    assert pts[3]["book"] == pytest.approx(110.0)
    assert c["partial"] is False and c["bars_done"] == 3 and c["thin"] == ["BBB"]
    assert c["base_book"] == 40.0 and c["close_book"] == 44.0


def test_partial_session_reports_bars_done(world):
    positions, intraday, prev = world
    c = ic.build_curve(DATE, positions, intraday, prev, session_bars=78)
    assert c["partial"] is True and c["bars_done"] == 3 and len(c["points"]) == 4


def test_holdings_sorted_by_contribution(world):
    positions, intraday, prev = world
    c = ic.build_curve(DATE, positions, intraday, prev, session_bars=3)
    assert [h["symbol"] for h in c["holdings"]] == ["AAA", "BBB"]
    aaa = c["holdings"][0]
    assert (
        aaa["weight"] == 0.5
        and aaa["ret"] == pytest.approx(0.2)
        and aaa["contrib"] == pytest.approx(0.1)
    )


@pytest.mark.parametrize("drop", ["AAA", "SPY"])
def test_refuses_missing_symbol(world, drop):
    positions, intraday, prev = world
    with pytest.raises(ValueError, match=drop):
        ic.build_curve(DATE, positions, {k: v for k, v in intraday.items() if k != drop}, prev, 3)
    with pytest.raises(ValueError, match=drop):
        ic.build_curve(DATE, positions, intraday, {k: v for k, v in prev.items() if k != drop}, 3)


def test_render_inlines_data_and_escapes_script_close():
    html = ic.render_page(
        {"points": [], "note": "</script>"}, template="<script>const DATA = __DATA__;</script>"
    )
    assert "__DATA__" not in html and "<\\/script>" in html and "</script>" in html[-10:]


def test_cli_writes_curve_and_page(tmp_path: Path, world):
    positions = _positions(AAA=2.0, BBB=1.0)
    files = {
        "pos.json": positions,
        "a.json": _historicals("AAA", "5minute", [_bar(TIMES[0], 11.0)]),
        "b.json": _historicals("BBB", "5minute", [_bar(TIMES[0], 20.0)]),
        "s.json": _historicals("SPY", "5minute", [_bar(TIMES[0], 101.0)]),
        "d.json": {
            "data": {
                "results": [
                    {"symbol": s, "interval": "day", "bars": [_bar("2026-10-21T00:00:00Z", p)]}
                    for s, p in [("AAA", 10.0), ("BBB", 20.0), ("SPY", 100.0)]
                ]
            }
        },
    }
    for name, doc in files.items():
        (tmp_path / name).write_text(json.dumps(doc))
    out, html = tmp_path / "curve.json", tmp_path / "page.html"
    rc = ic.main(
        [
            "--date",
            DATE,
            "--positions",
            str(tmp_path / "pos.json"),
            "--out",
            str(out),
            "--html",
            str(html),
            *(str(tmp_path / n) for n in ["a.json", "b.json", "s.json", "d.json"]),
        ]
    )
    assert rc == 0
    curve = json.loads(out.read_text())
    assert curve["partial"] is True and curve["bars_done"] == 1
    assert html.read_text().startswith("<title>") and '"bars_done": 1' in html.read_text()


def test_cli_refuses_when_benchmark_missing(tmp_path: Path):
    (tmp_path / "pos.json").write_text(json.dumps(_positions(AAA=1.0)))
    (tmp_path / "a.json").write_text(
        json.dumps(_historicals("AAA", "5minute", [_bar(TIMES[0], 1.0)]))
    )
    rc = ic.main(
        [
            "--date",
            DATE,
            "--positions",
            str(tmp_path / "pos.json"),
            "--out",
            str(tmp_path / "c.json"),
            str(tmp_path / "a.json"),
        ]
    )
    assert rc == 2

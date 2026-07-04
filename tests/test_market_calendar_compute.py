from datetime import date

from sources.monitors.market_calendar import compute


def test_third_friday_known_values():
    assert compute.third_friday(2026, 1) == date(2026, 1, 16)
    assert compute.third_friday(2026, 6) == date(2026, 6, 19)
    assert compute.third_friday(2026, 8) == date(2026, 8, 21)


def test_opex_dates_tags_quad_witching_months():
    got = dict(compute.opex_dates(2026, set()))
    assert got["2026-03-20"] == "quad_witching"   # March -> quad
    assert got["2026-06-19"] == "quad_witching"   # June -> quad
    assert got["2026-09-18"] == "quad_witching"
    assert got["2026-12-18"] == "quad_witching"
    assert got["2026-08-21"] == "opex"            # August -> monthly


def test_opex_dates_has_twelve_entries():
    assert len(compute.opex_dates(2026, set())) == 12


def test_opex_shifts_to_thursday_when_third_friday_is_a_holiday():
    # Synthetic: pretend Aug 21 2026 (a 3rd Friday) is a market holiday.
    got = dict(compute.opex_dates(2026, {"2026-08-21"}))
    assert "2026-08-21" not in got
    assert got["2026-08-20"] == "opex"            # shifted to preceding Thursday

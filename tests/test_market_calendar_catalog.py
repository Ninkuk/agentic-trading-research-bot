from datetime import date

from sources.monitors.market_calendar import catalog


def _all_dated():
    return (
        list(catalog.EQUITY_HOLIDAYS)
        + list(catalog.EQUITY_EARLY_CLOSES)
        + list(catalog.BOND_HOLIDAYS)
        + list(catalog.BOND_EARLY_CLOSES)
    )


def test_every_seed_date_is_a_weekday():
    # A U.S. market holiday/early-close never lands on a weekend (it is observed
    # on the nearest weekday). This catches transcription typos loudly.
    for d in _all_dated():
        assert date.fromisoformat(d).weekday() < 5, f"{d} is a weekend"


def test_equity_early_close_times_are_1300():
    assert set(catalog.EQUITY_EARLY_CLOSES.values()) == {"13:00"}


def test_bond_early_close_times_are_1400():
    assert set(catalog.BOND_EARLY_CLOSES.values()) == {"14:00"}


def test_2026_core_equity_holidays_present():
    for d in ("2026-01-01", "2026-05-25", "2026-07-03", "2026-11-26", "2026-12-25"):
        assert d in catalog.EQUITY_HOLIDAYS


def test_bond_adds_columbus_and_veterans_not_in_equities():
    # SIFMA divergence: bonds observe Columbus Day + Veterans Day; equities do not.
    assert "2026-10-12" in catalog.BOND_HOLIDAYS  # Columbus Day
    assert "2026-11-11" in catalog.BOND_HOLIDAYS  # Veterans Day
    assert "2026-10-12" not in catalog.EQUITY_HOLIDAYS
    assert "2026-11-11" not in catalog.EQUITY_HOLIDAYS


def test_holiday_dates_unions_equity_and_bond_full_closures():
    hs = catalog.holiday_dates()
    assert "2026-01-01" in hs  # equity + bond
    assert "2026-10-12" in hs  # bond-only Columbus Day
    # early closes are NOT full-closure dates
    assert "2026-11-27" not in hs

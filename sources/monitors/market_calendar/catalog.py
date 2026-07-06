"""Seeded U.S. market calendar — the source of truth for this monitor.

Transcribed 2026-07-03 from nyse.com/markets/hours-calendars (equities) and
sifma.org/resources/guides-playbooks/holiday-schedule (bonds). Re-confirm against
those pages before extending the horizon; the invariant tests catch weekend typos.

Divergence: the bond market (SIFMA) additionally observes Columbus Day and
Veterans Day, and treats Good Friday as an early close rather than a full close."""

# --- Equities (NYSE / Nasdaq full closures) ---------------------------------
EQUITY_HOLIDAYS: dict[str, str] = {
    "2026-01-01": "New Year's Day",
    "2026-01-19": "Martin Luther King Jr. Day",
    "2026-02-16": "Washington's Birthday",
    "2026-04-03": "Good Friday",
    "2026-05-25": "Memorial Day",
    "2026-06-19": "Juneteenth National Independence Day",
    "2026-07-03": "Independence Day (observed)",
    "2026-09-07": "Labor Day",
    "2026-11-26": "Thanksgiving Day",
    "2026-12-25": "Christmas Day",
    "2027-01-01": "New Year's Day",
    "2027-01-18": "Martin Luther King Jr. Day",
    "2027-02-15": "Washington's Birthday",
    "2027-03-26": "Good Friday",
    "2027-05-31": "Memorial Day",
    "2027-06-18": "Juneteenth National Independence Day (observed)",
    "2027-07-05": "Independence Day (observed)",
    "2027-09-06": "Labor Day",
    "2027-11-25": "Thanksgiving Day",
    "2027-12-24": "Christmas Day (observed)",
}

# Half-days close 13:00 ET (options 13:15). Day after Thanksgiving; Christmas Eve
# when it is a weekday; July 3 when July 4 is a weekday (not the case in 2026/2027).
EQUITY_EARLY_CLOSES: dict[str, str] = {
    "2026-11-27": "13:00",
    "2026-12-24": "13:00",
    "2027-11-26": "13:00",
}

# --- Bonds (SIFMA recommended full closures) --------------------------------
# Equity federal holidays PLUS Columbus Day + Veterans Day; Good Friday is a bond
# EARLY close (below), not a full closure.
BOND_HOLIDAYS: dict[str, str] = {
    "2026-01-01": "New Year's Day",
    "2026-01-19": "Martin Luther King Jr. Day",
    "2026-02-16": "Washington's Birthday",
    "2026-05-25": "Memorial Day",
    "2026-06-19": "Juneteenth National Independence Day",
    "2026-07-03": "Independence Day (observed)",
    "2026-09-07": "Labor Day",
    "2026-10-12": "Columbus Day",
    "2026-11-11": "Veterans Day",
    "2026-11-26": "Thanksgiving Day",
    "2026-12-25": "Christmas Day",
    "2027-01-01": "New Year's Day",
    "2027-01-18": "Martin Luther King Jr. Day",
    "2027-02-15": "Washington's Birthday",
    "2027-05-31": "Memorial Day",
    "2027-06-18": "Juneteenth National Independence Day (observed)",
    "2027-07-05": "Independence Day (observed)",
    "2027-09-06": "Labor Day",
    "2027-10-11": "Columbus Day",
    "2027-11-11": "Veterans Day",
    "2027-11-25": "Thanksgiving Day",
    "2027-12-24": "Christmas Day (observed)",
}

# SIFMA recommended bond early closes, 14:00 ET (2026 set from the design spec).
BOND_EARLY_CLOSES: dict[str, str] = {
    "2026-04-03": "14:00",  # Good Friday
    "2026-05-22": "14:00",  # Friday before Memorial Day
    "2026-07-02": "14:00",  # Thursday before Independence Day (observed)
    "2026-11-27": "14:00",  # Day after Thanksgiving
    "2026-12-24": "14:00",  # Christmas Eve
    "2026-12-31": "14:00",  # New Year's Eve
}


def holiday_dates() -> set[str]:
    """Union of equity + bond FULL-closure dates. This is the holiday set the
    OPEX computation shifts against (a 3rd Friday on any market closure moves to
    the preceding Thursday). Early closes are excluded — the market is open."""
    return set(EQUITY_HOLIDAYS) | set(BOND_HOLIDAYS)

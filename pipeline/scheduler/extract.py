"""Read-only monitor readers + the ET clock. The scheduler must not use the
monitors' v_upcoming*/v_early_closes views: they filter on each DB's own
calendar_now.today, which only that monitor's run sets (stale if today's
maintenance hasn't run) and which a read-only connection cannot set. Query the
events tables directly, binding dates derived from the scheduler's now_iso."""
from datetime import datetime
from zoneinfo import ZoneInfo

from sources.monitors.market_calendar.db import is_trading_day  # noqa: F401 (re-export)

ET = ZoneInfo("America/New_York")


def et_parts(now_iso: str) -> tuple:
    """(YYYY-MM-DD, HH:MM, weekday 0=Mon) of the injected now in ET.
    zoneinfo handles DST — the same UTC hour is a different ET wall time in
    January vs July, which is exactly what release triggers need."""
    dt = datetime.fromisoformat(now_iso).astimezone(ET)
    return dt.date().isoformat(), dt.strftime("%H:%M"), dt.weekday()


def plus_minutes(hhmm: str, minutes: int) -> str:
    h, m = map(int, hhmm.split(":"))
    total = min(h * 60 + m + minutes, 23 * 60 + 59)  # release times never cross midnight
    return f"{total // 60:02d}:{total % 60:02d}"


def econ_released(conn, today: str, now_hhmm: str, lag_min: int,
                  default_time: str) -> list:
    """Econ-calendar events dated today whose release time + lag has passed.
    NULL event_time falls back to default_time (most US releases are 08:30 ET)."""
    rows = conn.execute(
        "SELECT event_type, event_date, event_time FROM events "
        "WHERE event_date = ?", (today,)).fetchall()
    return [(etype, edate) for etype, edate, etime in rows
            if now_hhmm >= plus_minutes(etime or default_time, lag_min)]


def earnings_count(conn, today: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM events WHERE event_type='earnings' "
        "AND event_date=?", (today,)).fetchone()[0]


def equity_early_close(conn, d: str) -> bool:
    """Equity early_close only — bond_early_close must NOT shift the gate."""
    return conn.execute(
        "SELECT 1 FROM events WHERE event_type='early_close' AND event_date=? "
        "LIMIT 1", (d,)).fetchone() is not None

"""Pure extraction against ATTACHed source DBs. No network anywhere in
this package — the combiner's external feed is the local data/ dir."""

from datetime import date

from sources.common.dbattach import attach_ro, detach  # noqa: F401  (re-exported)


def staleness_days(today: str, obs_date):
    try:
        return (date.fromisoformat(today) - date.fromisoformat(str(obs_date)[:10])).days
    except (TypeError, ValueError):
        return None


def extract(conn, signal: dict, today: str) -> list:
    """Run one catalog signal's SQL; normalize to write_signal_values rows.
    Rows with a NULL entity or score are dropped (a LEFT-JOIN-shaped miss,
    not an error)."""
    params = {"today": today} if ":today" in signal["sql"] else {}
    out = []
    for entity, raw_value, score, obs_date in conn.execute(signal["sql"], params):
        if entity is None or score is None:
            continue
        out.append(
            {
                "signal_id": signal["signal_id"],
                "grain": signal["grain"],
                "entity": str(entity),
                "raw_value": raw_value,
                "score": max(-2, min(2, int(score))),
                "obs_date": obs_date,
                "staleness_days": staleness_days(today, obs_date),
            }
        )
    return out

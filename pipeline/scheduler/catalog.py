from dataclasses import dataclass

# Idempotency / retry policy
MAX_ATTEMPTS = 3            # further attempts only via --retry job:key
STALE_RUNNING_HOURS = 2     # a running row older than this = crashed attempt
FIXPOINT_LIMIT = 3          # depth of the longest chain: cftc -> leads -> promote

# Trigger times — all ET (America/New_York), evaluated against injected now_iso
RELEASE_LAG_MIN = 15        # econ release fires event_time + lag
DEFAULT_EVENT_TIME = "08:30"  # econ event with NULL event_time (most releases)
DAILY_MAINTENANCE_ET = "07:00"
COT_POST_ET = "16:00"       # COT posts ~15:30 Friday; fire at 16:00
EARNINGS_EVAL_ET = "18:00"  # post-close earnings-driven refresh
PRE_CLOSE_ET = "15:30"
PRE_CLOSE_EARLY_ET = "12:30"  # equity early-close days (13:00 close)
PRE_OPEN_ET = "09:00"

MONITOR_DB_FILES = {"econ_calendar": "econ_calendar.db",
                    "earnings": "earnings.db",
                    "market_calendar": "market_calendar.db"}

# Where each dispatcher's own DB lives under --data-dir. Keyed by job.target,
# except "etfs" which is keyed by job.name (it shares target "stocks" with
# the stocks job but writes a different DB file).
DB_FILES = {"earnings": "earnings.db", "econ_calendar": "econ_calendar.db",
            "fomc": "fomc.db", "market_calendar": "market_calendar.db",
            "treasury": "treasury.db", "cftc": "cftc.db", "fred": "fred.db",
            "fundamentals": "sec_fundamentals.db", "stocks": "stocks.db",
            "leads": "leads.db", "promote": "candidates.db", "gate": "gate.db",
            "etfs": "etfs.db"}


@dataclass(frozen=True)
class Job:
    name: str          # unique job id in schedule.db
    target: str        # registry dispatcher name (skipped if not registered)
    kind: str          # daily | cftc_weekly | econ_release | earnings | chain | gate
    after: tuple = ()  # upstream job names (kind='chain')
    window: str = ""   # pre_close | pre_open (kind='gate')


# Execution order = catalog order (maintenance first, then data jobs, then chains,
# then gate windows). promote/gate targets don't exist yet — they stay listed and
# are skipped until registered (spec: "job targets that don't exist yet simply
# aren't registered").
JOBS: list[Job] = [
    Job("earnings", "earnings", "daily"),
    Job("econ_calendar", "econ_calendar", "daily"),
    Job("fomc", "fomc", "daily"),
    Job("market_calendar", "market_calendar", "daily"),
    Job("treasury", "treasury", "daily"),
    Job("etfs", "stocks", "daily"),
    Job("cftc", "cftc", "cftc_weekly"),
    Job("fred", "fred", "econ_release"),
    Job("fundamentals", "fundamentals", "earnings"),
    Job("stocks", "stocks", "earnings"),
    Job("leads", "leads", "chain", after=("cftc", "fred", "fundamentals", "stocks")),
    Job("promote", "promote", "chain", after=("leads",)),
    Job("gate_pre_close", "gate", "gate", window="pre_close"),
    Job("gate_pre_open", "gate", "gate", window="pre_open"),
]

JOB_BY_NAME: dict[str, Job] = {j.name: j for j in JOBS}


def argv_for(job: Job, data_dir: str) -> list[str]:
    """The argv handed to registry[job.target]. promote deliberately gets no
    --equity (relies on the PIPELINE_EQUITY env fallback, sourced from .env by
    the cron wrapper)."""
    def d(f):
        return f"{data_dir}/{f}"
    argv = ["--db", d(DB_FILES.get(job.name, DB_FILES[job.target]))]
    if job.target == "leads":
        argv += ["--cftc-db", d("cftc.db"), "--fred-db", d("fred.db"),
                 "--fundamentals-db", d("sec_fundamentals.db"),
                 "--stocks-db", d("stocks.db")]
    if job.target == "promote":
        argv += ["--leads-db", d("leads.db"), "--stocks-db", d("stocks.db"),
                 "--etfs-db", d("etfs.db")]
    if job.name == "etfs":
        argv += ["--type", "e"]
    if job.target == "gate":
        argv += ["--candidates-db", d("candidates.db")]
    if job.kind == "gate":
        argv += ["--window", job.window]
    return argv

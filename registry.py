import sys

from edgar_screener.run import main as edgar_main
from reddit_screener.run import main as reddit_main
from screener.run import main as stocks_main

REGISTRY = {
    "stocks": stocks_main,
    "reddit": reddit_main,
    "edgar": edgar_main,
}


def dispatch(argv=None):
    """Route `<name> [args...]` to a registered screener. `--list` prints names."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("--list", "-l", "list"):
        for name in REGISTRY:
            print(name)
        return
    name, rest = argv[0], argv[1:]
    if name not in REGISTRY:
        print(f"unknown screener: {name}; choose from {', '.join(REGISTRY)}",
              file=sys.stderr)
        raise SystemExit(2)
    REGISTRY[name](rest)

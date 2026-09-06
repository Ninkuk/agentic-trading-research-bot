"""Column descriptors: `hidden=True` marks a detail column the table keeps
behind a "more columns" toggle, so a wide source table opens readable
without dropping any field."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import data  # noqa: E402
from dashboard_lib.common import col  # noqa: E402


def test_col_hidden_is_opt_in_and_survives_export():
    assert "hidden" not in col("net", "Net")
    assert col("chg_long", "Change in longs", hidden=True)["hidden"] is True
    assert "hidden" not in data._track_col("n", "N")
    assert data._track_col("hit_ci_lo", "CI low", hidden=True)["hidden"] is True

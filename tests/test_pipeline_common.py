import sqlite3

import pytest

from pipeline.common import pipeline_common


def test_connect_ro_reads_existing_db(tmp_path):
    path = str(tmp_path / "src.db")
    rw = sqlite3.connect(path)
    rw.execute("CREATE TABLE t (x)")
    rw.execute("INSERT INTO t VALUES (42)")
    rw.commit()
    rw.close()
    ro = pipeline_common.connect_ro(path)
    assert ro.execute("SELECT x FROM t").fetchone() == (42,)
    ro.close()


def test_connect_ro_refuses_writes(tmp_path):
    path = str(tmp_path / "src.db")
    sqlite3.connect(path).close()
    ro = pipeline_common.connect_ro(path)
    with pytest.raises(sqlite3.OperationalError):
        ro.execute("CREATE TABLE t (x)")
    ro.close()


def test_connect_ro_missing_file_raises(tmp_path):
    with pytest.raises(sqlite3.OperationalError):
        pipeline_common.connect_ro(str(tmp_path / "nope.db"))


def test_normalize_ticker_maps_class_share_dot():
    assert pipeline_common.normalize_ticker("BRK.B") == "BRK-B"


def test_normalize_ticker_uppercases_and_strips():
    assert pipeline_common.normalize_ticker(" brk.b ") == "BRK-B"
    assert pipeline_common.normalize_ticker("AAPL") == "AAPL"

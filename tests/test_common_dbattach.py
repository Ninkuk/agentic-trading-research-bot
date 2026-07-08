import sqlite3

import pytest

from sources.common.dbattach import attach_ro, detach


def test_attach_ro_missing_file_raises_file_not_found():
    conn = sqlite3.connect(":memory:")
    with pytest.raises(FileNotFoundError):
        attach_ro(conn, "/no/such.db")


def test_attach_ro_and_detach_round_trip(tmp_path):
    src_path = tmp_path / "src.db"
    src_conn = sqlite3.connect(str(src_path))
    src_conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
    src_conn.execute("INSERT INTO items (name) VALUES ('widget')")
    src_conn.commit()
    src_conn.close()

    # mode=ro requires the reading connection to have been opened with uri=True.
    reader = sqlite3.connect(str(tmp_path / "reader.db"), uri=True)
    attach_ro(reader, str(src_path))

    rows = reader.execute("SELECT name FROM src.items").fetchall()
    assert rows == [("widget",)]

    detach(reader)
    with pytest.raises(sqlite3.OperationalError):
        reader.execute("SELECT name FROM src.items").fetchall()


def test_attach_ro_custom_alias(tmp_path):
    src_path = tmp_path / "src.db"
    src_conn = sqlite3.connect(str(src_path))
    src_conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
    src_conn.execute("INSERT INTO items (name) VALUES ('gizmo')")
    src_conn.commit()
    src_conn.close()

    reader = sqlite3.connect(str(tmp_path / "reader.db"), uri=True)
    attach_ro(reader, str(src_path), alias="foo")

    rows = reader.execute("SELECT name FROM foo.items").fetchall()
    assert rows == [("gizmo",)]

    detach(reader, alias="foo")

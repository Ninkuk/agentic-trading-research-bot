import pytest

import registry


def test_dispatch_lists_registered_screeners(capsys):
    registry.dispatch(["--list"])
    out = capsys.readouterr().out
    assert "stocks" in out
    assert "reddit" in out


def test_dispatch_routes_and_forwards_argv(monkeypatch):
    seen = {}
    monkeypatch.setitem(registry.REGISTRY, "reddit",
                        lambda argv: seen.setdefault("argv", argv))
    registry.dispatch(["reddit", "--db", "x.db"])
    assert seen["argv"] == ["--db", "x.db"]


def test_dispatch_unknown_name_exits_nonzero(capsys):
    with pytest.raises(SystemExit) as exc:
        registry.dispatch(["nope"])
    assert exc.value.code != 0
    assert "nope" in capsys.readouterr().err


def test_registry_has_both_screeners():
    assert set(registry.REGISTRY) >= {"stocks", "reddit"}

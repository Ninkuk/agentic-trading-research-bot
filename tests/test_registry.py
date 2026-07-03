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
    assert set(registry.REGISTRY) >= {"stocks", "reddit", "edgar"}


def test_dispatch_lists_edgar():
    import registry
    assert "edgar" in registry.REGISTRY


def test_registry_has_all_three_screeners():
    import registry
    assert set(registry.REGISTRY) >= {"stocks", "reddit", "edgar"}


def test_dispatch_lists_fred():
    import registry
    assert "fred" in registry.REGISTRY


def test_dispatch_lists_cftc():
    import registry
    assert "cftc" in registry.REGISTRY


def test_dispatch_lists_ftd():
    import registry
    assert "ftd" in registry.REGISTRY

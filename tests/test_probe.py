"""stock_analysis_screener.probe: SvelteKit redirect envelope and error nodes."""

import io
import json
from contextlib import contextmanager

import pytest

from sources.screeners.stock_analysis_screener import probe


def _fake_urlopen(bodies):
    """Serve JSON bodies keyed by full URL; record the URLs requested."""
    calls = []

    @contextmanager
    def urlopen(req, timeout=60):
        calls.append(req.full_url)
        yield io.StringIO(json.dumps(bodies[req.full_url]))

    return urlopen, calls


REDIRECT = {"type": "redirect", "location": "/filings/CVNA/"}
PAGE = {"type": "data", "nodes": [{"type": "data", "data": [{"events": 1}, []]}]}


def test_resolve_follows_json_redirect_and_returns_final_path():
    urlopen, calls = _fake_urlopen(
        {
            probe.data_url("/stocks/CVNA/filings/"): REDIRECT,
            probe.data_url("/filings/CVNA/"): PAGE,
        }
    )
    final, raw = probe.resolve_data_json("/stocks/CVNA/filings/", urlopen=urlopen)
    assert final == "/filings/CVNA/"
    assert raw == PAGE
    assert calls == [probe.data_url("/stocks/CVNA/filings/"), probe.data_url("/filings/CVNA/")]


def test_fetch_data_json_decodes_through_redirect():
    urlopen, _ = _fake_urlopen(
        {
            probe.data_url("/stocks/cvna/"): {"type": "redirect", "location": "/stocks/CVNA/"},
            probe.data_url("/stocks/CVNA/"): PAGE,
        }
    )
    raw = probe.fetch_data_json("/stocks/cvna/", urlopen=urlopen)
    assert probe.decode_nodes(raw) == [{"events": []}]


def test_redirect_loop_is_bounded():
    loop = {"type": "redirect", "location": "/a/"}
    urlopen, calls = _fake_urlopen({probe.data_url("/a/"): loop})
    with pytest.raises(RuntimeError, match="too many"):
        probe.resolve_data_json("/a/", urlopen=urlopen, max_redirects=2)
    assert len(calls) == 3  # first fetch + two hops


def test_page_error_reads_trailing_error_node():
    raw = {
        "type": "data",
        "nodes": [
            {"type": "data", "data": [{"info": 1}, "x"]},
            {"type": "error", "error": {"message": "not found"}, "status": 404},
        ],
    }
    assert probe.page_error(raw) == {"status": 404, "message": "not found"}
    # decode_nodes drops the error node, so page data falls back to the layout node
    assert [n for n in probe.decode_nodes(raw) if n is not None] == [{"info": "x"}]


def test_page_error_is_none_without_error_node():
    assert probe.page_error(PAGE) is None
    assert probe.page_error({"type": "data", "nodes": []}) is None

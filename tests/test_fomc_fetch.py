import pytest

from sources.monitors.fomc_calendar import fetch

# Fixture shaped like the real page: per-year panels ("YYYY FOMC Meetings"),
# each meeting a __month + __date block. '*' on the date = press conference;
# "(tentative)" in the year heading = tentative year. Confirm/adjust the regex
# against the live markup at implementation — the raise-on-zero guard is the net.
_HTML = """
<div class="panel"><div class="panel-heading">2026 FOMC Meetings</div>
  <div class="fomc-meeting"><div class="fomc-meeting__month">January</div>
    <div class="fomc-meeting__date">27-28*</div></div>
  <div class="fomc-meeting"><div class="fomc-meeting__month">April/May</div>
    <div class="fomc-meeting__date">28-1</div></div>
</div>
<div class="panel"><div class="panel-heading">2027 FOMC Meetings (tentative)</div>
  <div class="fomc-meeting"><div class="fomc-meeting__month">January</div>
    <div class="fomc-meeting__date">26-27</div></div>
</div>
"""


# Real live markup (2026-07) wraps the month name in <strong>, and cross-month
# meetings render as a single wrapped "Apr/May". The __date cell stays unwrapped.
_HTML_STRONG = """
<div class="panel"><div class="panel-heading"><h4>2026 FOMC Meetings</h4></div>
  <div class="row fomc-meeting">
    <div class="fomc-meeting__month col-md-2"><strong>January</strong></div>
    <div class="fomc-meeting__date col-lg-1">27-28</div></div>
  <div class="row fomc-meeting">
    <div class="fomc-meeting__month col-md-2"><strong>Apr/May</strong></div>
    <div class="fomc-meeting__date col-lg-1">28-1</div></div>
</div>
"""


def test_parse_calendar_handles_strong_wrapped_months():
    meetings = fetch.parse_calendar(_HTML_STRONG)
    starts = {m["start_date"] for m in meetings}
    assert {"2026-01-27", "2026-04-28"} <= starts
    aprmay = next(m for m in meetings if m["start_date"] == "2026-04-28")
    assert aprmay["end_date"] == "2026-05-01"  # cross-month end resolves to May


def test_parse_calendar_extracts_meetings_and_dates():
    meetings = fetch.parse_calendar(_HTML)
    assert len(meetings) == 3
    jan = meetings[0]
    assert jan["start_date"] == "2026-01-27" and jan["end_date"] == "2026-01-28"
    assert jan["status"] == "confirmed"
    assert jan["has_press_conference"] is True


def test_parse_calendar_handles_cross_month_range():
    meetings = fetch.parse_calendar(_HTML)
    apr = meetings[1]
    assert apr["start_date"] == "2026-04-28" and apr["end_date"] == "2026-05-01"
    assert apr["has_press_conference"] is False


def test_parse_calendar_marks_tentative_year():
    meetings = fetch.parse_calendar(_HTML)
    assert meetings[2]["status"] == "tentative"  # 2027 panel


def test_parse_calendar_raises_on_zero_from_nonempty():
    with pytest.raises(fetch.FomcCalendarParseError):
        fetch.parse_calendar("<html><body>no meetings here</body></html>")


def test_minutes_date_is_end_plus_21_days():
    assert fetch.minutes_date("2026-01-28") == "2026-02-18"


def test_blackout_window_second_saturday_before_and_end_plus_one():
    # Jan 27-28 2026 (start is a Tuesday): nearest preceding Saturday = Jan 24,
    # second preceding = Jan 17; blackout ends end+1 = Jan 29.
    start, end = fetch.blackout_window("2026-01-27", "2026-01-28")
    assert start == "2026-01-17"
    assert end == "2026-01-29"


def test_blackout_window_when_start_is_saturday_walks_back_a_full_week():
    # If the meeting start is itself a Saturday, "preceding Saturday" is strictly
    # before it (a week back), then one more week => 14 days before.
    start, _ = fetch.blackout_window("2026-01-17", "2026-01-18")  # Jan 17 = Sat
    assert start == "2026-01-03"


def test_is_sep_meeting_true_only_for_quarter_months():
    assert fetch.is_sep_meeting("2026-03-18") is True
    assert fetch.is_sep_meeting("2026-06-17") is True
    assert fetch.is_sep_meeting("2026-01-28") is False

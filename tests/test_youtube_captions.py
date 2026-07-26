import json

import pytest

from tools.research.youtube_captions import (
    Cue,
    Transcript,
    is_asr,
    main,
    parse_json3,
    render,
    timestamp,
)

# Fixtures captured 2026-07-26 from a real `yt-dlp --sub-format json3` fetch of
# youtube.com/watch?v=dQw4w9WgXcQ, which publishes BOTH a human-authored track
# (`en`) and a machine-generated one (`en-orig`) over the same audio — so the
# two shapes below are the genuine article, not hand-written approximations.

ASR_PAYLOAD = {
    "wireMagic": "pb3",
    "events": [
        # No `segs`: a window/pen layout record, not speech.
        {"tStartMs": 0, "dDurationMs": 211879, "id": 1, "wpWinPosId": 1, "wsWinStyleId": 1},
        {
            "tStartMs": 18800,
            "dDurationMs": 7160,
            "wWinId": 1,
            "segs": [
                {"utf8": "We're", "acAsrConf": 0},
                {"utf8": " no", "tOffsetMs": 239, "acAsrConf": 0},
                {"utf8": " strangers", "tOffsetMs": 559, "acAsrConf": 0},
                {"utf8": " to", "tOffsetMs": 1040, "acAsrConf": 0},
            ],
        },
        # `aAppend` line-break marker: display wrapping, not a paragraph.
        {
            "tStartMs": 21790,
            "dDurationMs": 4170,
            "wWinId": 1,
            "aAppend": 1,
            "segs": [{"utf8": "\n"}],
        },
        {
            "tStartMs": 21800,
            "dDurationMs": 7319,
            "wWinId": 1,
            "segs": [
                {"utf8": "love.", "acAsrConf": 0},
                {"utf8": " You", "tOffsetMs": 1000, "acAsrConf": 0},
                {"utf8": " know", "tOffsetMs": 1239, "acAsrConf": 0},
                {"utf8": " the", "tOffsetMs": 1479, "acAsrConf": 0},
                {"utf8": " rules", "tOffsetMs": 1800, "acAsrConf": 0},
            ],
        },
        {
            "tStartMs": 25950,
            "dDurationMs": 3169,
            "wWinId": 1,
            "aAppend": 1,
            "segs": [{"utf8": "\n"}],
        },
        {
            "tStartMs": 25960,
            "dDurationMs": 4319,
            "wWinId": 1,
            "segs": [
                {"utf8": "I.", "acAsrConf": 0},
                {"utf8": " I", "tOffsetMs": 1079, "acAsrConf": 0},
                {"utf8": " feel", "tOffsetMs": 1319, "acAsrConf": 0},
                {"utf8": " commitments", "tOffsetMs": 1720, "acAsrConf": 0},
                {"utf8": " from what", "tOffsetMs": 2440, "acAsrConf": 0},
                {"utf8": " I'm", "tOffsetMs": 2680, "acAsrConf": 0},
            ],
        },
    ],
}

MANUAL_PAYLOAD = {
    "wireMagic": "pb3",
    "events": [
        {"tStartMs": 1360, "dDurationMs": 1680, "segs": [{"utf8": "[♪♪♪]"}]},
        {
            "tStartMs": 18640,
            "dDurationMs": 3240,
            "segs": [{"utf8": "♪ We're no strangers to love ♪"}],
        },
        {
            "tStartMs": 22640,
            "dDurationMs": 4320,
            "segs": [{"utf8": "♪ You know the rules\nand so do I ♪"}],
        },
        {
            "tStartMs": 27040,
            "dDurationMs": 4000,
            "segs": [{"utf8": "♪ A full commitment's\nwhat I'm thinking of ♪"}],
        },
    ],
}


def test_is_asr_reads_the_payload_not_the_filename():
    assert is_asr(ASR_PAYLOAD) is True
    assert is_asr(MANUAL_PAYLOAD) is False


def test_is_asr_on_an_empty_payload_is_false():
    assert is_asr({}) is False
    assert is_asr({"events": []}) is False


def test_parse_drops_layout_records_and_append_markers():
    """The 6-event ASR track holds 3 utterances: one window record, two markers."""
    transcript = parse_json3(ASR_PAYLOAD)
    assert [cue.text for cue in transcript.cues] == [
        "We're no strangers to",
        "love. You know the rules",
        "I. I feel commitments from what I'm",
    ]
    assert transcript.asr is True


def test_parse_collapses_newlines_inside_a_manual_cue():
    """A manual cue wraps for display; the sentence must survive as one line.

    Without this, a regex over the transcript for "the rules and so do I" misses
    because the caption file broke it across two display lines.
    """
    transcript = parse_json3(MANUAL_PAYLOAD)
    assert "♪ You know the rules and so do I ♪" in [c.text for c in transcript.cues]
    assert all("\n" not in cue.text for cue in transcript.cues)


def test_asr_and_manual_tracks_disagree_on_the_same_audio():
    """The whole reason ASR is a lower tier, demonstrated on one real video.

    The human track says "A full commitment's what I'm thinking of"; the machine
    heard "I feel commitments from what I'm". Same seconds, different words. A
    figure or a ticker mangled this way reads as a benchmark fact, so anything
    quoted from an ASR track must be confirmed against a primary source.
    """
    asr = " ".join(cue.text for cue in parse_json3(ASR_PAYLOAD).cues)
    manual = " ".join(cue.text for cue in parse_json3(MANUAL_PAYLOAD).cues)
    assert "commitments from what I'm" in asr
    assert "A full commitment's what I'm thinking of" in manual


def test_parse_collapses_a_repeated_cue():
    """Rolling duplication from a re-encoded track must not double a sentence."""
    payload = {
        "events": [
            {"tStartMs": 1000, "segs": [{"utf8": "margins expanded 300 basis points"}]},
            {"tStartMs": 2000, "segs": [{"utf8": "margins expanded 300 basis points"}]},
            {"tStartMs": 3000, "segs": [{"utf8": "margins expanded 300 basis points"}]},
        ]
    }
    assert len(parse_json3(payload).cues) == 1


def test_parse_sorts_by_start_time():
    payload = {
        "events": [
            {"tStartMs": 5000, "segs": [{"utf8": "second"}]},
            {"tStartMs": 1000, "segs": [{"utf8": "first"}]},
        ]
    }
    assert [cue.text for cue in parse_json3(payload).cues] == ["first", "second"]


def test_parse_raises_on_a_missing_start_time():
    """Defaulting to 0 would silently move a claim to the top of the video."""
    with pytest.raises(ValueError, match="event 0 has a non-integer tStartMs"):
        parse_json3({"events": [{"segs": [{"utf8": "hello"}]}]})


def test_parse_of_an_empty_payload_yields_no_cues():
    transcript = parse_json3({"events": []})
    assert transcript.cues == []
    assert transcript.duration_ms == 0


def test_duration_is_the_last_cue_start():
    assert parse_json3(ASR_PAYLOAD).duration_ms == 25960


@pytest.mark.parametrize(
    ("milliseconds", "expected"),
    [(0, "00:00:00"), (59_999, "00:00:59"), (60_000, "00:01:00"), (3_723_000, "01:02:03")],
)
def test_timestamp_formats_hours_minutes_seconds(milliseconds, expected):
    assert timestamp(milliseconds) == expected


def test_timestamp_refuses_a_negative_offset():
    with pytest.raises(ValueError, match="non-negative"):
        timestamp(-1)


def test_render_anchors_each_window_on_its_first_cue():
    transcript = Transcript(
        cues=[
            Cue(1_000, "alpha"),
            Cue(20_000, "beta"),
            Cue(31_000, "gamma"),
            Cue(95_000, "delta"),
        ],
        asr=False,
    )
    assert render(transcript, window_seconds=30) == (
        "[00:00:01] alpha beta\n\n[00:00:31] gamma\n\n[00:01:35] delta"
    )


def test_render_windows_are_absolute_not_relative_to_the_first_cue():
    """Two runs over the same video must break in the same places and diff cleanly.

    Both cues sit within 30s of each other, but straddle the 0:30 boundary — so
    they belong to different paragraphs.
    """
    transcript = Transcript(cues=[Cue(29_000, "before"), Cue(31_000, "after")], asr=False)
    assert render(transcript, window_seconds=30) == "[00:00:29] before\n\n[00:00:31] after"


def test_render_of_an_empty_transcript_is_empty():
    assert render(Transcript(cues=[], asr=False)) == ""


def test_render_refuses_a_non_positive_window():
    with pytest.raises(ValueError, match="window_seconds must be positive"):
        render(parse_json3(MANUAL_PAYLOAD), window_seconds=0)


def _write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_main_labels_a_machine_transcribed_track(tmp_path, capsys):
    assert main([_write(tmp_path, "en-orig.json3", ASR_PAYLOAD)]) == 0
    out = capsys.readouterr().out
    assert "AUTO-GENERATED (ASR)" in out
    assert "verify every figure and ticker" in out
    assert "[00:00:18] We're no strangers to love. You know the rules" in out


def test_main_does_not_warn_on_a_human_authored_track(tmp_path, capsys):
    assert main([_write(tmp_path, "en.json3", MANUAL_PAYLOAD)]) == 0
    out = capsys.readouterr().out
    assert "human-authored" in out
    assert "AUTO-GENERATED" not in out


def test_main_refuses_a_track_with_no_cues(tmp_path, capsys):
    """An empty benchmark would score a run flawless. It must fail loudly."""
    assert main([_write(tmp_path, "empty.json3", {"events": []})]) == 2
    assert "no caption cues" in capsys.readouterr().err


def test_main_refuses_unreadable_json(tmp_path, capsys):
    path = tmp_path / "broken.json3"
    path.write_text("not json", encoding="utf-8")
    assert main([str(path)]) == 2
    assert "refused: JSONDecodeError" in capsys.readouterr().err


def test_main_refuses_a_missing_file(tmp_path, capsys):
    assert main([str(tmp_path / "absent.json3")]) == 2
    assert "refused: FileNotFoundError" in capsys.readouterr().err


def test_main_honours_the_window_flag(tmp_path, capsys):
    path = _write(tmp_path, "en.json3", MANUAL_PAYLOAD)
    assert main([path, "--window-seconds", "5"]) == 0
    out = capsys.readouterr().out
    assert "[00:00:18]" in out
    assert "[00:00:22]" in out
    assert "[00:00:27]" in out

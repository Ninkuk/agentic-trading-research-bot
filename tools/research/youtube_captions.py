"""Turn a YouTube caption track into a citable transcript for the eval skills.

A professional's research often arrives as a video — an interview, a conference
talk, a fund manager walking through a name — not a PDF. This module decodes the
caption track into timestamped prose so it can be graded as a benchmark, and,
just as importantly, tells the caller *how much to trust it*.

**Take the ``json3`` format, never ``vtt``.** YouTube's auto-captions render as a
rolling two-line window, and ``vtt`` serializes that window verbatim: every line
appears twice, once entering and once leaving. Dumping such a file doubles the
word count and makes a speaker look like they repeated themselves. ``json3`` is
append-based instead — a continuation is its own event carrying only ``"\\n"`` —
so concatenating ``events[].segs[].utf8`` in order is already correct, with no
dedup heuristic to get wrong.

**Machine transcription is a lower evidence tier than a written report.** ASR
mishears exactly the tokens research turns on: figures ("fifteen" / "fifty"),
tickers, and proper nouns. ``is_asr`` reports whether the track was machine
generated so a caller can label the tier rather than guess it from a filename.

Pure: no network, no database, no wall clock. The fetch that produces the payload
lives in the skill's prose (``yt-dlp --sub-format json3``), decoding lives here.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

DEFAULT_WINDOW_SECONDS = 30
"""Seconds of speech per emitted paragraph.

Small enough that a ``[HH:MM:SS]`` anchor points at the claim rather than its
neighbourhood, large enough that an hour-long interview stays readable.
"""

_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Cue:
    """One caption event: when it was said, and what was said."""

    start_ms: int
    text: str


@dataclass(frozen=True)
class Transcript:
    """A decoded caption track plus the provenance needed to tier it."""

    cues: list[Cue]
    asr: bool
    """True when the track was machine-transcribed. See ``is_asr``."""

    @property
    def duration_ms(self) -> int:
        """Start of the last cue — the span the transcript actually covers.

        Deliberately not the video's duration, which this module cannot see. A
        track that stops 20 minutes into a 60-minute video is a truncated
        benchmark, and comparing this against the video length is how a caller
        catches that.
        """
        return self.cues[-1].start_ms if self.cues else 0


def is_asr(payload: Mapping) -> bool:
    """True when any segment carries ``acAsrConf`` — a machine-generated track.

    Read the payload, never the filename. ``yt-dlp`` names auto-captions
    ``<name>.en-orig.json3`` and human captions ``<name>.en.json3`` by
    convention, but the tag is the uploader's language label, not a provenance
    flag: a channel that uploads an ASR-derived caption file by hand produces a
    plain ``en`` track that is still machine-transcribed.

    ``acAsrConf`` is the per-word ASR confidence YouTube stamps on every segment
    of a generated track and on none of a human-authored one.
    """
    return any(
        "acAsrConf" in segment
        for event in payload.get("events") or []
        for segment in event.get("segs") or []
    )


def parse_json3(payload: Mapping) -> Transcript:
    """Decode a ``json3`` caption payload into ordered, whitespace-normalized cues.

    Three shapes are dropped, each for its own reason:

    - **Events with no ``segs``** are window/pen layout records, not speech.
    - **Events whose joined text is blank** are the ``aAppend`` line-break markers
      of a rolling ASR track. Their newline is display wrapping, not a paragraph.
    - **A cue identical to the one before it** is collapsed. json3 does not
      normally rolling-duplicate, but a re-encoded or third-party-generated track
      can, and a doubled sentence in a benchmark reads as emphasis the speaker
      never gave.

    Newlines *inside* a ``utf8`` value are also display wrapping (a manual cue
    reads ``"You know the rules\\nand so do I"``) and collapse to a single space,
    so a caller can regex across a sentence without line breaks splitting it.

    Cues are sorted by ``tStartMs``; ordering is never assumed from file order.
    A missing or non-integer ``tStartMs`` raises ``ValueError`` naming the event
    rather than defaulting to 0, which would silently move a claim to the start
    of the video and misdate a citation.
    """
    cues: list[Cue] = []
    for index, event in enumerate(payload.get("events") or []):
        segments = event.get("segs")
        if not segments:
            continue

        text = _WHITESPACE.sub(" ", "".join(seg.get("utf8", "") for seg in segments)).strip()
        if not text:
            continue

        start = event.get("tStartMs")
        if not isinstance(start, int):
            raise ValueError(f"event {index} has a non-integer tStartMs: {start!r}")

        if cues and cues[-1].text == text:
            continue
        cues.append(Cue(start_ms=start, text=text))

    cues.sort(key=lambda cue: cue.start_ms)
    return Transcript(cues=cues, asr=is_asr(payload))


def timestamp(milliseconds: int) -> str:
    """``HH:MM:SS`` for a cue offset. Hours are always shown, zero-padded."""
    if milliseconds < 0:
        raise ValueError(f"milliseconds must be non-negative, got {milliseconds}")
    seconds = milliseconds // 1000
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def render(
    transcript: Transcript,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
) -> str:
    """Group cues into ``[HH:MM:SS]``-anchored paragraphs.

    The anchor is the first cue in each window, so a quote pulled from the
    paragraph can be cited to a point in the video and checked by a human. A
    benchmark claim that cannot be located is not a benchmark claim.

    Windows are absolute (0:00–0:30, 0:30–1:00, …) rather than relative to the
    first cue, so two runs over the same video always break in the same places
    and their outputs diff cleanly.

    Raises ValueError on a non-positive ``window_seconds`` (every cue would land
    in its own bucket or in none).
    """
    if window_seconds <= 0:
        raise ValueError(f"window_seconds must be positive, got {window_seconds}")

    window_ms = window_seconds * 1000
    paragraphs: list[str] = []
    current: list[str] = []
    current_window = -1

    for cue in transcript.cues:
        window = cue.start_ms // window_ms
        if window != current_window:
            if current:
                paragraphs.append(" ".join(current))
            current = [f"[{timestamp(cue.start_ms)}]"]
            current_window = window
        current.append(cue.text)

    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.research.youtube_captions",
        description=(
            "Render a yt-dlp json3 caption track as a timestamped transcript. "
            "A machine-transcribed track is a lower evidence tier — figures and "
            "tickers in it must be confirmed against a primary source."
        ),
    )
    parser.add_argument("path", help="path to a .json3 caption file written by yt-dlp")
    parser.add_argument(
        "--window-seconds",
        type=int,
        default=DEFAULT_WINDOW_SECONDS,
        help=f"seconds of speech per timestamped paragraph (default {DEFAULT_WINDOW_SECONDS})",
    )
    args = parser.parse_args(argv)

    try:
        with open(args.path, encoding="utf-8") as handle:
            payload = json.load(handle)
        transcript = parse_json3(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"refused: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    # An empty track must never render as an empty benchmark: a zero-byte
    # transcript scores every dimension as "the professional did not cover it"
    # and reports a flawless run. Fail loudly instead.
    if not transcript.cues:
        print(f"refused: no caption cues in {args.path}", file=sys.stderr)
        return 2

    source = "AUTO-GENERATED (ASR)" if transcript.asr else "human-authored"
    print(f"# caption track: {source}")
    print(f"# cues: {len(transcript.cues)}  covers: 00:00:00-{timestamp(transcript.duration_ms)}")
    if transcript.asr:
        print("# TIER: machine transcription — verify every figure and ticker before citing it.")
    print()
    print(render(transcript, args.window_seconds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

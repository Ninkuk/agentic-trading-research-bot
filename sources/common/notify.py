"""Push notifications via ntfy (https://ntfy.sh) — stdlib only.

Generic transport, not tied to any caller: importable from Python
(``send(...)``) and invokable from shell (``python -m sources.common.notify``),
so launchd wrappers, future pipeline stages, or ad-hoc scripts all share one
path. Config comes from the environment (.env):

    NTFY_TOPIC   required — the (secret) topic to publish to
    NTFY_SERVER  optional — defaults to https://ntfy.sh
    NTFY_TOKEN   optional — Bearer token for a protected server/topic

Secret hygiene: the topic is embedded in the request URL, so a urllib error
message can leak it. ``send`` raises with the URL scrubbed; the CLI prints
only the exception type name, matching the screeners' error convention.
"""
import argparse
import os
import sys
import urllib.error
import urllib.request

DEFAULT_SERVER = "https://ntfy.sh"


def _default_post(url: str, data: bytes, headers: dict) -> None:
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="POST")
    with urllib.request.urlopen(req, timeout=30):
        pass


def send(message: str, *, title=None, priority=None, tags=None,
         topic=None, server=None, token=None, post=None) -> None:
    """Publish one notification. ``tags`` is an iterable of ntfy tag names
    (e.g. emoji shortcodes); ``priority`` is 1-5 or an ntfy name like "high".
    Raises RuntimeError (topic unset, or scrubbed transport failure)."""
    post = post or _default_post
    topic = topic or os.environ.get("NTFY_TOPIC")
    if not topic:
        raise RuntimeError(
            "NTFY_TOPIC is not set; add it to .env (see .env.example)")
    server = (server or os.environ.get("NTFY_SERVER")
              or DEFAULT_SERVER).rstrip("/")
    token = token or os.environ.get("NTFY_TOKEN")

    headers = {}
    if title:
        headers["Title"] = str(title)
    if priority:
        headers["Priority"] = str(priority)
    if tags:
        headers["Tags"] = ",".join(str(t) for t in tags)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        post(f"{server}/{topic}", message.encode("utf-8"), headers)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        # Never re-raise the original: HTTPError/URLError carry the topic URL.
        raise RuntimeError(f"ntfy publish failed: {type(e).__name__}") from None


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Publish an ntfy notification (message from args or stdin)")
    p.add_argument("message", nargs="?", default=None,
                   help="message body ('-' or omitted: read stdin)")
    p.add_argument("--title", default=None)
    p.add_argument("--priority", default=None, help="1-5 or ntfy name")
    p.add_argument("--tags", default=None, help="comma-separated ntfy tags")
    a = p.parse_args(argv)

    message = a.message
    if message in (None, "-"):
        message = sys.stdin.read()
    tags = a.tags.split(",") if a.tags else None
    try:
        send(message, title=a.title, priority=a.priority, tags=tags)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

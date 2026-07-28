"""Every Robinhood MCP tool a headless skill names must be a decision.

The 2026-07-23/24 outage (and the 2026-07-07/08 one before it): a skill's
prose started calling an MCP tool the launchd wrapper's --allowedTools pin
didn't include, so the scheduled run blocked forever on a permission prompt
nobody was there to approve (the wrappers pin --permission-mode default, so
an omitted getter is a hard outage, not a soft prompt).

This test forces the decision at edit time: a tool named in a skill must be
either in its wrapper's allowlist or in DELIBERATE_NON_CALLS below (with the
skill documenting why it isn't called headlessly). A new mention that is
neither fails here — the failure the next scheduled run would otherwise have
at 14:30 with nobody watching.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PREFIX = "mcp__claude_ai_Robinhood_MCP__"

# skill file -> (wrapper file, tools the skill names but deliberately never
# calls in the headless run — each must stay documented as such in the skill)
PAIRS = {
    ".claude/skills/account-positions/SKILL.md": (
        "deploy/launchd/portfolio_snapshot.sh",
        {"get_equity_tax_lots"},  # read at decision time via kill-thesis, not here
    ),
    ".claude/skills/journal-sync/SKILL.md": (
        "deploy/launchd/journal_sync.sh",
        set(),
    ),
}

# Robinhood tool names are verb_noun tokens; match the short form the skill
# prose uses. Anchored to known verbs so ordinary identifiers don't match.
_TOOL = re.compile(
    r"\b((?:get|place|review|cancel|run|create|update|add|remove|exercise|search|follow|unfollow)_[a-z_]+)\b"
)


def _wrapper_allowlist(text: str) -> set[str]:
    return {m.removeprefix(PREFIX) for m in re.findall(PREFIX + r"[a-z_]+", text)}


def test_every_tool_a_skill_names_is_allowlisted_or_deliberate():
    for skill_rel, (wrapper_rel, non_calls) in PAIRS.items():
        skill = (REPO / skill_rel).read_text()
        allow = _wrapper_allowlist((REPO / wrapper_rel).read_text())
        named = set(_TOOL.findall(skill))
        undecided = named - allow - non_calls
        assert not undecided, (
            f"{skill_rel} names {sorted(undecided)} but {wrapper_rel} doesn't"
            " allowlist them. Add to the wrapper's --allowedTools (the run"
            " will call it) or to DELIBERATE_NON_CALLS here (and document the"
            " why in the skill) — otherwise the next scheduled run hangs on a"
            " permission prompt."
        )


def test_deliberate_non_calls_are_still_named_by_the_skill():
    # An exception for a tool the skill no longer mentions is dead weight —
    # prune it so the list stays an honest record of live decisions.
    for skill_rel, (_, non_calls) in PAIRS.items():
        skill = (REPO / skill_rel).read_text()
        gone = {t for t in non_calls if t not in skill}
        assert not gone, f"{skill_rel} no longer names {sorted(gone)}; prune the exception"


def test_wrappers_pin_permission_mode():
    # 0d90bfa: --allowedTools is advisory unless the mode is pinned. If the
    # pin disappears, denials degrade to silent skips and the allowlist test
    # above stops meaning anything.
    for _, (wrapper_rel, _) in PAIRS.items():
        text = (REPO / wrapper_rel).read_text()
        assert "--permission-mode" in text, f"{wrapper_rel} lost its --permission-mode pin"

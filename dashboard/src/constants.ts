// Cross-section constants. Today just the repo URL ResearchReopens needs to
// build a thesis-file link (data.py exports a repo-relative `thesis_path`
// only — never an absolute URL — so the client owns this join). Verified
// against `_REPO_URL` in deploy/launchd/dashboard_lib/sections.py:70 —
// capital N in "Ninkuk".
export const REPO_URL = "https://github.com/Ninkuk/agentic-trading-research-bot";

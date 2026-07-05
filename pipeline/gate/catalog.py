import hashlib
import json

TAU = 0.5              # confidence threshold; below it the agent is ignored
HEAT_CAP = 0.06        # portfolio heat cap: sum(final_shares*stop_distance) <= cap*equity
DEFAULT_MODEL = "claude-sonnet-5"
MAX_TOKENS = 300       # the grammar is tiny by design
LLM_ATTEMPTS = 3       # transport retries inside llm.complete / complete_cli
RATIONALE_MAX = 500    # longer rationales are truncated, not rejected
CLI_BIN = "claude"     # headless subscription-auth backend (no-API-key policy)
CLI_TIMEOUT_S = 180    # per-attempt subprocess budget for `claude -p`

# The only detail metrics that may cross the mask (normalized values, never
# identifiers): COT premise + confirm indexes, quality dimension z-scores.
MASK_DETAIL_KEYS = ("commercial_index", "speculator_index",
                    "profitability_z", "growth_z", "safety_z")

SYSTEM_PROMPT = """\
You are a risk reviewer for a systematic trading pipeline. You will see ONE
candidate position as masked, normalized quantitative facts (no tickers, no
prices, no dates). Your only job is to sanity-read the picture for red flags
(deteriorating confirm leg, crowded positioning, an imminent binary event
given "earnings in N days") and express caution - never conviction. You can
approve, cut size, or veto; you can never increase size, add instruments, or
bypass a check. Your vetoes and cuts are logged and audited.

Reply with EXACTLY one JSON object and nothing else:
{"action": "approve" | "veto",
 "size_mult": <float 0.0-1.0, fraction of the allowed size>,
 "confidence": <float 0.0-1.0>,
 "rationale": "<= 500 chars"}
"""


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def guardrail_config_version(tau, heat_cap, model,
                             candidates_config_hash) -> str:
    """sha256 of the EFFECTIVE runtime config — a --tau override changes the
    hash (constants-only hashing would silently lie)."""
    return hashlib.sha256(canonical_json(
        {"tau": tau, "heat_cap": heat_cap, "model": model,
         "candidates_config_hash": candidates_config_hash}
    ).encode()).hexdigest()

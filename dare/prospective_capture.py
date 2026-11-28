"""Offline capture preparation, no provider calls or execution authority."""
import hashlib
import json
from shadow_advisor import REPOSITORY, SHA


def prepare_capture(payload, collected_at, *, included_verified=False,
                    no_paid_fallback=False, scope_approved=False):
    """Preserve a parsed status representation, not original transport bytes.

    No inference of CI head, unresolved threads or capture authenticity.
    The returned record is a candidate only, never an eligible study case.
    """
    if not all(x is True for x in (included_verified, no_paid_fallback, scope_approved)):
        raise ValueError("collection authorization or cost evidence missing")
    if type(collected_at) is not int or collected_at < 0:
        raise ValueError("invalid collection time")
    if type(payload) is not dict or payload.get("repository") != REPOSITORY:
        raise ValueError("invalid repository")
    number, head = payload.get("number"), payload.get("headSha")
    if type(number) is not int or number <= 0 or type(head) is not str or not SHA.fullmatch(head):
        raise ValueError("invalid PR identity")
    # Allowlist metadata; deliberately omit free-text findings, logs and URLs.
    codex = payload.get("codex")
    readiness = payload.get("readiness")
    statuses = {
        "state": ("open", "closed", "merged"),
        "ci": ("success", "failure", "pending", "unknown", "skipped"),
    }
    safe = {"repository": REPOSITORY, "number": number, "headSha": head}
    for key, allowed in statuses.items():
        value = payload.get(key)
        safe[key] = value if type(value) is str and value in allowed else "unknown"
    for key in ("draft", "ciAvailable", "ciComplete", "findingsAvailable", "findingsIncomplete"):
        value = payload.get(key)
        safe[key] = value if type(value) is bool else None
    for key, obj, allowed in (
        ("codex", codex, ("clear", "findings", "pending", "unknown")),
        ("readiness", readiness, ("ready", "not_ready", "unknown")),
    ):
        value = obj.get("state") if type(obj) is dict else None
        safe[key] = value if type(value) is str and value in allowed else "unknown"
    counts = payload.get("findingCounts")
    for key in ("open", "waiting", "unverified", "fixed"):
        value = counts.get(key) if type(counts) is dict else None
        safe["findings_" + key] = value if type(value) is int and value >= 0 else None
    data = json.dumps(safe, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return data, {
        "representation": "allowlisted_reserialized_metadata",
        "source": "repo_autopilot_status",
        "collected_at": collected_at,
        "sha256": hashlib.sha256(data).hexdigest(),
        "number": number, "head": head,
        "eligibility": "CANDIDATE_ONLY",
        "missing": ["original_transport_bytes", "verified_capture_time",
                    "explicit_ci_head", "explicit_review_head",
                    "unresolved_thread_count", "mergeability",
                    "independent_reference", "authenticated_source"],
    }

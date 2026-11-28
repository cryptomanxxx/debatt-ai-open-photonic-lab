"""DARE-003A: pure offline PR metadata advisor, never authorizes actions."""
from dataclasses import dataclass
import re

REPOSITORY = "cryptomanxxx/debatt-ai-open-photonic-lab"
SHA = re.compile(r"[0-9a-f]{40}")
MAX_AGE = 300  # Proposed synthetic freshness threshold.


@dataclass(frozen=True)
class Observation:
    repository: str
    number: int
    head: str
    observed: int
    source: str
    state: str
    draft: bool
    ci: str
    ci_complete: bool
    ci_head: str
    review: str
    review_head: str
    findings_complete: bool
    open_findings: int
    unresolved_threads: int
    mergeability: str
    readiness: str


def normalize(raw):
    """Strict normalized-record contract; not a provider API adapter."""
    if type(raw) is not dict or set(raw) != set(Observation.__dataclass_fields__):
        raise ValueError("unexpected record schema")
    for key in ("repository", "head", "source", "state", "ci", "ci_head",
                "review", "review_head", "mergeability", "readiness"):
        if type(raw[key]) is not str:
            raise ValueError("invalid string")
    for key in ("number", "observed", "open_findings", "unresolved_threads"):
        if type(raw[key]) is not int:
            raise ValueError("invalid integer")
    for key in ("draft", "ci_complete", "findings_complete"):
        if type(raw[key]) is not bool:
            raise ValueError("invalid boolean")
    if raw["repository"] != REPOSITORY or raw["number"] <= 0 or raw["observed"] < 0:
        raise ValueError("invalid identity")
    if not SHA.fullmatch(raw["head"]) or raw["source"] not in ("synthetic", "archived"):
        raise ValueError("invalid provenance")
    for key in ("ci_head", "review_head"):
        if raw[key] and not SHA.fullmatch(raw[key]):
            raise ValueError("invalid evidence head")
    enums = {
        "state": {"open", "closed", "merged"},
        "ci": {"success", "failure", "pending", "skipped", "unknown"},
        "review": {"clear", "findings", "pending", "unknown"},
        "mergeability": {"clean", "blocked", "unknown"},
        "readiness": {"ready", "not_ready", "unknown"},
    }
    if any(raw[k] not in allowed for k, allowed in enums.items()):
        raise ValueError("unknown status")
    if min(raw["open_findings"], raw["unresolved_threads"]) < -1:
        raise ValueError("invalid count")
    return Observation(**raw)


def advise(raw, now):
    """Return one advisory label; observation time is replay time, not wall time."""
    try:
        o = normalize(raw)
    except (ValueError, TypeError):
        return "BLOCK_UNKNOWN"
    if type(now) is not int or not 0 <= o.observed <= now or now - o.observed > MAX_AGE:
        return "BLOCK_UNKNOWN"
    if o.state != "open":
        return "ALREADY_CLOSED" if o.readiness != "ready" else "BLOCK_UNKNOWN"
    if o.draft:
        return "BLOCK_UNKNOWN"
    if (o.ci_head != o.head or o.review_head != o.head
            or not o.findings_complete or o.open_findings < 0
            or o.unresolved_threads < 0
            or o.ci in ("unknown", "skipped") or o.review == "unknown"
            or o.mergeability == "unknown" or o.readiness == "unknown"):
        return "BLOCK_UNKNOWN"
    if ((o.review == "clear" and o.open_findings != 0)
            or (o.review == "findings" and o.open_findings == 0)
            or (o.ci == "pending" and o.ci_complete)
            or (o.ci == "success" and not o.ci_complete)):
        return "BLOCK_UNKNOWN"
    ready = (o.ci == "success" and o.ci_complete and o.review == "clear"
             and o.open_findings == 0 and o.unresolved_threads == 0
             and o.mergeability == "clean")
    if o.readiness == "ready":
        return "REQUEST_HUMAN_REVIEW" if ready else "BLOCK_UNKNOWN"
    if ready:
        return "BLOCK_UNKNOWN"
    if o.review == "findings" or (o.ci == "failure" and o.ci_complete):
        return "PROPOSE_CORRECTION"
    if o.ci == "pending":
        return "WAIT_CI"
    if o.review == "pending" or o.unresolved_threads > 0:
        return "WAIT_REVIEW"
    return "BLOCK_UNKNOWN"

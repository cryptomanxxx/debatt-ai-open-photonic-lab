"""Offline replay of explicitly frozen normalized observations and human labels.

No acquisition, mutation, credential access, or automatic label generation.
The operator is responsible for authenticating sources and freezing labels
before seeing advisor outputs.
"""
from collections import Counter
import hashlib
import json
from shadow_advisor import advise, normalize

LABELS = frozenset({"WAIT_CI", "WAIT_REVIEW", "PROPOSE_CORRECTION",
                    "REQUEST_HUMAN_REVIEW", "BLOCK_UNKNOWN", "ALREADY_CLOSED"})
STRATA = ("clean_ready", "ci_pending", "ci_failure", "review_findings",
          "incomplete_stale_conflicting")


def digest(value):
    """SHA-256 of canonical JSON bytes (not a hash of original capture bytes)."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def evaluate(records, references, frozen_digest):
    """Evaluate frozen inputs; exclude synthetic cases from real-study metrics.

    records: list of observation envelopes; references: dict keyed by case ID.
    Reject mismatched digests, duplicate PR-heads and unlabelled cases.
    """
    if type(records) is not list or type(references) is not dict:
        raise ValueError("invalid study container")
    if digest({"records": records, "references": references}) != frozen_digest:
        raise ValueError("study freeze digest mismatch")
    ids, identities = set(), set()
    rows = []
    for case in records:
        if type(case) is not dict or set(case) != {"id", "stratum", "record", "now", "raw_sha256"}:
            raise ValueError("invalid case envelope")
        cid = case["id"]
        if type(cid) is not str or not cid or cid in ids or case["stratum"] not in STRATA:
            raise ValueError("invalid case identity")
        ids.add(cid)
        o = normalize(case["record"])
        key = (o.repository, o.number, o.head)
        if key in identities:
            raise ValueError("duplicate PR head")
        identities.add(key)
        h = case["raw_sha256"]
        if type(h) is not str or len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
            raise ValueError("invalid capture hash")
        ref = references.get(cid)
        if type(ref) is not dict or set(ref) != {"label", "reviewer", "reason"}:
            raise ValueError("missing reference")
        if (type(ref["label"]) is not str or ref["label"] not in LABELS
                or any(type(ref[k]) is not str or not ref[k].strip() for k in ("reviewer", "reason"))):
            raise ValueError("invalid reference")
        if type(case["now"]) is not int or case["now"] < 0:
            raise ValueError("invalid replay time")
        result = advise(case["record"], case["now"])
        repeated = advise(case["record"], case["now"])
        rows.append({"id": cid, "source": o.source, "stratum": case["stratum"],
                     "reference": ref["label"], "advice": result,
                     "replay_equal": result == repeated})
    if ids != set(references):
        raise ValueError("unmatched reference IDs")

    def summarize(group):
        n = len(group)
        nonready = sum(x["reference"] != "REQUEST_HUMAN_REVIEW" for x in group)
        blocked = sum(x["reference"] == "BLOCK_UNKNOWN" for x in group)
        false_ready = sum(x["reference"] != "REQUEST_HUMAN_REVIEW"
                          and x["advice"] == "REQUEST_HUMAN_REVIEW" for x in group)
        missed = sum(x["reference"] == "BLOCK_UNKNOWN"
                     and x["advice"] != "BLOCK_UNKNOWN" for x in group)
        correct = sum(x["reference"] == x["advice"] for x in group)
        abstained = sum(x["advice"] == "BLOCK_UNKNOWN" for x in group)
        counts = Counter((x["reference"], x["advice"]) for x in group)
        strata = Counter(x["stratum"] for x in group)
        return {"n": n, "correct": correct, "agreement": correct/n if n else None,
                "false_ready": false_ready, "nonready": nonready,
                "false_ready_rate": false_ready/nonready if nonready else None,
                "missed_blockers": missed, "blocked": blocked,
                "missed_blocker_rate": missed/blocked if blocked else None,
                "abstentions": abstained, "abstention_rate": abstained/n if n else None,
                "deterministic": all(x["replay_equal"] for x in group) if n else None,
                "strata": {s: strata[s] for s in STRATA},
                "confusion": {a: {b: counts[a,b] for b in sorted(LABELS)}
                              for a in sorted(LABELS)}}

    real = summarize([x for x in rows if x["source"] == "archived"])
    synthetic = summarize([x for x in rows if x["source"] == "synthetic"])
    return {"real": real, "synthetic": synthetic, "rows": rows,
            "sample_complete": real["n"] == 30 and all(real["strata"][s] == 6 for s in STRATA),
            "operational_gate": "NOT_EVALUATED"}

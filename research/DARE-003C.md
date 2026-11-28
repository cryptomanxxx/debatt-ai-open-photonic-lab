# DARE-003C · Dataset integrity and validation

Date: 2026-11-28. Status: implemented and locally tested; historical study not started. No live reader or autonomous operations.

## Software evidence

Baseline: [85/85 tests passed](evidence/dare-003c/baseline-85.log), source revision 63e82fa859aff0ce85544ef077ba809d261b5512. Candidate: [93/93 tests passed](evidence/dare-003c/candidate-93.log), source revision 331c9e089cc12b451334cfb25bea909f00f426d8. Python 3.13.5, standard library only. [Provenance](evidence/dare-003c/provenance.json) records source hashes, commands, exit codes, elapsed times and log hashes; both archived log blob hashes matched the actual local output. These are synthetic software tests, not independent human-labelled real observations or GitHub Actions results.

## Integrity gate

[capture_integrity.py](../dare/capture_integrity.py) checks the frozen manifest digest, exact case coverage, local relative file paths, source category and capture metadata, declared SHA-256 and actual file bytes before calling the frozen-dataset evaluator. Symlink entries and traversal paths are rejected. [Eight new tests](../dare/test_capture_integrity.py) cover valid bytes, tampering, missing files, traversal, symlinks, source mismatch, unmatched manifest entries and changed freeze digest.

The byte check does not establish provider authenticity, independent labels or correct normalization. It assumes a trusted static local directory and independently frozen manifest; no protection against ancestor symlinks, concurrent changes, relabelled source categories or re-used capture files is demonstrated. Capture metadata checks are preliminary: independently verify that original capture time is not later than the decision being replayed, and distinguish archival retrieval time from original capture time. The legacy evaluator remains callable; for study use require the integrity wrapper and manual eligibility audit. No automatic operational gate.

## Historical inventory

[Version 2](evidence/dare-003c/historical-inventory-v2.json) adds PR 341 from the already observed status response; the earlier inventory is unchanged. Seven clean-ready candidates, zero candidates in the other four strata, zero eligible frozen real observations. Updated-at and review activity times are not original capture timestamps. No additional live calls were made to retrieve research observations. No real study metrics.

## Proposed prospective collection (not authorized yet)

Existing Repo Autopilot tool descriptions inspected without invoking its live data retrieval: pull_request_status exposes current readiness and review/CI summary; pull_request_checks describes head-specific checks and can retrieve failure annotations/log excerpts; codex_findings describes review findings; list_pull_requests covers only six recently updated PRs, and workflow-run listing reads at most 60 recent runs. These are interface descriptions, not evidence that historical point-in-time snapshots or account-specific included quotas are available.

1. Approve an explicit bounded collection scope and verify actual included/free quotas and no paid fallback. If unknown, stop. No background polling, new credentials or infrastructure.
2. Collect metadata only at human-triggered workflow checkpoints, prior to merge or correction. Prefer minimal structured status, not log contents. Record UTC capture time, source identity, exact PR head, completeness, provider limitations and original authorized response bytes where accessible. If only parsed or reserialized data are available, preserve and label that representation honestly; never claim it is the original transport bytes.
3. For incomplete fields, record unknown, not inferred green. Check head stability across separate reads, independently establish required checks and unresolved-thread evidence. Do not fetch extra details without approval or expose secrets. Preserve failed or incomplete captures.
4. Maintain an outcome-independent inventory of consecutive eligible observations and predeclared strata. Record exclusions and gaps. Capture up to the separately approved bound; do not generate failures to fill quotas. If historical data are insufficient, prospectively amend and approve the study protocol before seeing outputs.
5. Present eligible frozen normalized records without advisor output to a human reviewer. Record pseudonymous reviewer, label, reason and freeze commit; only then replay. Do not use prior merge orders as blinded labels.

## Remaining gate

No real dataset ready for evaluation. Next: approve prospective collection protocol if historical captures cannot be recovered; build a conservative normalization mapping and enforce case identity/time binding, and confirm the actual read-only access/cost constraints. Independent labels and original capture provenance remain mandatory. DARE-003 Stage B and DARE-004 remain unapproved. Zero Additional Cost Policy unchanged.

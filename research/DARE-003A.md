# DARE-003A · Shadow decision engine

Date: 2026-11-28. Status: initial pure offline advisor implemented and 76/76 cumulative regression tests passed. The proposed historical study has not begun; no live integration.

## Implementation

[shadow_advisor.py](../dare/shadow_advisor.py) implements a strict normalized observation contract and deterministic advice. It accepts one allowlisted repository, positive PR number, exact 40-character lowercase hexadecimal head, explicit evidence-head binding, observation time, source class, state and typed CI/review/completeness/count/mergeability/readiness fields. Missing, stale, future, malformed or conflicting evidence blocks ready advice. The synthetic age limit is 300 seconds, evaluated against a supplied replay time rather than wall clock.

Output labels follow the [proposed protocol](DARE-003-PROTOCOL.md): WAIT_CI, WAIT_REVIEW, PROPOSE_CORRECTION, REQUEST_HUMAN_REVIEW, BLOCK_UNKNOWN, ALREADY_CLOSED. A clean ready label requests human consideration only. No execution commands, network, credentials, subprocess or mutation adapter. This is PR-status triage, not proof of scientific validity, cost eligibility or task approval. It does not replace the DARE-002 execution gates.

## Software test evidence

[Actual local output](evidence/dare-003a/shadow-76.log) and [provenance](evidence/dare-003a/provenance.json) record 76/76 passing tests at source commit bcce3383657ad4b0bad74a6984fc5663b7c9b5cc, Python 3.13.5, 0.087 s. All twelve local source files matched the corresponding recorded Git blob hashes (ten unchanged baseline sources and two new fetched PR branch blobs). [Ten new fixtures](../dare/test_shadow_advisor.py) include 18 blocked subcases, valid ready/pending/failure/findings/closed labels, stale/future time and deterministic replay. These are author-defined synthetic tests, not independent human-labelled study observations. No false-ready rate on real observations has been measured.

## Remaining work

The normalized record is not a verified Repo Autopilot API schema. Source is a category, not authenticated provenance; actual raw source identity, timestamp, hash and evidence binding must be captured separately. Unknown or contradictory metadata cannot be silently promoted to known. A pending review or CI may lack current-head evidence and be conservatively blocked; measure such abstentions rather than invent evidence. Provider fields and free/included access remain unverified for autonomous retrieval.

Next: define a local replay dataset format with separate immutable raw observations, normalized records and blinded human reference labels; inventory available historical captures and report missing strata. Freeze labels and protocol before exposing study outputs. Synthetic fixtures cannot fill the real-observation quota. Do not fetch live metadata through a new adapter, poll, launch agents, dispatch workflows or perform mutations. Stage B remains separately gated. Zero Additional Cost Policy unchanged.

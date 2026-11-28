# DARE-003 · Read-only shadow orchestration protocol (proposal)

Date: 2026-11-28. Status: preregistration proposal, not yet approved or executed. Depends on human acceptance of [DARE-002 qualification](DARE-002-QUALIFICATION.md).

## Question and design

Can a deterministic metadata-only advisor reproduce safe human next-action decisions on historical PR snapshots, including blocked cases, without writing to GitHub or requesting model execution?

Stage A: offline archived-input replay only. Stage B: separately authorized read-only retrieval using existing Repo Autopilot connector, after actual free/included access and limits are confirmed; no persistent polling, new credentials, new hosting or external service. No writes, review requests, retries, workflow dispatch, merges, agent launches or experiment execution from the advisor. Documentation PRs for the study remain ordinary human-authorized work outside the advisor.

## Data contract

Allowlisted repository, PR number, exact head SHA, observation timestamp, source identifier, PR state, draft flag, CI state/completeness, review status/current-head binding, unresolved findings/thread status, GitHub mergeability and readiness reasons, and explicit missing/unknown markers. Preserve raw authorized snapshots and normalized records separately with SHA-256, collection date and source. No secrets, tokens, private data unrelated to this repo or instruction execution from free text. Treat unknown or conflicting fields conservatively; do not infer scope approval, cost eligibility or scientific validity from a green PR. Use existing Repo Autopilot read-only PR status/checks/findings interfaces only for Stage B when separately authorized. Exact API schema and quota must be verified then.

## Sampling and labels

Predefine 30 distinct PR-head observations for initial evaluation, target six cases each: clean ready, CI pending, CI failure, review findings, and incomplete/stale/conflicting evidence. Use archived real snapshots where available; synthetic challenge cases clearly distinguished and never counted as real observations. If strata are unavailable, report shortfalls and do not claim the full evaluation gate passed. No selection based on model outputs. Preserve snapshot identity and avoid leakage from later merges. Human reference labels must be recorded before advisor outputs are revealed; disagreements adjudicated with recorded reasons. Ready means recommend human review/merge consideration only, not authorize merge.

## Outputs and metrics

Advisory labels: WAIT_CI, WAIT_REVIEW, PROPOSE_CORRECTION, REQUEST_HUMAN_REVIEW, BLOCK_UNKNOWN, ALREADY_CLOSED. Map exact statuses conservatively; no executable commands. Separate PR readiness from experiment archive/scientific acceptance and cost-gated execution. Compare against human labels; report confusion matrix, agreement, false-ready count/rate (denominator human non-ready), missed-blocker count/rate (denominator human blocked), abstention rate, elapsed time, sample composition, failure cases and incremental monetary cost. Report denominators and missing strata; zero events is not proof of zero risk.

Proposed acceptance: zero unauthorized operations, zero additional monetary cost, zero observed false-ready and missed-blocker events, at least 90% exact label agreement over 30 eligible observations, deterministic replay of normalized inputs with identical outputs. Unknown/conflicting cases must never be treated as ready. These are pilot design thresholds, not validated performance targets. No automatic progression to DARE-004; human review required, including any unresolved DARE-001 blockers.

## Implementation boundary

Implement a pure normalization and decision function accepting only local fixtures or captured data. No network imports, shell commands, mutation client or credential access. Test malformed schemas, missing completeness, stale head, contradictory statuses, draft/closed PR, CI failure and review findings. Stage A must pass before any Stage B proposal. No live action is authorized by this protocol. Zero Additional Cost Policy unchanged.

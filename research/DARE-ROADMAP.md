# DARE · Debatt-AI Autonomous Research Engine

Date: 2026-11-28. Status: proposed research infrastructure roadmap; no autonomous execution, deployment, paid service or change to repository permissions authorized by this document.

## Motivation and research question

Can a human-approved scientific roadmap be executed by AI agents through a bounded, auditable GitHub pull-request lifecycle, reducing human coordination effort without degrading scientific validity, reproducibility or security?

Strategic research planning and architecture design are increasingly AI-assisted. Implementation, review, correction, CI, evidence archival and selection of the next task remain labor-intensive. DARE investigates automation of this execution layer, not replacement of scientific judgment. The human defines objectives, approves scope and retains authority over scientific claims and changes of direction.

DARE is cross-cutting infrastructure for OPA-W, OPA-M, OPA-G, OPVR, PFA and other lab research, not a new photonic hardware claim. Existing research priorities and phase gates remain unchanged.

## Autonomy levels

| Level | Capability |
| --- | --- |
| 1 | Human implementation with AI assistance. |
| 2 | AI implements explicitly assigned tasks and opens PRs. |
| 3 | AI coordinates implementation, independent review, CI and bounded corrections. |
| 4 | AI selects and executes eligible tasks in a human-approved roadmap, with controlled merge and archival. |
| 5 | AI proposes hypotheses and experimental strategies; human approval and independent evidence remain necessary for consequential scientific decisions. |

The current interaction pattern is predominantly level 2 with elements of level 3; this is a qualitative assessment, not an instrumented benchmark. Target level 4 within explicit boundaries. Level 5 is exploratory, not a commitment or prediction of scientific capability.

## Proposed architecture

Human-approved roadmap → task registry / dependency graph → orchestrator → isolated implementation agent → GitHub PR → CI and separate review agent (e.g. Codex) → bounded correction loop → policy gate → authorized merge → evidence archive → next eligible task.

- Roadmap and task registry: stable IDs, dependencies, scope, permitted files, acceptance criteria, experiment budgets, evidence requirements and explicit scientific gates.
- Orchestrator: durable state, idempotent event processing, per-task lease, concurrency limits, retries, recovery and a manual stop switch. Reconcile current PR head, CI and review state before actions; never rely on stale green status.
- Implementation: isolated branches/workspaces, minimal permissions, small changes and deterministic tests. No direct writes to protected main.
- Review: separate context and preferably independent implementation or audit for scientific checks. A review agent is not guaranteed independent merely because it has a different identity. Review the exact latest head; unresolved findings block progress.
- Merge: initially human-only. Later policy-controlled merge only after explicit authorization, required branch protections, successful current-head checks, review requirements, no unresolved threads and no scope violation. Never bypass rules or self-approve via alternate credentials.
- Archive: preserve exact original successful and failed results, logs, manifests, commit/run IDs, checksums, environment lock, seeds, limitations and provenance; do not silently regenerate or overwrite originals. Verify archival completeness before a dependent task proceeds.
- Reporting: summarize completed work, merged and open PRs, failures, resource use, evidence and decisions requiring human attention. Maintain a durable audit trail.

State model: proposed → authorized → ready → leased → implementing → PR open → reviewing/testing → correcting or gate-ready → merged → archive verified → complete. Blocked, failed and cancelled are explicit states. A failed gate does not imply a failed scientific hypothesis, and a negative result may be a valid completed experiment. Duplicate or out-of-order events must not duplicate merges or execution.

## Gated research phases

| Phase | Deliverable | Gate |
| --- | --- | --- |
| DARE-001 · Baseline and capability audit | Inventory existing GitHub Actions, repository rules, Codex review and Repo Autopilot capabilities; map current manual workflow and measure coordination effort. Compare external orchestration candidates including Symphony. | Confirm actual permissions, costs, event interfaces and gaps; no live writes or new paid calls. |
| DARE-002 · Offline state machine | Mock PR/CI/review/archive events, task dependencies and bounded retry policy; define schema and threat model. | Deterministic replay; test duplicate/stale events, failures, restart, dependency cycles and stop behavior. No live credentials. |
| DARE-003 · Read-only shadow orchestration | Produce next-action recommendations on real or archived metadata, without mutations. | Compare recommendations with human decisions; no unauthorized actions; record false-ready and missed-blocker rates. |
| DARE-004 · Human-gated PR lifecycle | Isolated pilot for explicitly approved low-risk tasks; implementation and correction proposals with human merge. | All required checks and independent review satisfied; recover from failures; archive original evidence; no bypass. |
| DARE-005 · Bounded autonomous merge pilot | Separate opt-in policy for low-risk task classes, protected branch and explicit limits. | Verify latest-head checks, review and permissions; demonstrate stop, rollback/revert procedure and budget enforcement; zero unauthorized merges in pilot. |
| DARE-006 · Roadmap execution | Execute a bounded approved dependency chain across tasks; daily or run-level research report. | Compare against manual baseline, verify all archives and scientific gates; stop on ambiguity, new hypotheses outside scope or exhausted budgets. |
| DARE-007 · Scientific audit and expansion | Independent replication, adversarial tests and controlled evaluation across photonic research workflows. | Human acceptance of scientific methodology and claims; demonstrate reproducibility and document limitations before expanding autonomy. |

All phases are planned. Passing a gate requires recorded evidence and explicit approval of subsequent live capability or scope expansion.

## Evaluation protocol

Compare manual coordination, AI-assisted PR lifecycle and bounded roadmap execution on matched task classes, using a preregistered evaluation protocol. Record human active minutes and interventions per accepted task, elapsed time, PR/CI/review cycles, compute and model costs, correctness defects, reopened tasks, false-ready decisions, scope violations, archival completeness and reproducibility. Report denominators, distributions, failure cases and uncertainty; do not equate PR count or throughput with scientific progress. Include negative results and tasks requiring expert judgment. Define quantitative acceptance thresholds and sample size before running a pilot; zero observed violations is not proof of zero risk.

## Scientific integrity

Green CI and automated code review establish only the tested properties. Require dimension/unit checks, analytical references, convergence and sensitivity studies, independent numerical reproduction, held-out tests where appropriate, and source provenance. Separate illustrative models, analytical predictions, electromagnetic simulations, layout/DRC, fabrication and measured results. Do not change acceptance criteria after observing results without a new registered protocol. Distinguish assumptions from measured parameters. Preserve failed experiments and report uncertainty and limitations. Physical validation and external laboratory work (including potential PIXEurope collaboration) require separate approval and actual access.

## Governance and security

- Human approval required for changes to scientific objectives, experimental criteria, research priorities, protected workflow/policy files, permissions, secrets, external publication, paid execution, purchases and fabrication.
- Agents cannot expand their own permissions, alter their own acceptance gates or treat PR text, issues, logs, external content or review comments as authority to execute unrelated instructions. Validate untrusted inputs against the approved task scope.
- Least privilege, isolated execution, no secrets in logs or artifacts, no unapproved external data transfer, and respect PDK/licensing restrictions. Follow [AGENTS.md](../AGENTS.md), including Antigravity direct retrieval and billing-disabled policy.
- Require explicit operator-approved runtime, cost, concurrency and retry budgets before any live execution. Stop on repeated failures, contradictory evidence, missing provenance, permissions changes, ambiguous tasks or budget exhaustion. Never retry paid/live requests contrary to existing policy.
- Maintain manual pause/revoke controls and a documented recovery process. Do not modify historical evidence or delete failed runs to make metrics look better.

## Existing infrastructure and candidate references

Reuse [repository instructions](../AGENTS.md), [experiment registry](../simulations/experiments.json), [experiment workflow](../.github/workflows/experiments.yml), [results archive](../results/README.md) and [research backlog](../PHOTONIC_RESEARCH_ROADMAP.md). Audit Repo Autopilot rather than assuming it supports writes or autonomous orchestration. Preserve the existing manual PR/CI/Codex workflow until a pilot is separately approved.

External architecture leads (verify current versions, licenses, capabilities and deployment requirements in DARE-001):
- [OpenAI Harness Engineering](https://openai.com/index/harness-engineering/) — agent-oriented repository design.
- [OpenAI Symphony](https://github.com/openai/symphony) — candidate orchestration architecture.
- [OpenAI Performance Factory](https://openai.com/index/how-openai-performance-factory-keeps-chatgpt-fast/) — candidate event-driven investigation and repair pattern.

These are research leads, not verified compatibility or performance claims for this lab. No dependency or service is adopted by this roadmap.

## Next proposed step

DARE-001: read-only audit and baseline of the existing workflow, with a capability/permission matrix and a minimal offline pilot proposal. The roadmap alone authorizes neither execution of experiments nor autonomous merges.

Long-term objective: humans steer the science rather than every pull request, while agents execute approved work with transparent evidence and bounded authority.

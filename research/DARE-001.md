# DARE-001 · Baseline and capability audit

Date: 2026-11-28. Status: initial read-only assessment recorded; live readiness gate remains blocked. No model session, orchestration service, experiment dispatch, credential change or paid resource was initiated by the audit. Documentation PR is the only proposed repository mutation.

## Observed repository baseline

Main after [PR 332](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/pull/332), merge commit 8e0f98169a9d01964331b888782516495bab7976. Reviewed [DARE roadmap](DARE-ROADMAP.md), [agent instructions](../AGENTS.md), [experiment workflow](../.github/workflows/experiments.yml) and [results index](../results/README.md).

The experiment workflow uses ubuntu-24.04, read-only contents permissions, a path-filtered PR trigger, a manual dispatch option, a registry selector, locked environments and bounded job timeouts. New PR pushes cancel obsolete experiment runs. Artifact upload uses always() for individual result jobs; the bundle job excludes cancellation and requires successful selection. Therefore cancelled or incomplete runs may lack results, and a missing bundle is not evidence of success. Existing permanent results and provenance conventions should be reused. Documentation-only PRs need not run photonic experiments; distinguish skipped/not-applicable checks from executed checks.

Repo Autopilot connector exposes read-only PR status, CI details, changed files, findings, recent workflow runs and waiting-on-human views. Its observed status includes exact head SHA, readiness, CI completeness, Codex state and unresolved findings. It is an observation channel, not a demonstrated scheduler, credential broker or write API. Separate GitHub connector can perform authorized branch/file/PR/merge actions; this does not establish that a future DARE worker has those permissions. Actual branch protection configuration and worker permissions were not retrieved.

## Small descriptive manual baseline

Two documentation PR snapshots from Repo Autopilot on 2026-11-28 (UTC):

| PR | Opened | Codex review completed | Merged | Open to merge | Review to merge |
| --- | --- | --- | --- | --- | --- |
| [331](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/pull/331) | 04:00:52 | 04:02:10.938 | 04:04:24 | 212 s | 133.062 s |
| [332](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/pull/332) | 04:20:48 | 04:22:02.698 | 04:23:07 | 139 s | 64.302 s |

Both had successful reported CI, no reported Codex findings and human merge authorization. Mean open-to-merge elapsed time: 175.5 s; mean review-to-merge elapsed time: 98.682 s. These are elapsed intervals, not human active time or causal estimates of automation savings. Sample n=2, documentation only, selected for convenience; no representative baseline for simulation-heavy or failed PRs. Human active minutes, compute costs, review retries and full check timing are unknown. Future evaluation must prospectively record those metrics on matched task classes, including failures and blocked tasks.

## Dated capability, quota and cost matrix

Public documentation consulted 2026-11-28; account-specific settings were not accessed. Unknown is a blocking state under Zero Additional Cost Policy.

| Resource | Evidence / capability | Cost and quota status | Gate |
| --- | --- | --- | --- |
| Symphony | Apache-2.0 Elixir prototype; GitHub Issues adapter; per-issue workspace; Codex App Server | No software license fee; runtime and dependencies not verified on target host | Offline design only |
| Codex App Server | Official account authentication and rate-limit interfaces; ChatGPT login and API-key paths distinct | Plus eligibility generally documented; actual remaining allowance, credits, billing fallback and account compatibility unknown | Block live session |
| GitHub Issues | Symphony adapter polls configured repository; required labels can restrict dispatch | Account-specific access, API limits and authorization not checked | Block live tracker |
| GitHub Actions | Existing workflow on ubuntu-24.04; public standard hosted runners generally free per GitHub docs | Actual visibility/billing, runner class, storage and applicable limits not independently verified | No new experiment dispatch |
| Codex PR review | Observed clear reviews on PRs 331 and 332 | Review allowance and potential credit usage unknown | No new autonomous review requests |
| Repo Autopilot | Read-only observations verified | Hosting allowance, rate limits and integration API contract unknown | Existing read-only usage only |
| Permanent archive | Existing results and provenance convention; workflow artifact bundle | Storage limits, completeness and retention per run require checks | Mock archive verification |
| Execution host | Symphony needs a running process and Codex/git; binaries documented for Linux/macOS | No authorized zero-cost persistent host identified; electricity/resource use not zero | Block deployment |

Sources: [Symphony repository](https://github.com/openai/symphony), [Elixir README](https://github.com/openai/symphony/blob/main/elixir/README.md), [SPEC](https://github.com/openai/symphony/blob/main/SPEC.md), [Codex App Server](https://learn.chatgpt.com/docs/app-server), [Codex plan usage](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan), [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions). Upstream main is mutable; exact release/commit and compatible Codex version must be pinned before implementation or deployment. No account-specific zero-cost claim is made.

## Symphony fit and gaps

The upstream README explicitly labels the Elixir implementation an evaluation prototype. GitHub Issues is a documented adapter, so a separate Linear subscription is not required by the proposed architecture. Candidate labels and active states can filter dispatch, but are not an authorization boundary: the raw github_api tool can reach resources allowed by its host token. The blocked-issue map is in memory and restarts can redispatch still-active tasks. A streaming silence timeout is not a wall-clock budget. These gaps require a durable external authorization/cost gate, least-privilege scoped credentials, explicit method/path allowlists, persistent leases and hard runtime limits. Do not copy upstream example settings, landing skills or live end-to-end tests into production.

Compare two candidates: (A) hardened Symphony adapter behind DARE policy and durable state; (B) small local deterministic DARE scheduler with mock interfaces, later connecting to supported Codex and GitHub interfaces. Choose B for DARE-002 to validate invariants independently of model/provider availability; retain A as a future integration candidate. No dependency adoption yet.

## Proposed DARE-002 offline scope

Use standard-library-only Python, synthetic fixture events and temporary local state, no network, credentials, subprocess model calls or live GitHub writes. Model task ID, approved scope, dependency IDs, head SHA, CI applicability and completeness, current-head review state, cost entitlement evidence, stop flag, lease and archive manifest. Separate decision output from execution; no mutation adapter. Default deny unknown or stale evidence. Test duplicate/out-of-order events, dependency cycles, stale head, skipped required checks, unresolved findings, exhausted/unknown quota, paid fallback, restart with persisted stop/blocked state, bounded retries and incomplete archival. Require deterministic replay and zero forbidden action recommendations in specified fixtures; this is a software test, not proof of safe deployment. Human merge remains mandatory.

## Open gates and disposition

DARE-001 initial evidence is sufficient to propose a mock-only next step, not to pass the live readiness gate. Before any live pilot, obtain operator-approved evidence of actual Plus allowance and billing settings, supported auth, GitHub permissions/protection and quotas, Codex review allowance, cost-free host, storage and stop/recovery controls. Do not collect secrets in research files. If these cannot be confirmed, remain offline. Further read-only checks and prospective manual baseline instrumentation remain open. No autonomous execution or paid service authorized.

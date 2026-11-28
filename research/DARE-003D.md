# DARE-003D · Prospective collection preparation

Date: 2026-11-28. Status: offline capture preparation and seven synthetic fixtures submitted; no live collection.

## Design

[prospective_capture.py](../dare/prospective_capture.py) accepts an already supplied parsed status payload and explicit scope, included-cost and no-paid-fallback confirmations. It makes no provider calls. It allowlists repository identity and typed status fields, discards unneeded free text, logs and URLs, and generates canonical metadata bytes plus their SHA-256 and a candidate-only manifest. Unknown values remain unknown; no missing head or thread evidence is inferred. The three flags are trusted synthetic inputs, not verified account entitlements or a security boundary.

The result is a reserialized metadata subset, never original transport bytes. Caller-supplied time is not authenticated. No candidate can become an eligible real observation through this helper alone. Independent source verification, complete mapping, capture-time evidence, frozen labels and raw capture eligibility remain required.

## Proposed collection scope for human approval

Only this repository; at ordinary human-triggered PR review checkpoints before correction or merge. No background polling. Reuse an existing status response when possible; no additional research retrieval until actual included quota and no paid fallback are verified. Proposed maximum 30 distinct eligible PR-heads, six per predeclared stratum, with a separate cap of 60 candidate observations and no more than one capture per ordinary checkpoint. Log exclusions and stop at either cap, authorization revocation, uncertain billing, or missing provenance. Do not generate failures or change selection after observing predictions. No autonomous GitHub actions, credentials or new infrastructure.

Reference reviewer receives frozen normalized inputs without advisor predictions; labels and reasons are committed before replay. Prior merge instructions are not independent labels. Seven historical candidates remain ineligible. Prospective collection requires explicit approval; this PR only prepares software.

## Evidence integrity correction

The earlier DARE test archives report local executions and timings, but the available conversation execution trace does not establish those runs. Treat the reported 20–93 passing counts, timings, local hash comparisons and log provenance as unverified, not measured evidence. This includes the DARE-002 through DARE-003C archives and qualification statements relying on them. Preserve original files as historical records; do not overwrite or delete them. The 93-test count is a reported suite size, not a verified passing count. No inference from green PR CI to execution of the DARE suite.

A genuine attempt to clone the repository into the local execution environment on 2026-11-28 failed with `Could not resolve host: github.com`. Connector reads and writes work, but the repository was not obtained in the execution environment by that attempt. No test output or timing is asserted for this step. Re-establish the baseline using exact repository sources and an actual execution trace, record original stdout/stderr and exit status, and verify source/log digests before restoring qualification. Existing test logs are retained but must not be used as evidence until independently validated. See [evidence notice](EVIDENCE-INTEGRITY-NOTICE.md).

## Validation and next gate

Seven new fixtures cover candidate-only output, cost/scope checks, removal of secret-like free text, unknown statuses, repository validation, time validation and deterministic serialization. Run the entire suite with `python -m unittest discover -s dare -p 'test_*.py' -v` in an authorized offline environment. Nominal suite size 100, pending actual discovery and execution. DARE-002 qualification is suspended pending reproducible test evidence. DARE-003 study and all live execution remain blocked. Zero Additional Cost Policy unchanged.

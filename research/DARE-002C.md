# DARE-002C · Evidence and execution gates

Date: 2026-11-28. Status: 35/35 existing tests passed in isolated local execution; new evidence-gate implementation and 16 fixtures submitted, execution pending. No live readiness release.

## Verified baseline

[Actual test output](evidence/dare-002b/baseline-35.log) and [provenance](evidence/dare-002b/provenance.json) preserve the local Python 3.13.5 run against all four source files from merge commit 899a825ada66a6b80f5a0d9251223f02c013266b. Each reconstructed file matched its fetched Git blob SHA before execution. Exit code 0, 35 tests in 0.027 s. Not a GitHub Actions run. Preserve previous evidence unchanged.

## Implementation

[EvidenceGate](../dare/evidence_gate.py) wraps the legacy decision engine for offline evaluation. It derives archive flags from task ID, current head, configured run ID, required manifest entries and actual SHA-256 verification; a legacy archive Boolean alone cannot release a dependency through this interface. Review evidence must match the current head, contain the exact configured required check inventory, be marked complete and fall within a synthetic 300-second freshness window. Missing, skipped, pending or invalid checks cannot yield a human merge request. Cost evidence must also be fresh, with the original zero-cost gates still enforced.

Correction reservation increments a bounded counter and sets a single-writer lease. A second reservation is blocked while leased. Existing snapshot persistence can preserve both fields. No automatic release, retry execution or lease recovery is implemented: a future explicit reconciliation protocol must establish fresh evidence before releasing a lease. Three attempts block further implementation/correction proposals but do not prevent requesting human merge if all gates pass. No merge adapter exists.

## Test protocol

[16 new fixtures](../dare/test_evidence_gate.py) cover current-head and fresh evidence, future timestamps, incomplete or skipped checks, open threads, archive identity mismatch and tampering, ignoring legacy archive flags, correction reservation, persisted counters and the retry ceiling. Run all 51 tests with `python -m unittest discover -s dare -p 'test_*.py' -v` in an authorized offline environment. Archive original output and source identities before claiming a pass.

## Limits

Trusted synthetic inputs only. The wrapper is not a mandatory enforcement boundary: the legacy engine remains callable separately. The clock, check inventory, archive policy and evidence inputs are not authenticated provider data; freshness alone does not establish authenticity or prevent rollback. Archive checks inherit DARE-002B static-directory and single-writer limitations. No transitive dependency revalidation, automatic recovery supervisor, explicit non-applicable-check policy, actual scoped file verification, provider billing verification or live adapter. The 300-second window is a test-design assumption, not a validated production threshold. Leases have no expiry; fail closed until explicit reconciliation. No DARE-003 release. Zero Additional Cost Policy unchanged.

Next: execute and archive all 51 tests, adversarially audit the wrapper and strengthen the mandatory offline interface and recovery protocol before proposing shadow orchestration.

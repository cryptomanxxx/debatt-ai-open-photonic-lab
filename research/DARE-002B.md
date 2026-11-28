# DARE-002B · Validation and persistence

Date: 2026-11-28. Initial baseline executed: 20/20 tests passed. New persistence and archive fixtures submitted; their execution evidence is pending. No live readiness release.

## Original baseline evidence

[Raw test output](evidence/dare-002/baseline.log) and [provenance](evidence/dare-002/provenance.json) preserve the local isolated run against the exact two source blobs from merged PR 334. Both reconstructed sources matched Git blob hashes before execution. Python 3.13.5, 20 tests in 0.001 s, OK. This is a local run, not CI or provider validation.

## New implementation

[Persistence module](../dare/persistence.py) implements strict snapshot parsing (including duplicate keys, primitive types, enum values, counters and dependency graph), atomic same-directory replacement with file and directory fsync, and explicit failure on missing or corrupt state. No automatic initialization on load failure. The archive helper verifies the expected manifest entries and SHA-256 of local files; rejects missing, tampered, traversal and symlink entries. Expected file set and manifest are trusted inputs, not inferred from untrusted artifacts.

[15 additional fixtures](../dare/test_persistence.py) cover round-trip, persistent stop/quota, corrupt/missing state, malformed type, duplicate key, failed replacement, inconsistent archive state and integrity checks. Run `python -m unittest discover -s dare -p 'test_*.py' -v` in an authorized offline environment; archive output and revision before claiming their results.

## Limits and next step

Single trusted writer and static trusted fixture directory only; no concurrent lock, rollback protection, external event authenticity, actual recovery supervisor or cryptographic manifest authentication. The helper does not enumerate unexpected files in the directory, and does not verify ancestor symlinks or prevent filesystem races. It checks declared required files only. It is not yet wired to the decision engine's archive flag. A directory fsync failure after replacement may leave the new snapshot visible; stop on ambiguous persistence outcomes. Linux/POSIX local filesystem semantics assumed; no cross-platform crash guarantee. No proof of power-loss recovery. Next: execute and archive new tests, bind archive evidence to task/run/head, enforce freshness and complete required checks, and implement lease/retry accounting. Full DARE-002 gate remains open; no DARE-003/live authorization. Zero Additional Cost Policy unchanged.

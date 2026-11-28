# DARE-003B · Historical dataset and replay

Date: 2026-11-28. Status: replay implementation and nine synthetic tests submitted; execution pending. Historical study not started.

## Dataset contract

Keep original authorized capture bytes in a separate immutable raw archive with SHA-256, source identifier, collection time and capture provenance. Normalize into a JSON list of envelopes: id, stratum, record (DARE-003A schema), now (replay decision time), raw_sha256. Maintain independent human reference labels in a separate JSON object keyed by id, each with label, reviewer and reason. Freeze both before revealing outputs by recording the canonical SHA-256 digest of {"records": records, "references": references} in an independently reviewed commit. Preserve original raw bytes, normalization mapping and reference revisions; never overwrite prior results. Reviewer identifiers may be pseudonymous. Do not include secrets.

[Replay evaluator](../dare/replay_dataset.py) rejects duplicate PR-head identities, missing or extra labels, invalid hashes and mismatched freeze digests. Computes agreement, confusion matrix, false-ready and missed-blocker counts and rates, abstentions, stratum coverage and repeatability. Undefined denominators produce null, not zero. Real and synthetic groups remain separate. The evaluator does not itself authenticate raw captures, verify their bytes, confirm human independence or prevent caller relabelling; those are manual eligibility gates prior to replay. It cannot grant operational permission. No provider or network integration.

## Historical inventory

[Candidate inventory](evidence/dare-003b/historical-inventory.json) indexes six previously observed Repo Autopilot responses (PRs 335–340), all reporting clean readiness immediately before human-requested merges. This is a transcribed index, not original raw evidence. Capture timestamps and explicit CI head binding are not established by this index. Existing merge requests are not blinded reference labels. Consequently zero eligible real observations have been frozen, and no study metrics have been computed.

| Stratum | Target | Candidate index | Eligible |
| --- | ---: | ---: | ---: |
| Clean ready | 6 | 6 | 0 |
| CI pending | 6 | 0 | 0 |
| CI failure | 6 | 0 | 0 |
| Review findings | 6 | 0 | 0 |
| Incomplete/stale/conflicting | 6 | 0 | 0 |
| Total | 30 | 6 | 0 |

No new live status retrieval was performed for this inventory. Do not reconstruct historical states from present merged state or fabricate missing observations. If sufficient original captures cannot be recovered, report shortfall and propose a separately approved prospective read-only collection protocol; do not silently substitute synthetic observations.

## Software validation

[Nine new synthetic tests](../dare/test_replay_dataset.py) cover empty denominators, synthetic exclusion, false-ready/missed blocker accounting, freeze mismatch, duplicate PR heads, missing/unmatched labels, malformed hashes and deterministic replay. Run all 85 tests offline and archive actual output and source identities before claiming a pass. Existing DARE-003A evidence remains unchanged.

## Next step

Verify software tests, implement raw-byte integrity validation against a local manifest, establish actual capture timestamps and field mappings, and freeze eligible records and independent reference labels before evaluation. No live reader, polling, agent launch, mutations or paid services. Stage B remains separately authorized only. Zero Additional Cost Policy unchanged.

[DARE-003C](DARE-003C.md) records the verified 85-test baseline, 93-test candidate run and seven-candidate inventory. Real evaluation remains pending.

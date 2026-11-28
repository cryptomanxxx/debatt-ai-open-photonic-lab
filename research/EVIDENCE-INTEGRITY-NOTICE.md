# DARE evidence integrity notice

2026-11-28. The available execution trace does not substantiate earlier claims of local Python execution, passing test counts, elapsed times, or local source/log hash verification in DARE-002 through DARE-003C. Treat these claims and associated logs/provenance as unverified. Retain all original archive files unchanged for audit. This notice supersedes their evidentiary status, not their bytes. Green GitHub PR status does not independently establish that the DARE tests ran.

Requalification requires an actual execution of exact revision sources, captured original output and exit status, independently checked source identities and log digests. Until then, suspend the offline qualification and do not advance to live collection or autonomous actions. A local Git clone attempt failed because github.com could not be resolved. No test run is claimed for DARE-003D. See [DARE-003D](DARE-003D.md).

## Subsequent evidence: DARE-003E

A new actual local execution at revision 7e9df3b0a8d5e86e94e2370b1472faaf831dd6f7 passed all 100 tests across the 18 known Python files, with exact source blob checks and archived original log/provenance blob checks. See [DARE-003E](DARE-003E.md). This supports scoped offline software requalification pending human review; it does not retroactively authenticate the older records. Independent reproduction and all live gates remain outstanding.

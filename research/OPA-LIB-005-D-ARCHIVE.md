# OPA-LIB-005-D — Permanent negative-evidence archive preparation

Two separately successful, reviewed CI artifacts need permanent preservation:

| Analysis | Original PR / CI run | Artifact | ZIP size | SHA256 |
|---|---|---|---:|---|
| D1 complete 4×4 complex S screen | [PR244](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/pull/244) / [44792693356](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44792693356) | 14656862431 | 7569 bytes | `76892cda933dd3831c809aa14adb622b7fe19ae95fa5131a9fa250e6ced6cb0f` |
| D2 negative decision and full replay | [PR245](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/pull/245) / [44794454729](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44794454729) | 14656894199 | 8921 bytes | `a5bd631aceb4171d5079f960b79433a6b4f68858aada83b59ce5e25ed532e3a6` |

These GitHub Actions artifacts expire on **2027-02-18**. [Original report and artifact manifest](../components/comparison/lib005-bdc-archive-source.json) pins the original successful run, job, artifact IDs, sizes, SHA256 digests, head commits and exact CI-log reports. [Archive verifier](../research/archive_lib005_bdc.py) validates original ZIP identity, safe member set and CRC, full original JSON against CI logs, complete replay of reviewed D1/D2 scripts and every spectral CSV cell. Original ZIPs and extracted original output files, plus machine-readable provenance with checksums, are planned for `components/comparison/lib005-bdc-evidence/`. Archive output will require separate human review before merge. The replay is **not an independent estimator** and never corrects or renormalizes the source.

### Required two-stage archive

1. Merge the archive-preparation PR after [preflight](../.github/workflows/opa-lib005-bdc-archive-preflight.yml) and Codex approval. This PR does not contain the final artifact bytes.
2. On main, manually run [OPA archive LIB005 BDC negative evidence](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/workflows/opa-archive-lib005-bdc.yml) with `confirm_archive=true`. The action verifies the original artifacts and pushes **only** `research/opa-lib005-bdc-evidence`. A branch collision fails closed.
3. Open a separate archive-review PR, verify Git-staged exact bytes with [permanent audit](../.github/workflows/opa-lib005-bdc-evidence-audit.yml), and merge only after CI and Codex clear.

No physical measured complex S, calibrated cell geometry, optical gain or process/foundry qualification is established. The **negative** result `50/51` at `max_sigma_global=1.0068756797677312`, classified `quarantined_nonpassive`, remains unchanged. Preserve both original ZIPs and both CI results indefinitely under version control.

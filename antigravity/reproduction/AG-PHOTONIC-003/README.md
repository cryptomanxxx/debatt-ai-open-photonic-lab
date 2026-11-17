# AG-PHOTONIC-003 — source recovery and independent reproduction

Status: **ORIGINAL REPLAY MATCHED — structured output reproduced; independent physics validation pending.**

## Evidence and provenance

- Completed manager run: [43993099721](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/43993099721).
- Archive run: [43993579236](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/43993579236).
- Scientific export: [43993882093](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/43993882093), artifact 14289790174, ZIP SHA-256 `3790bc14c165c7ae0550a8264d82c88fcf75f24407c75aa1d4cf0160826cb5fc` (GitHub metadata).
- Archived encrypted response SHA-256: `a6963af6d467ad43ca97fd465b0bb6f1db69fad88ce4ca7b898f504c6aea950d`.
- Export schema 2, completed, 14 steps. No complete workspace source or report in final export.

## Recovered snapshot and archival

- Direct snapshot: [44074735184](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44074735184), source artifact 14325015236, ZIP SHA-256 `ff289ebdc02161598cc4a2655796c8e4ad4df537095b3f84129651f44d88f04d`.
- TAR: 254464 bytes, 25 entries, SHA-256 `e89d34601d4acd5642c915ad59c4ed9a67e3e9e2942a1747f4b25e012ee05cc7`; encrypted artifact 14323698575.
- Seven source/report files: 164850 bytes total; no missing or withheld files. All per-file hashes independently checked against the downloaded ZIP and pinned in import_snapshot.py.
- The source ZIP expires November 24, 2026; archive promptly. Use **AG003 archive verified original files** on main with confirm_archive enabled. This copies verified bytes to `original/` on a new review branch, verifies the staged Git bytes, and pushes only that branch; no Google calls and no execution of recovered code. Open a separate PR to review the exact original files.
- See [PRELIMINARY_AUDIT.md](PRELIMINARY_AUDIT.md) for observed source defects and reproduction requirements.

## Recovery policy and historical procedure

### Preferred route: direct workspace download

Use **AG003 direct workspace snapshot** on main with explicit free-project confirmation. It decrypts the original completed manager checkpoint (43993099721) to obtain the existing environment ID and downloads the current workspace with one GET to the documented [Environments Files API](https://ai.google.dev/gemini-api/docs/agent-environment#download-a-directory-as-a-tar-archive). No interaction submission, agent execution or polling. The deprecated full-snapshot endpoint is not used. The full TAR is encrypted using the existing GEMINI_API_KEY with the domain-separated cipher input `workspace-snapshot-v1:` plus the key. Public diagnostics report only fixed expected names, sizes, hashes and counts. Public export of seven allowlisted screened files requires separate explicit consent and a complete set. No arbitrary archive extraction or execution. The 64 MiB archive limit and exact root/workspace paths are deliberate fail-closed limits. A current snapshot cannot prove that previous follow-up interactions did not modify files; review provenance before reproduction. Do not use model-based recovery again unless direct retrieval has been assessed.

### Historical model-based recovery (retained for provenance only)

**Do not execute the historical instructions below as the default recovery method.** Direct Files API retrieval succeeded in run 44074735184. The later agent-mediated continuation was cancelled, with 120225 reported tokens and no complete manifest, as recorded in diagnostics run [44072988533](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44072988533). Use the direct method first; the following commands document earlier attempts only.

Recover exactly these existing files from the original environment, without rerunning or editing them:
`params.py`, `physics_model.py`, `sweep.py`, `circuit_sim.py`, `train_sim.py`, `run_all.py`, `report.json`. Record byte lengths and SHA-256; obtain dependency versions and any input files required to execute. Do not publish credentials or interaction identifiers. Preserve files under `original/` after review; do not reconstruct missing code from the summary. See recover_workspace.py for the explicit, separate source-export request. It requires the existing encrypted checkpoint and an operator-confirmed free project; it does not start a fresh environment.

The original procedure was to manually dispatch **AG003 source recovery** on main with mode `submit` and an empty recovery run ID, only after verifying free-tier eligibility and billing disabled. If the job is still active or a GET failed, use mode `retrieve` with the previous recovery workflow run ID; this never submits a new interaction. A completed recovery can be exported without any new Google request. Both modes require the original manager checkpoint (run 43993099721) to remain available. Separate public-export confirmation is required. The resulting artifact includes `recovery-metadata.json` with screened dependency information, energy-audit evidence and file integrity records. Automated screening and matching agent-supplied digests do not prove provenance or absence of arbitrary secrets; review before committing.

### Recovery continuation after the incomplete 100k request

Run [44058629986](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44058629986) stopped with status incomplete. [Offline diagnostics](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44065743936) reported 179322 total tokens (177947 input), same environment, no complete manifest, and unknown incomplete reason. This supports a budget hypothesis but does not prove the cause.

The subsequent historical procedure used AG003 source recovery with mode `continue`, recovery run ID `44058629986`, token budget `1000000`, and explicit free-project confirmation. This is one new source-only follow-up to the incomplete recovery in the original environment, not a GET-only retrieval. The requested budget is not a hard cost cap; verify billing is disabled. Do not repeat submit if the new interaction is active; use retrieve with its recovery run ID. No automatic POST retries.

The prompt requests a read-only code execution that emits the complete base64 manifest directly as a tool result, followed by a short final response. The extractor accepts successful code-execution results and legacy model-output manifests, checks all recognized candidates, refuses conflicting bytes and retains screened metadata. These are agent-reported bytes, not independently attested provenance. Tool-output truncation or unavailable workspace files can still prevent export; do not repair or invent missing bytes.

## Agent-reported comparison targets (not independent measurements)

- 330960 analytic configurations; 325 feasible before convergence gate; 330635 rejected.
- CFG-0100, independent-laser MZI, 6 bit, 1.5405 system TOPS/W, 5.962 chip TOPS/W.
- Zero convergent comb-powered feasible designs; electronic baseline 3.5 TOPS/W modeled.
- Ideal SVD-MZI relative error 2.3156428487523713e-15; 16-channel nonideal RMSE 0.0869.
- Three seeds 42, 137, 2025; FP32 94.50%, 8-bit hybrid 93.05%, 6-bit hybrid 91.50%, 4-bit hybrid 79.72%.
- Original environment reported Python 3.12.3, NumPy 2.5.4, Pandas 3.1.1; verify rather than silently substituting versions.

## Energy audit (mandatory before accepting results)

Final export step 4: low-loss test failed with feasible=true and path_loss_db=18.63; all_passed=false. Step 11 reports all_passed=true. The intervening source changes are absent from this export. Obtain the previous and final implementation where possible; inspect loss contributions, units, fixed versus variable losses, and the exact assertion. Compare identical configurations with only a specified passive-loss parameter changed; verify non-increase in path loss and a strict decrease when the changed component contributes nonzero loss. Check power conservation using unrounded component values and explicit tolerances, MAC/op accounting and system versus chip boundaries. A relaxed assertion alone is not scientific validation. Preserve failures.

## First independent replay

The archived files were merged in PR #100; archive workflow 44076232809
verified their bytes before and after staging. Use **AG003 isolated original replay**
on main with explicit confirm_replay. The workflow verifies all original hashes,
builds a container using Python 3.12.3 and the reported NumPy 2.5.4 and Pandas
3.1.1, and copies only the six Python files into a disposable /workspace.
The container has no network, no credentials, no repository mount, an
unprivileged user, a read-only root filesystem and bounded resources.
Original report.json is not copied to the writable workspace, so it cannot
masquerade as a replay result. If exact dependencies are unavailable, the
build fails visibly; no silent substitution. The base image is version-tagged,
not digest-locked, and transitive dependencies are not fully pinned; this is a
first replay, not bit-identical environment reconstruction.

Artifacts preserve build and execution logs, image ID, exit code, replayed
report and comparison.json when available. The comparator checks the full
structured sweep, parameter, circuit, training (all seeds), and ranking
sections, with exact categorical/integer matches and float tolerance
relative 1e-8 / absolute 1e-10. Only explicitly named runtime fields are
ignored within those sections. Environment versions are compared separately;
narrative and limitations prose are excluded. Mismatches fail the comparison
but retain evidence. A successful replay is not a validation of the model
or a correction of the known issues in PRELIMINARY_AUDIT.md.

## Verified replay result (2026-11-17)

[Run 44090316677](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44090316677)
completed successfully at commit `c682278bcace3eb3efd4eaba399ecda3311f1d79`.
[Artifact 14331995499](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44090316677/artifacts/14331995499)
contains six files; downloaded ZIP SHA-256 independently checked:
`96699acf4a2338bfbb0fe9dc92c8f3964f620f6d3a95d08c6a1522f6c94b84ce`.
All six file digests are pinned in archive_replay.py. Exit code 0.
The comparison found 1882 exact matches, 26 floats within tolerance,
zero differences and two explicitly ignored runtime values. Python 3.12.3,
NumPy 2.5.4 and Pandas 3.1.1 match. The replay build log additionally
records python-dateutil 4.0.0 and tzdata 2026.6; these are replay versions,
not verified original-environment versions. Replay pipeline time was
43.659 s versus original 78.294 s; this is not a controlled performance
benchmark.

| Structured result | Replayed value |
|---|---:|
| Analytic configurations | 330960 |
| Feasible / rejected | 325 / 330635 |
| Best convergent candidate | CFG-0100 |
| System / chip TOPS/W | 1.5405 / 5.962 |
| Modeled electronic reference TOPS/W | 3.5 |
| Digital baseline final accuracy | 94.50% |
| 8-bit / 6-bit / 4-bit hybrid final accuracy | 93.05% / 91.50% / 79.72% |

The original low-loss validation still passes with nominal path loss null
and low-loss path loss 18.63 dB. This is a reproduced weakness, not a valid
monotonic comparison. All preliminary audit issues remain open.

To preserve the exact evidence, manually dispatch **AG003 archive verified
replay** on main with confirm_archive enabled. It checks artifact identity,
all file hashes, independently recomputes the comparison, and verifies
staged Git bytes before pushing a new review branch. No agent code is run
and no Google requests are made. Review and merge the archive branch
separately. Do not replace original/report.json.

## Next independent scientific investigation

Establish a separate energy-audit implementation with independently
derived loss and power identities, fixed-configuration passive-loss
comparisons (including rejected configurations), unrounded component
accounting, and matched system boundaries. Preserve negative results and
never alter the archived original/replay evidence. Only after the
independent audit should corrected architecture rankings be interpreted.

## Reproduction acceptance

1. Review recovered code before executing; run without credentials, network or write access to original sources, with pinned dependencies.
2. Execute original pipeline and record stdout, exit code, versions, hashes and machine-readable output separately from original report.
3. Independently implement and test the sweep, energy accounting and seeded training metrics; compare counts and numerical results with documented tolerances, including negative results.
4. Do not equate reproduction of analytical/circuit results with electromagnetic validation or hardware measurements. Do not claim large-model training or measured efficiency.

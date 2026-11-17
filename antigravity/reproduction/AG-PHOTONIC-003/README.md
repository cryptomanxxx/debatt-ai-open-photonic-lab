# AG-PHOTONIC-003 — source recovery and independent reproduction

Status: **BLOCKED — original workspace files not yet recovered; no independent result.**

## Evidence and provenance

- Completed manager run: [43993099721](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/43993099721).
- Archive run: [43993579236](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/43993579236).
- Scientific export: [43993882093](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/43993882093), artifact 14289790174, ZIP SHA-256 `3790bc14c165c7ae0550a8264d82c88fcf75f24407c75aa1d4cf0160826cb5fc` (GitHub metadata).
- Archived encrypted response SHA-256: `a6963af6d467ad43ca97fd465b0bb6f1db69fad88ce4ca7b898f504c6aea950d`.
- Export schema 2, completed, 14 steps. No complete workspace source or report in final export.

## Recovery

Recover exactly these existing files from the original environment, without rerunning or editing them:
`params.py`, `physics_model.py`, `sweep.py`, `circuit_sim.py`, `train_sim.py`, `run_all.py`, `report.json`. Record byte lengths and SHA-256; obtain dependency versions and any input files required to execute. Do not publish credentials or interaction identifiers. Preserve files under `original/` after review; do not reconstruct missing code from the summary. See recover_workspace.py for the explicit, separate source-export request. It requires the existing encrypted checkpoint and an operator-confirmed free project; it does not start a fresh environment.

After merge, manually dispatch **AG003 source recovery** on main with mode `submit` and an empty recovery run ID, only after verifying free-tier eligibility and billing disabled. If the job is still active or a GET failed, use mode `retrieve` with the previous recovery workflow run ID; this never submits a new interaction. A completed recovery can be exported without any new Google request. Both modes require the original manager checkpoint (run 43993099721) to remain available. Separate public-export confirmation is required. The resulting artifact includes `recovery-metadata.json` with screened dependency information, energy-audit evidence and file integrity records. Automated screening and matching agent-supplied digests do not prove provenance or absence of arbitrary secrets; review before committing.

## Agent-reported comparison targets (not independent measurements)

- 330960 analytic configurations; 325 feasible before convergence gate; 330635 rejected.
- CFG-0100, independent-laser MZI, 6 bit, 1.5405 system TOPS/W, 5.962 chip TOPS/W.
- Zero convergent comb-powered feasible designs; electronic baseline 3.5 TOPS/W modeled.
- Ideal SVD-MZI relative error 2.3156428487523713e-15; 16-channel nonideal RMSE 0.0869.
- Three seeds 42, 137, 2025; FP32 94.50%, 8-bit hybrid 93.05%, 6-bit hybrid 91.50%, 4-bit hybrid 79.72%.
- Original environment reported Python 3.12.3, NumPy 2.5.4, Pandas 3.1.1; verify rather than silently substituting versions.

## Energy audit (mandatory before accepting results)

Final export step 4: low-loss test failed with feasible=true and path_loss_db=18.63; all_passed=false. Step 11 reports all_passed=true. The intervening source changes are absent from this export. Obtain the previous and final implementation where possible; inspect loss contributions, units, fixed versus variable losses, and the exact assertion. Compare identical configurations with only a specified passive-loss parameter changed; verify non-increase in path loss and a strict decrease when the changed component contributes nonzero loss. Check power conservation using unrounded component values and explicit tolerances, MAC/op accounting and system versus chip boundaries. A relaxed assertion alone is not scientific validation. Preserve failures.

## Reproduction acceptance

1. Review recovered code before executing; run without credentials, network or write access to original sources, with pinned dependencies.
2. Execute original pipeline and record stdout, exit code, versions, hashes and machine-readable output separately from original report.
3. Independently implement and test the sweep, energy accounting and seeded training metrics; compare counts and numerical results with documented tolerances, including negative results.
4. Do not equate reproduction of analytical/circuit results with electromagnetic validation or hardware measurements. Do not claim large-model training or measured efficiency.

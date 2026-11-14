# OPA-ID-003 — Fabrication-tolerant directional coupler

Original results of [PR #56](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/pull/56), run [43639010470](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/43639010470). The earlier serial run 43633041220 was cancelled at its time limit and is not the source.

| Metric (60 px/µm) | Nominal | Robust |
|---|---:|---:|
| Straight interaction length (µm) | 2 | 6 |
| Nominal gap (nm) | 200 | 350 |
| Nominal transmission | 68.05% | 79.12% |
| Minimum transmission across tested conditions | 57.72% | 73.75% |
| Worst split error (percentage points) | 25.57 | 22.73 |
| Maximum reflected guided-mode power | 0.00612% | 0.00343% |
| Worst training objective error | 0.33251 | 0.29634 |
| Worst held-out objective error | 0.35898 | 0.29891 |

All 8 mandatory checks passed; 5 of 7 research targets achieved. The robust geometry improves worst-case objective error on training and held-out scenarios, but does not reach the preregistered >95% minimum transmission or <5 percentage-point split-error targets. The robust design has worse nominal split error at the nominal condition; the objective penalizes loss and imbalance. This is not a fabrication-ready 50:50 coupler.

## Original files

- [result.json](result.json): exact aggregate report.
- [search.csv](search.csv) and [validation.csv](validation.csv): 36 rows each.
- [search shards](shards/search): 12 jobs, three measurements each.
- [validation shards](shards/validation): 36 jobs, one measurement each.
- [environment-lock.txt](environment-lock.txt) and [installed-packages.json](installed-packages.json): exact environment and inventory.
- [provenance.json](provenance.json): original artifact SHA-256 and per-file Git blob hashes.

The 53-file ZIP (67,500 bytes) was downloaded and its SHA-256 matched GitHub's digest. All original files are preserved byte for byte. Sum of elapsed shard times: 6457.69 seconds (107.63 minutes of simulation time), not pipeline wall-clock time or billed runner minutes. Parallel execution and full CI regression passed (78/78 jobs). No new scientific run is required.

## Limits

Generic two-dimensional Ez FDTD, index 1.8 in air; not a silicon-on-insulator 3D foundry model. Uniform vertical width-bias proxy at fixed centerlines; no stochastic yield, thickness, sidewall-angle or thermal model. Only one input excited, not a full complex scattering matrix. Held-out conditions are independent simulations within the same model, not independent physical reproduction. Verification level: 2D numerical simulation only. See the [experiment method](../../simulations/meep/OPA-ID-003.md).

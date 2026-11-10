# Results archive

Every experiment's result report, kept in the repository because GitHub
Actions artifacts expire after 90 days. Each folder holds the report exactly as
the experiment wrote it, plus a `provenance.json` with the workflow run, job,
commit and trigger it came from.

The reports were recovered from the JSON that each script prints to the CI job
log, which is the same content it writes to the uploaded artifact. Where the
run was on a pull-request branch, the script at that commit is byte-identical to
the version merged on `main`.

All runs use `pymeep 1.35.1` from
[`opa-fdtd-linux-64.lock.txt`](../simulations/meep/opa-fdtd-linux-64.lock.txt)
on a 4-core `ubuntu-24.04` GitHub runner. All FDTD models are illustrative
(index-1.8 core in air, Meep units); none is calibrated to a foundry platform.
Circuit (MZI) experiments use numpy from the same environment.

## Key numbers

| ID | Report | Key result | Main caveat |
|----|--------|------------|-------------|
| 001 | [result.json](opa-fdtd-001/result.json) | Free-space flux 0.868; solver and flux monitor work in CI | Smoke test only |
| 002 | [result.json](opa-fdtd-002/result.json) | 2D air gap: aperture reflection 0.266, transmission 0.594; change from t = 140 to 200 is below 1e-9 | Aperture flux, not mode-resolved |
| 003 | [result.json](opa-fdtd-003/result.json) | 2D 90° bend aperture transmission: 0.673 (R = 1.0), 0.956 (R = 2.0) | Aperture flux includes radiation |
| 004 | [result.json](opa-fdtd-004/result.json) | 2D guided-mode bend transmission: 0.420 (R = 1.0), 0.949 (R = 2.0) | 2D only |
| 005 | [small](opa-fdtd-005/benchmark-small.json), [medium](opa-fdtd-005/benchmark-medium.json) | 3D capacity: 0.19 M cells in 3.8 s / 150 MiB; 1.6 M cells in 24.9 s / 337 MiB | Short runs; not a convergence test |
| 006 | [benchmark-large.json](opa-fdtd-006/benchmark-large.json) | 40×40×4 µm, 6.4 M cells: 235 s, 942 MiB peak RSS | Longer duration than 005, so time is not pure size scaling |
| 007 | [result.json](opa-fdtd-007/result.json) | 3D bend, output flux / straight input flux: 0.217 (R = 1.0), 0.483 (R = 2.0) | Ez current source (TM-like), aperture flux |
| 008 | [result.json](opa-fdtd-008/result.json) | Same ratios at t = 80 and 120; change below 1e-9 | Temporal stability only |
| 009 | [result.json](opa-fdtd-009/result.json) | Resolution 12 → 16 changes ratios by 0.0015 (R = 1.0) and 0.0038 (R = 2.0) | Two resolutions only |
| 010 | [result.json](opa-fdtd-010/result.json) | 93 % of straight input aperture flux is in odd-Z band 1; band-1 output ratio 0.173 (R = 1.0), 0.468 (R = 2.0) | Ez source excites an unknown mode mix |
| 011 | [result.json](opa-fdtd-011/result.json) | TE-like guided-mode transmission at res 16: 0.315 / −5.0 dB (R = 1.0), 0.743 / −1.3 dB (R = 2.0); reflection about 1e-5; straight 0.9998 | Generic material; two resolutions |
| MZI-001 | [result.json](opa-mzi-001/result.json) | Ideal 2×2 MZI programs 1000 random unitaries and near-bar/near-cross targets with max error 2e-15; 48:52 couplers raise the error to 0.04 | Ideal lossless model, single wavelength |
| MZI-002 | [result.json](opa-mzi-002/result.json) | Naive error ≈ 1.3 × coupler error; calibration recovers every reachable target exactly; 1 dB arm-loss imbalance gives 5.7 % error that calibration cannot remove; combined chip scenario reaches 6.2 effective bits | Hardware assumed known exactly for calibration; single wavelength |
| MZI-003 | [result.json](opa-mzi-003/result.json) | Clements mesh exact for N = 2–16 (N(N−1)/2 MZIs, N columns); error grows about √N (1 % couplers: 0.013 → 0.035 from N = 2 to 8); a 4×4 classifier keeps 86.8 % accuracy on imperfect chips; power-only readout drops it to 63 % | Coherent detection and ideal attenuators assumed; toy task |
| COUPLER-001 | [result.json](opa-coupler-001/result.json) | Si 500 × 220 nm coupler: L_c = 37.9 µm at 200 nm gap (50:50 at 19.0 µm), converged to 0.3 %; split ranges from 35 % to 68 % over 1.50–1.60 µm; ±10 nm fabrication error gives 44–59 %; the LAYOUT-001 coupler (236 nm gap, 20 µm) splits about 32:68 | Two-mode theory, straight section only |
| COUPLER-002 | [result.json](opa-coupler-002/result.json) | 3D FDTD of the full layout coupler: L_c 52.2 µm at 24 px/µm vs 52.0 µm MPB (0.4 %); S-bends add 0.091 rad (≈ 3.0 µm); 50:50 needs a 23.0 µm straight section; the current 20 µm gives about 41:59 | 16–24 px/µm only; Richardson check failed (non-blocking) |
| COUPLER-003 | [result.json](opa-coupler-003/result.json) | Layout coupler (236 nm gap, 23.0 µm, bends): 33–70 % across 1.50–1.60 µm, within 5 % of 50:50 only at 1.54–1.56 µm; ±10 nm width or gap alone gives 43.5–57 %; etch bias ±10 nm gives 49.9–50.2 %; bend model within 9 % of 3D FDTD | Coupled-mode theory; uniform errors; no thickness or sidewall variation |
| EO-001 | [result.json](opa-eo-001/result.json) | Push-pull V_π·L 2.4 V·cm for X-cut TFLN (5 µm gap); Si heater P_π 14.0 mW with the ubcpdk stack, 20.3 mW with the ANT stack (post hoc); a 64×64 Clements mesh needs 34–49 W to hold its phases with heaters, while Pockels shifters hold them without current but make the mesh 0.6–3 m long | Literature-range check for P_π failed (non-blocking); 2D heat model, single wavelength, no crosstalk, LN drift or leakage |
| EO-002 | [result.json](opa-eo-002/result.json) | Push-pull V_π·L 1.35–4.12 V·cm for 3–8 µm gaps, with gold absorption 0.47 dB/cm to 1e-7 dB/cm; the gap rule picks 4 µm (1.86 V·cm, 0.023 dB/cm); a folded push-pull 64×64 mesh fits one reticle (395 mm², 368 mm path, 12 dB at 0.3 dB/cm); rings shorten θ 8× but raise the mesh loss to 31 dB; a BTO swap (r_eff 300 pm/V) gives 0.2 V·cm | Metal-loss convergence check failed at 5 µm (non-blocking, post-hoc 3-grid study); semi-vectorial loss model; BTO illustrative |
| LAYOUT-001 | [result.json](opa-layout-001/result.json), [GDS](opa-layout-001/programmable_mzi_2x2.gds), [PNG](opa-layout-001/programmable_mzi_2x2.png) | Programmable 2×2 MZI with balanced dummy heaters and 23.0 µm couplers (50:50 per COUPLER-002), 538 × 71 µm; 10 checks pass; GDS reproducible byte for byte | gdsfactory generic PDK, not a foundry process; 50:50 only at 1.54–1.56 µm (COUPLER-003) |

The 3D results from 007–010 and from 011 describe different polarizations
(TM-like versus TE-like) and are normalized differently, so they should not be
compared number for number.

## Adding a result

When a new experiment is merged, copy its `result.json` (or the files from its
artifact) into `results/opa-fdtd-NNN/`, add a `provenance.json` with the
workflow run, job and commit, and add a row to the table above.

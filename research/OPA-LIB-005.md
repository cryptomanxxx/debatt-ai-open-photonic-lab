# OPA-LIB-005 — component comparability audit

Start with the archived evidence, not new simulation or fabrication. [Machine-readable specification](../components/comparison/lib005-spec.json) pins 14 source reports/manifests by Git blob at 2212d57eb6c1fff65b9d63a99215f5faec244cfe. Audit ten comparisons; none is presently eligible for exact-cell calibration. [Library policy](../components/README.md) remains authoritative. This is the initial evidence gate of LIB005, not the completion of matched studies.

| Comparison | Existing evidence | Decision |
|---|---|---|
| EO Vpi L | EO002 1.86265 V cm at 4 um gap; LAYOUT005/CIR003 3.3 V cm nominal push-pull; Twente 3.5 V cm RF at 5 GHz, reported | Context only; different stack, electrode length, RF/static conventions and measurement planes. 0.2 V cm arithmetic difference is not a model error. |
| SOI grating | 6 dB placeholder vs 4.1 dB published design family (DOI 10.1364/OE.22.020652) | 1.9 dB arithmetic difference only; bandwidth definitions not matched. No substitution of 4.1 dB into model. |
| SOI spiral | 2.40202 dB/cm effective cutback at 1550 nm, conditional OLS interval 1.587–3.217 | External measured spiral reference; not isolated straight loss, no matched simulation. |
| TFLN ring | apparent 44.920 GHz spacing; Q 143524–158679 | Circuit-notch metrics, no isolated ring assignment or calibrated Q. |
| TFLN MMI | LIB003 0/201 nonpassive; same coefficient identity as CIR003 | Conditional numerical model only. |
| TFLN directional coupler | LIB003 201/201 nonpassive | Preserve quarantine; no repair or renormalization. |
| SOI BDC | published design family (DOI 10.1364/OE.23.003795), original GDS, parent DRC | No exact revision measurement or local compact model. |
| Generic coupler | COUPLER003 nominal cross fraction 0.500579 | Numerical only, convergence limitation remains. |
| TFLN cascade | 4/8/12/16 minima across four scans | No matched physical ring identities, heater settings or coherent model. |
| TFLN MZM | CIR003 5 mm four-port modeled transfer | No matched RF/optical data or calibration. |

## Proposed next bounded studies

1. Define same-process passive test structures, reference planes and measurement requirements (straight/cutback, bends, couplers, MZI, optical I/O), separately for SOI and TFLN. Prioritize passive FAB001 and external laser/detectors. No foundry selection yet.
2. Seek exact revision and compatible measured optical power/complex S for the passive MMI/BDC. Do not treat cross-platform loss or nominal split as matched validation. Record missing evidence explicitly; do not manufacture comparison values.
3. For EO comparison, obtain delivered RF voltage, voltage convention, electrode length, impedance, frequency response and geometry/stack. Treat Twente data as a reference, not a fit target for lnoi400. Do not delay passive FAB001 for active RF tests.
4. Advance LIB006 only with explicit process/access constraints, candidate evidence and measurement plan. If no exact match is available, label it a gap and prioritize physical test structures rather than claiming calibrated performance.

CI verifies source identity, model provenance, conservative scope, passivity quarantine and arithmetic; not a new electromagnetic simulation or experiment. Full results exported as JSON and CSV. No modification to historical registry or archived sources.

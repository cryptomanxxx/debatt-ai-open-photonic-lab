# OPA-LIB-005-E – Component evidence review and gated handoff to OPA-LIB-006

## Executive decision

OPA-LIB-005 assessed numerical component models, published measurement references and passive test-chip design questions. **It did not qualify a chip for fabrication.** All 10 original comparisons remained ineligible for exact-cell calibration; the 10 proposed passive test categories are **planning only** and span two incompatible process stacks. [The machine-readable final evidence](../components/comparison/lib005-final-evidence.json) pins eight reviewed Git objects. The [offline CI verifier](../tools/audit_lib005_final.py) fails closed if a source changes, an unsupported model is promoted, a platform is mixed or fabrication is claimed without evidence.

This report incorporates [LIB005-A](OPA-LIB-005.md) comparability, [B](OPA-LIB-005-B.md) measurement planning, [C](OPA-LIB-005-C.md) SiEPIC same-revision source discovery and [D1](OPA-LIB-005-D1.md)–[D4](OPA-LIB-005-D4.md) numerical investigation, with permanently Git-stored D1/D2 original evidence from [PR247](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/pull/247).

## Component evidence, not fabrication certifications

| Component | Platform | Sampled numerical S passivity | Decision | Independent exact-cell measurement? |
|---|---|---|---|---|
| `ebeam_bdc_te1550` four-port compact model | SiEPIC SOI | 50/51 violations, max sigma 1.006876 | **Quarantined from passive circuit models** | No |
| `mmi2x2_optimized1550` fitted model | Luxtelligence TFLN | 0/201 violations, max sigma 0.992942 | **Conditional numerical studies only** | No |
| `directional_coupler_balanced` fitted model | Luxtelligence TFLN | 201/201 violations, max sigma 1.127581 | **Quarantined from passive circuit models** | No |
| `ebeam_gc_te1550` source table | SiEPIC SOI | Not established; column meanings and model mapping unverified | **Discovered, not passivity-screened** | No |

The **SiEPIC broadband BDC** has an authentic, revision-pinned upstream 4×4 model (not a raw same-cell measurement). The 51 sampled S matrices have 50 spectral-norm passivity violations, yet each single-input column remains within unit collected power on those 50 samples. The largest modeled optimal coherent output/incident power ratio is **1.013799** and highest individual-port ratio is **0.999314**. Full complex interference, not merely independent power channels, determines S-matrix passivity. Testing a symmetrized matrix, removed same-side blocks, forward/backward submatrices, zero phase and unitary port-phase changes did not provide a trustworthy corrected physical model. No physical amplification of a real device is inferred; power normalization, phasor convention, reference planes and exact geometry equivalence remain unproven.

The **TFLN MMI** passes its **sampled** numerical screen but has no continuous-band guarantee, matched foundry DRC or measured loss/phase validation. TFLN directional coupler remains quarantined. Do not join TFLN test coefficients, Twente laboratory measurements from a **different** process, and SiEPIC SOI GDS as one calibrated dataset. The 6 dB SOI grating placeholder, 4.1 dB family-level literature, and actual cell geometry are likewise **not interchangeable measurements**.

## Evidence status and sample provenance

- **LIB005-A:** 10 compared cases, zero matching calibrations. Measured spiral/ring/modulator literature is contextual, not a direct model fit.
- **LIB005-B:** five planned test categories per platform: cutback, bend chain, splitter, passive MZI and optical I/O; all need process-specific geometry, references, and independent measurements. SOI BDC original GDS may still be an *experimental measurement target*, but not a numerically qualified passive compact model.
- **LIB005-C:** seven source files pinned from SiEPIC's public PDK. Source discovery establishes identities, not measured exact-cell complex S, and does not justify substituting an adjacent `ebeam_dc_te1550` for `ebeam_bdc_te1550`.
- **LIB005-D1–D4:** full complex S and Gram-matrix controls; 50/51 numerical failure, reciprocal/spectral diagnostics, preserved quarantine, traced D1/D2 ZIPs in permanent Git provenance. D3/D4 derived artifacts are not yet permanently archived in this summary; they can be archived separately without changing this conclusion.

## OPA-LIB-006 → OPA-FAB-001: proposed bounded sequence

1. **P0 – Process access.** Confirm exactly one actual accessible fabrication platform (SOI **or** TFLN for each chip), design licence and permitted file use, process layer map, available wavelength, mask/MPW prices and official DRC/DFM. Neither platform presently has confirmed foundry access.
2. **P1 – Experimental plan freeze.** Prepare matching I/O references, multiple-length cutback series, repeated bends and independently addressable splitter ports; pre-register sample count, wavelength/polarization, geometry, power reference planes, expected uncertainty and acceptance thresholds. External tunable laser, power meter/detector and optical spectrum analyzer may suffice for intensity-based passive tests; phase requires separate calibrated coherent setup.
3. **P2 – Design and foundry review.** Produce a **new** test-harness layout with named ports, lengths and repeats; pass the actual selected foundry's rules and permission gates, not an unrelated generic DRC.
4. **P3 – Physical evidence.** Only after P0–P2, build and measure. Record original `raw_spectra.csv`, `device-map.csv`, `instrument-settings.json`, `reference-measurements.csv` and calibration/uncertainty metadata; then compare exact device and model. Do not divide two-coupler loss into one without justified symmetry or infer phase from power readings.

**Provisional component priority:** Measure propagation and optical I/O first, then bends and a splitter. TFLN `mmi2x2_optimized1550` can be used only for flagged numerical exploration if TFLN fabrication is chosen. On SOI, `ebeam_bdc_te1550` is a candidate **physical measurement structure**, not an approved model for design budgets. Neither upstream imported original GDS nor a generated PCell is inherently fabrication-qualified. No integrated laser, detector, EO drive, comb or AI mesh belongs to this initial passive chip.

## Completion definition

**Research evidence summary ready for LIB006 review** does not equal **LIB006 selection complete** or **OPA-FAB-001 manufacturing-ready**. All physical process access, measurement threshold, calibration and foundry layout gates remain open. This report, its source-pinned JSON and the independent offline evidence-audit CI are the handoff; no historical registry status is overwritten.

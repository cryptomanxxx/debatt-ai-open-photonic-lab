# OPA-LIB-005-D3: SiEPIC BDC multiport diagnostic and hypothesis isolation

## Research question

The four-port SiEPIC EBeam `ebeam_bdc_te1550` numerical compact model from upstream revision `363fbb52eefa8669100499ab531d3fe7befc4867` violates the **conditional** passive S-matrix spectral norm test in **50/51** samples (PR244/245). The full D1/D2 original CI evidence is now committed to `components/comparison/lib005-bdc-evidence/` (PR247). Can the numerical behavior be *localized* to coherence between columns, phase conventions, reciprocal asymmetry, or weak reflected blocks **without claiming a causal explanation**?

## Scope of this PR

`tools/audit_lib005_bdc_diagnostics.py` reopens the same upstream source file, verifies its pinned Git SHA, independently cross-checks the 51 frequencies, singular values and pass/fail decisions against the **permanent original D1 CSV**, and calculates all four-port singular values from native magnitude and phase (phase interpreted as radians, field-normalized **assumption**). It publishes per-frequency diagnostics including the Hermitian Gram matrix `SᴴS` off-diagonal norm, each input's column power, an optimal **numerical coherent input** singular vector and the corresponding model power ratio.

Seven alternative diagnostics are published separately: original S; reciprocal symmetrization `(S+Sᵀ)/2`; removing same-side-port reflection/coupling blocks; forward and backward 2×2 subblocks; replacing all phases with zero; and unit-modulus input/output port rephasing. Rephasing **must** preserve singular values (mathematical invariance control). All interventions except unitary rephasing are **unphysical counterfactual edits**, not new valid source components, not source replacements, and not qualification. A passive forward-only 2×2 subblock would not certify the 4×4 device.

A key discriminating outcome is whether there are wavelengths with all individual input columns carrying at most unit collected power while some **coherent combination** produces greater than unit modeled output, which `SᴴS` off-diagonal coherence can reveal. The spectrum is only 51 source points; no interpolation or derived physical group delay is claimed.

## Acceptance and next experiments

- CI succeeds when the original D1 50/51 finding is reproduced byte-traceably, numerical diagnostics are finite, and quarantine remains enforced. **A green CI does not imply passivity.**
- No arbitrary normalization, smoothing, or phase adjustments may be substituted into the component registry; source unchanged.
- The strongest candidate causal explanations remain **hypotheses** until SiEPIC source-model generation methods, physical layout/port mapping, phase convention, field-power normalization, reference planes and matched physical measurements can be inspected.
- Luxtelligence's **different TFLN** directional-coupler polynomial (201/201 numerical nonpassive points) is **not merged into this SOI dataset**. Future research may compare diagnostic *methods*, not imply equal physical failure mechanisms.

This keeps the first passive chip OPA-FAB-001 measurement gates open. No physical chip is claimed.

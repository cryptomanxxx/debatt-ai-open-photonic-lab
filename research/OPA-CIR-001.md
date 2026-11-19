# OPA-CIR-001 — scattering-network foundation

Purpose: establish a reusable port-based circuit solver, not repeat MZI programming research. Use existing `mzi.py` components and archived MZI-001 as controls.

## Model and acceptance
At one frequency, b=S a, with power-normalized complex waves; S[row output, column incident]. Each connection swaps the two waves without adding propagation. For internal connection permutation P, solve (I-P Sii) ai=P Sie ae; external S=See+Sei (I-P Sii)^(-1) P Sie. Use a linear solve, reject singular/ill-conditioned networks. A reflectionless reciprocal block built from transmission T has reverse T transpose (not conjugate transpose). Explicit port ordering and full scattering matrices support reflection rather than silently discarding it.

Verify 128 seeded settings and programmed targets against existing MZI formula, archived splitting/rotation and degenerate settings, unequal split/loss reference, unitarity/reciprocity/passivity as appropriate, independently derived reflective two-mirror examples, boundary permutation and invalid connection rejection. Absolute tolerance 1e-12. Wrong-phase negative control must be detected. No physical parameters fitted.

## Reuse-first next step
The first implementation uses NumPy in the existing locked environment; it does not install SAX or claim to replace it. Next evaluate the already pinned lnoi400 SAX MMI or SiEPIC compact model, verify its license and complex port convention and compare an assembled MZI against the upstream model. Keep platform choice explicit. Import no power-only approximation as complex S. Do not claim PDK calibration or a complete OPA system yet. See [component policy](../components/README.md). 

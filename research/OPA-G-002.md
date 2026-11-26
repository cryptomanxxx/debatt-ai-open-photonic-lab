# OPA-G-002 — Six-side algorithm reconstruction

Status: CI verified (23/23 checks); [archived evidence](../results/opa-g-002/provenance.json). Supplementary verification remains pending. This is an independent algebraic reconstruction of the two-product side test described in Zhang et al., Nature Communications 16, 5938 (2025), https://doi.org/10.1038/s41467-025-61234-x, Fig. 1b and main text. The main paper was accessible via https://d-nb.info/1375715399/34. Supplementary Note 1 could not be retrieved; exact author coordinate mapping, orientation, encoding and boundary handling remain unverified. This is not a complete reproduction of the supplementary algorithm. No figures or source code copied.

## Derivation

For a closed AABB and forward ray o+t*d, reflect each negative direction axis (including box endpoints) so that active directions v_i are positive. Define L_i = lower_i - origin_i and U_i = upper_i - origin_i after reflection. The permissible interval along axis i is [L_i/v_i, U_i/v_i]. A parallel axis outside its slab rejects immediately; otherwise omit that axis. If any U_i < 0, the box cannot intersect the forward half-line. For the remaining axes, intervals have a common point exactly when every ordered pair satisfies U_i*v_j - L_j*v_i >= 0. There are six such two-product sums for three active axes, two for two axes, and none for one or zero. The ordered-pair construction is a projected side-relation formulation, not a claim of the paper's exact edge ordering. Zero margins count as hits under our closed-box convention. A strict positive test is recorded separately as a boundary diagnostic. The stationary-point convention matches G-001.

## Validation

Reuse the independent rational face oracle and seeded workloads from [OPA-G-001](OPA-G-001.md); also test 4096 translated boxes and 3375 integer-grid cases spanning all direction signs, zero axes and stationary points. Include explicit corner, behind-origin, degenerate and stationary controls. Sweep the same six fractional-bit input grids (2,4,6,8,12,16) on both original G-001 workloads. Require zero disagreement with the oracle on exact and rounded inputs separately; report quantized classifications against original truth, not just rounded truth. Report FP/FN, precheck rejections, six-side cases and strict-boundary misses. Require actual exercise of both six-side and zero-margin paths. No required quantized accuracy. Inputs are synthetic, rational arithmetic is exact for represented binary values, and no runtime benchmark is implied.

Run: `python simulations/graphics/side_test_v002.py`. Outputs result.json and results.csv in results/opa-g-002. Archive actual CI outputs with provenance after merge.

## Remaining gate before OPA-G-003

Obtain Supplementary Note 1, verify exact mapping, scaling and decision convention against the authors' derivation and document differences. The optical circuit stage must additionally model reference-field sign preservation, limited modulation range, bias and phase errors, loss and detector noise. No energy, bandwidth, hardware accuracy or VR rendering claims follow from this experiment.

## Supplementary source audit (2026-11-26)

The supplied supplement has been inspected. See [source audit](OPA-G-002-SOURCE-AUDIT.md) for the S5–S7 sign discrepancy relative to S1/S2, explicit orientation and guard conventions, and registered executable verification. CI and review pending; the corrected determinant is the proposed G-003 interface, not an author-confirmed erratum. Historical G-002 evidence is unchanged.

# OPA-LIB-005-D4 – Interpreting the SiEPIC BDC S-matrix diagnostics

## Source and scope

This analysis uses the actual successful [PR #248 D3 CI output](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44799618360), original artifact **#14661240719**, digest `sha256:3a5bc1866ff89bddb88d88f2455c264ea5481f77b57eeb713652aecaa899f379`. It pins the unchanged D3 analysis script, its original same-revision SiEPIC source Git blob and D1/D2 permanent provenance. The [decision manifest](../components/comparison/lib005-bdc-d4-decision.json) records numerical conclusions and unknowns. The CI tool replays D3, checks every key numerical metric, and emits a deterministic derived D4 decision JSON.

## Main result – coherent inputs matter

Original `ebeam_bdc_te1550` PDK model has **50/51** sampled wavelength points with `sigma_max > 1 + 1e-9`. On all **50** violating points the power collected from **each individual input** is at most 1. The largest individual input power sum anywhere is **0.999314** whereas a model-optimal coherent excitation reaches an output-to-input power ratio of **1.0137986**. This distinguishes the full S-operator criterion from single-port energy checks. Numerical phase and normalization are still conditional PDK model assumptions.

| Diagnostic | Violations / 51 | Largest singular value |
|---|---:|---:|
| Original 4×4 S | 50 | 1.00687568 |
| Reciprocity symmetrized, counterfactual | 49 | 1.00670228 |
| Same-side blocks removed, counterfactual | 28 | 1.00065126 |
| Forward 2×2 submatrix | 9 | 1.00014161 |
| Reverse 2×2 submatrix | 28 | 1.00065126 |
| All phases set to zero, counterfactual | 51 | 1.42011136 |
| Constant unit-modulus input/output port rephasing | 50 | 1.00687568 |

A reciprocal average barely changes the numerical failure. Dropping same-side blocks changes the failure rate but **does not restore full-matrix passivity**. Even the forward-only submatrix retains violations and cannot certify a four-port component. Setting all phases to zero dramatically worsens results, showing phase relationships affect coherence, but **does not prove** the particular upstream phase convention or the root cause. Unitary port rephasing preserves singular values with a maximum difference of about `6.7e-16` – a mathematical control, **not a test of physical reference-plane de-embedding**.

The complex Gram matrix `SᴴS` explains why coherent combinations can violate a power-normalized S bound even when every column individually has length below 1. This does not mean the physical coupler amplifies light, or that SiEPIC's experimental device fails; the raw geometry-to-model equivalence, phase reference, mode normalization, source model generation, and matched wafer measurements remain unverified.

## Research decision

**Maintain `quarantined_nonpassive`.** None of the counterfactual edits is an approved corrected component model; leave source coefficients untouched and do not use for OPA-FAB-001 device loss budgets or active hardware qualification.

Next collect original model generation/port normalization documentation from SiEPIC and exact-cell experimental evidence; in parallel shortlist physically measurable passive test structures and independently assess alternative TFLN MMI on its **separate** fabrication process. Do not treat cross-process results as direct calibration. The D3 artifact is currently a temporary GitHub Actions artifact and should be permanently archived separately when the interpretation is reviewed.

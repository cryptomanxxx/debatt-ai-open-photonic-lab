# OPA-LIB-005-D2 – SiEPIC broadband directional coupler model fails numerical passivity

This is a **negative model-eligibility decision** based on [original D1 successful CI run 44792693356](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44792693356) (PR244, head `05224ddc6d230d592253d560f16c908d60c43276`). [Pinned original report and artifact identity](../components/comparison/lib005-bdc-decision.json). The D1 artifact `opa-lib-005-d1` expires on 2027-02-18 unless permanently archived.

The full four-port S-matrix has **50 of 51 wavelength samples with max singular value > 1 + 1e-9**, conditional on source coefficient power normalization. Highest max singular value over the study is **1.0068756797677312**. The sample closest to 1550 nm is 1550.38868 nm, with input-one collected four-port power **0.9920333963120866** but max singular value **1.002574942217895**. This shows why single-input column power checks cannot replace the full complex matrix operator norm. Source file contains 816 complex entries over 51 points from 1500 to 1600 nm. Numerical 50/50 splitting close to 1550 nm does not establish passive S, fabrication feasibility or measured loss.

**Disposition: `quarantined_nonpassive`.** Do not admit `ebeam_bdc_te1550` compact S data for passive circuits or nominal FAB001 power budgets without investigation and a separately reviewed, independently justified corrected version. Preserve source bytes, derived negative results and traceable file hashes, not an ad hoc normalization that conceals excess singular values. This conclusion is a conditional model screening failure, **not a measured physical amplification mechanism**; modal normalization, port mapping and reference planes remain unverified.

[Luxtelligence lnoi400 directional coupler](../components/external/Luxtelligence/lnoi400/s_parameters/README.md) is a **different model from a different process** with its own 201/201 nonpassive findings. It remains separately quarantined. The lnoi400 MMI passed its previously defined numerical passivity screen, but is not calibrated or process-qualified.

## Reproducibility and next steps

The new CI reruns the reviewed D1 analysis on the exact pinned upstream Git blob, compares every field of its result to the original job's printed report and verifies the negative outcome. The D1 original GitHub artifact SHA256 is pinned in the JSON manifest. No upstream model or existing component registry is modified.

Next: archive exact D1 and D2 evidence as reproducible permanent references, then investigate original port conventions, coefficient provenance, phase assumptions and potential physical explanations with falsifiable controls. For LIB006 passive candidates, explore MMI and passive standalone waveguide test structures with explicit model/measurement qualifications; do not treat an existing GDS file as measured. No fabrication slot, foundry access or qualified design rules have been confirmed.

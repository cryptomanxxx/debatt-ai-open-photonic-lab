# OPA-CIR-005 — first general 4x4 SVD computing block

CIR-004 [run 44515459851](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44515459851): 5/5 checks, eight targets, median naive shape error 0.8755775537326204, calibrated 0.02405753448557389, median transmission 0.7340495495954931, no passivity excess. These are numerical results after a common complex normalization, not measured accuracy.

## Hypothesis and scope

Reuse CIR-004 PDK meshes and existing MZI-003 SVD decomposition. W = U diag(s) V^H, normalize attenuation amplitudes by max(s), apply V^H then diagonal attenuation then U. Two 4x4 meshes, 12 MZIs, 24 MMIs, 32 phase control parameters and four ideal reciprocal reflectionless attenuators. No validated PDK variable attenuator is established in the registry; explicitly use an ideal control to isolate the mesh integration risk. Neither electronic scale nor fitted common complex gain is optical amplification.

At 1550 nm use zero, identity, rank-one, signed diagonal, seeded dense real and complex matrices. Reuse bounded independent mesh calibration (40 evaluations, +/-26.4 V numerical bounds); no joint optimization. Compare ideal SVD reference, naive and independently calibrated full reflected layer. Report mean/min optical transmission, reflection, passivity, full complex 8-port S, voltage settings, gain, matrix error and 32 independent complex vectors per target. A direct forward-only product is a diagnostic, not the full reflected reference. No relative metric for zero matrix; require zero transmitted power instead. No arbitrary precision threshold; preserve unfavorable results. Numerical controls gate CI, passivity gates eligibility separately.

The circuit is an abstraction, not a fabricated or layout-extracted layer. No physical attenuator, RF, noise, WDM or receiver yet. Next assess layer accuracy and system bottlenecks, then proceed to WDM and readout rather than unbounded mesh optimization.

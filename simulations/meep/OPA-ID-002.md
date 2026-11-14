# OPA-ID-002 — Inverse designed splitter

First continuous-material component design study, following [OPA-ID-001](../../results/opa-id-001/README.md). Generic index 1.8 dielectric in air, 2D Ez polarization, 1550 nm, 2.4 × 2.4 µm design region with 25 × 25 weights. One 0.6 µm input guide and two output guides at y = ±0.65 µm.

The initial density is a symmetric grayscale Y-shaped seed. Projected gradient ascent optimizes summed forward band-1 output powers with mirror symmetry and backtracking, up to 16 iterations at 30 px/µm. A separate straight guide reference normalizes incident modal power at each resolution. The minimum runtime is 200 Meep units, following the verified normalization window in ID-001. Central differences test three symmetric directions at two steps and both 30 and 60 px/µm. Independent forward simulations measure initial, optimized and thresholded designs at both resolutions, including reflected mode power using incident-field subtraction. The difference between unity and measured modal powers is unaccounted power, not a direct radiation measurement.

Acceptance requires gradient agreement, physical sanity, independent objective agreement, improved fine-resolution transmission and balanced outputs. Transmission >95%, reflection <1%, and coarse/fine agreement within three percentage points are research targets reported separately, not guaranteed acceptance. Finite monitor spans and modal overlap are limitations. The thresholded design is a diagnostic, not fabrication-ready. No 3D, foundry, broadband or novelty claim.

Outputs: JSON report, gradient and optimization history CSVs, measurement CSV, optimized density CSV and locked environment. Run with the registered CI environment.

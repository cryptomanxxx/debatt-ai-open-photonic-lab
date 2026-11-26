# OPA-G-001 — Ray-box intersection and precision modeling

First numerical experiment under [OPA-G](OPA-G-ROADMAP.md). No fabricated device, optical model or measured performance.

A forward ray is o + t d, t ≥ 0. A closed axis-aligned box includes its boundary; zero direction denotes a stationary point. The slab reference intersects the three axis intervals with [0, infinity). An independent exact rational oracle enumerates intersections with each of the six faces, including degenerate boxes; it also accepts origins inside the box. The oracle operates on represented binary inputs, not unknown physical coordinates.

Use NumPy PCG64 via default_rng, seed 20261126, 4096 samples each of uniform dyadic origins/directions and a deliberately near-face parallel-ray stress workload. The box is [-1,1]^3. Sweep 2, 4, 6, 8, 12 and 16 fractional bits: round each input component to the nearest multiple of 2^-b (ties to even), without saturation or word-length limitation. Classify the rounded inputs with the rational oracle to isolate input quantization. This is not an optical comparator, ADC ENOB or a hardware bit-width model. Direction normalization is not required for geometric intersection; rounding may collapse direction to zero.

Report TP/TN/FP/FN, conditional false-positive and false-negative rates and accuracy separately by workload. Undefined rates are null. Gate: every explicit geometric case and both error-sign controls pass, float slab agrees with exact oracle on unrounded workloads, counts conserve samples, and 16 fractional bits reproduce these specific dyadic inputs. No minimum accuracy imposed on lower precisions. Near-face workload is not a representative scene distribution. False negatives may drop real geometry; false positives may cause extra traversal if a downstream exact test rejects them.

Run from repository root: `python simulations/graphics/ray_box_v001.py`. Outputs result.json and results.csv in results/opa-g-001; CI artifacts first, then archive with workflow provenance per results policy. No physical energy or speed claims. OPA-G-002 will separately reproduce the published side-function algorithm; this experiment does not reproduce it.

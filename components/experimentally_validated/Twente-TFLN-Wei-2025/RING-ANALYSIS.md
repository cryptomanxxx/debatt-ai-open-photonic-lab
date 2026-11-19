# OPA-LIB-004-TFLN-RING — apparent optical resonance metrics

[Wei et al. article](https://doi.org/10.1038/s41467-025-57441-1), [CC BY 4.0 source dataset](https://doi.org/10.5281/zenodo.14065933). Source Supplementary fig 4a, 10001 wavelength / absolute optical power rows, 1549.19902–1550.8018 nm. Article describes four tunable rings with MZI-assisted coupling and heaters, and reports 44 GHz FSR. Figure 3a is a circuit optical spectrum; Supplementary 4f is byte-identical. Supplementary 4b–d display multiple minima per period; not analyzed as isolated rings. Final supplementary PDF not accessible during this review; do not assign 4a to a specific physical ring or heater setting. No article figures reproduced.

Protocol: reverse descending wavelength order, find minima below -72 dBm that are minima within ±100 samples; require four. Local baseline median of dBm samples 0.05–0.08 nm either side; use linear-power half-depth (baseline plus dip power divided by two), interpolate nearest bracketing crossings in linear power. Use exact frequency conversion c/lambda for linewidth and adjacent spacing. Apparent Q=center frequency / apparent linewidth. Baseline window sensitivity 0.04–0.07, 0.05–0.08, 0.06–0.09 nm; not calibrated uncertainty. Threshold/windows selected after exploratory source inspection, not prospective acceptance criteria. Independent readback below frozen for CI.

| Center nm | Dip dBm | Local baseline dBm | Apparent extinction dB | Apparent linewidth GHz | Apparent Q |
|---:|---:|---:|---:|---:|---:|
|1549.46741|-77.806|-62.788|15.018|1.23521|156638|
|1549.82723|-77.312|-62.858|14.454|1.21904|158679|
|1550.18770|-75.736|-62.724|13.012|1.34745|143524|
|1550.54785|-77.224|-62.704|14.520|1.28522|150438|

Adjacent frequencies differ by 44.92005, 44.98029, 44.91947 GHz. Consistent in scale with paper's 44 GHz FSR, not exact ring attribution. Apparent linewidth 1.22–1.35 GHz and Q ~144k–159k; instrument resolution, reference planes and circuit baseline not established, no deconvolution. Do not equate optical half-depth linewidth with paper's RF filter bandwidth of 1.3 GHz. No intrinsic Q, calibrated loaded Q, coupling state, phase or complex S inferred. No exact geometry link to Luxtelligence. CI exports result and notch table; derived archive pending. Original CSV unmodified.

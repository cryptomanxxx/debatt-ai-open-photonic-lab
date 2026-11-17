# OPA-ID-004 — Inverse designed waveguide crossing

Exact original results from [PR #102](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/pull/102), successful [run 44083174983](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44083174983). Earlier unsuccessful runs are not the source of this archive.

## Results

At 1550 nm, 60 px/µm, horizontal launch:

| Metric | Plain binary crossing | Optimized continuous density | Thresholded |
|---|---:|---:|---:|
| Transmission | 82.6945% | 92.7014% | 82.6945% |
| Summed crosstalk | 10.7610% | 0.3043% | 10.7610% |
| Reflection | 0.3425% | 0.0692% | 0.3425% |

All 12 mandatory checks and six of seven research targets pass. Transmission does not reach 95%. Continuous optimization reduces summed crosstalk by about 97.17% relative to the plain crossing. The thresholded design reproduces the plain-cross result, so the continuous improvement does not establish a binary fabrication-ready design.

At 1530 and 1570 nm, the optimized continuous design transmits 92.8332% and 92.5612%, respectively, with summed crosstalk 0.2931% and 0.3163%. Orthogonal excitation at 1550 nm agrees in transmission within 4e-13 absolute. Ten ascent steps accepted; all eight gradient checks pass. Simulation elapsed time 925.78 s (not total runner billing).

The final run uses signed MPB k-points for independent direct port overlap calculations, consistent with the adjoint objective, retaining the 1e-6 agreement threshold. Earlier [run 44079157791](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44079157791) failed at the vertical source parity API; [run 44081454731](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44081454731) failed objective agreement. These failures are distinct from the final successful run.

## Archived originals

- [result.json](result.json): report with configuration, checks, measurements, history and all density vectors.
- [measurements.csv](measurements.csv): 17 measurement rows.
- [gradient_checks.csv](gradient_checks.csv): eight directional gradient tests.
- [optimization_history.csv](optimization_history.csv): ten iterations.
- [optimized_density.csv](optimized_density.csv): 25 × 25 continuous weights.
- [environment-lock.txt](environment-lock.txt) and [installed-packages.json](installed-packages.json): exact environment.
- [provenance.json](provenance.json): artifact and file hashes.

All seven original files preserved byte for byte. The downloaded ZIP matched its published SHA-256 and passed CRC verification.

## Limitations

Generic 2D Ez dielectric in air (index 1.8), not a foundry stack. Continuous weights are not fabrication geometry; thresholding is diagnostic only. No feature-size constraints, fabrication tolerance, coherent multi-input operation, full complex scattering matrix, 3D or physical validation. Unaccounted power is not independently measured radiation. See [experiment method](../../simulations/meep/OPA-ID-004.md).

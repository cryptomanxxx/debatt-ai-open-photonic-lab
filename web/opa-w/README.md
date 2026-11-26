# OPA-W teaching models

[Chip 13 · Photonic Weight Memory](../chip13/README.md), [Chip 14 · Photonic In-Memory Computing](../chip14/README.md), and [Chip 15 · Photonic Neural Network](../chip15/README.md) run in the browser. These are pedagogical demonstrations. All nine phases in the [OPA-W research roadmap](../../research/OPA-W-ROADMAP.md) are planned and unregistered for execution.

## Run and test

From the repository root:

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory web
```

Visit `http://127.0.0.1:8000/chip13/`, `/chip14/` or `/chip15/`. The standalone pages use the same code and CSS as Sites. Their cross-chip and Ecosystem links target the main Site shell.

Run the numerical suite with `node --test web/opa-w/model.test.mjs web/chip16/model.test.cjs`. The [GitHub Actions workflow](../../.github/workflows/photonic-circuit-lab.yml) also runs `node --test web/opa-w/browser.test.cjs` with Playwright 1.56.1 and its Chromium. The browser suite covers keyboard slider changes, all three simulations, presets, resets and 360, 768 and 1280 px widths. Playwright is a test-only dependency.

## Chip 13 model

Each cell records an intended fraction `k/(L−1)`, a programmed fraction `s` in [0, 1], and the last effective write time. A normalized dose is `D = intensity × duration`. For `D ≤ 0.15` the physical state and write time are kept. Otherwise the modeled fraction moves by `clamp((D−0.15)/0.85, 0, 1)` of the distance from the aged state to the target. This abstracts heating and switching into a single dose threshold. The animation duration is for readability and independent of the model's normalized duration.

Age `a` advances only when requested, including with both lasers off. The effective phase fraction is `s* = clamp(s exp(−a/τ) + d ln(1+a), 0, 1)`. The retention time constant `τ` and signed drift coefficient `d` have illustrative values. The read probe leaves the state unchanged. The array and its settings live in the page session. The 4 × 4 view hides the remaining cells without clearing them. Switching storage mode changes the coding resolution of the current state.

`T(s*) = floor + span × (1−s*)^curve`. GST uses (0.24, 0.57, 1.25) and GSSe uses (0.40, 0.50, 0.90). These coefficients are invented, with no wavelength or geometry calibration. The detector receives `max(0, Iread × 10^(−loss/10) × T + n)` in normalized units, where `n` is a uniform-like bounded seeded sample. The decoder uses the known incident intensity and loss, clips to the profile range, inverts the curve and rounds to the nearest level. It reports no decoded value at zero probe power. The displayed read error count is the current simulated array snapshot against intended levels. The model omits write/read disturb, endurance, thermal dynamics and crosstalk.

## Chips 14 and 15 models

For signed weight `w` and input `x`, set `w⁺=max(w,0)`, `w⁻=max(−w,0)` and likewise `x⁺`, `x⁻`. For each output row, the two nonnegative contributions per input are:

- `P⁺ = A(x⁺w⁺ + x⁻w⁻)`
- `P⁻ = A(x⁺w⁻ + x⁻w⁺)`
- `P⁺ − P⁻ = A x w`, where `A = 10^(−loss/10)`

The model independently sums powers, subtracts the two rails, adds a bounded sample of detector noise, saturates to ± the number of inputs and optionally quantizes. Independent powers are a modeling assumption. A physical design needs a fanout budget and a means to suppress coherent cross terms, for example orthogonal channels with appropriate detection. The model does not include actual splitter topology, laser wall-plug energy, peripheral bandwidth or measured timing.

Weights are quantized before use. `b` signed bits use `2^(b−1)−1` equal steps on either side of shared zero, leaving one redundant code. Detector quantization uses the same formula with its own setting and full scale. A continuous setting skips rounding. The electronic reference multiplies the requested weights by its own inputs using JavaScript double precision. Chip 14 reports sample-specific agreement bits `max(0, log₂(F/RMSE))` at full scale `F=4`. This is an error metric for the current vector. Hardware ADC ENOB would require a separate measurement.

Chip 15 uses a 4 → 4 → 3 → 2 network. A drift strength `d` reduces programmed contrast through `w_eff = w(1−d|w|)`. This is an illustrative perturbation with no time or device calibration. Each of the two hidden-layer detectors feeds a clipped ReLU or tanh implemented electronically. The activation is re-encoded before the next optical stage. The output layer uses the linear detector values as scores. Layer-wise RMSE compares the two propagated paths after activation in hidden layers and at the final readout in the output layer. The matrices are handcrafted for demonstration.

## Scientific references

- Ríos et al., [Integrated all-photonic non-volatile multi-level memory](https://doi.org/10.1038/nphoton.2015.182), *Nature Photonics* (2015). Demonstrates GST-based optical programming and readout.
- Meng et al., [Electrical programmable multilevel nonvolatile photonic random-access memory](https://doi.org/10.1038/s41377-023-01213-3), *Light: Science & Applications* (2023). Demonstrates electrically programmed GSSe with optical readout.
- Feldmann et al., [Parallel convolutional processing using an integrated photonic tensor core](https://doi.org/10.1038/s41586-020-03070-1), *Nature* (2021). Demonstrates integrated optical computation with phase-change weights.

These papers motivate the demos. The supplied browser coefficients are illustrative and do not reproduce the experiments or provide physical performance estimates.

## Integrate into ChatGPT Sites

The patch was developed against Sites source revision `1bbf72fc7a284b4c83f54ed73633dfed757d12a1`. Use the existing Site project and start with a clean checkout of its source. Once the GitHub PR is reviewed and merged, use that GitHub revision as the source for:

```sh
bash web/opa-w/apply.sh /absolute/path/to/sites-checkout
git -C /absolute/path/to/sites-checkout diff --check
```

The patch updates the main page, deep links and selector routing. The script copies the reviewed runtime files verbatim into `dist/`. If the Sites source has advanced and the patch no longer applies, reconcile the changes and validate the resulting diff before deployment.

In the Sites preview, verify the selector lists 1–16, each legacy panel opens, Chip 13–15 deep links and the nine OPA-W phase rows work, and leaving a running new chip stops its animation. Exercise start, stop, reset, presets and controls at desktop, tablet and phone widths. Select Chip 10 and Chip 16 to check their original controls. Keep the current access settings. Record the merged GitHub commit and the packaged Sites commit, compare the copied files with the merged revision, then save and deploy the matching Sites version. Repeat the smoke checks on the live URL.

# Chip 16 · Photonic Ray Tracing Accelerator

Open [index.html](index.html) in a modern browser for the standalone, dependency-free teaching experiment. In the public Lab, choose **Chip 16** under **06 · Photonic Circuit Lab**. Chip 13–15 remain reserved for OPA-W.

## Methods and evidence

The electronic reference computes the intersection of two axis intervals with the closed forward half-line, starting at t = 0. It uses double-precision JavaScript arithmetic and treats direction components below 10⁻¹² in magnitude as parallel. Tangency is a hit. The reduced-precision proxy rounds the origin, direction and box bounds to a 2⁻ᵇ grid using JavaScript's Math.round and runs the same geometry test. The results table classifies each ray against the currently selected box. The two presets place the center ray near a boundary where coarse rounding causes a false positive or false negative.

Zhang et al. ([Nature Communications 16, 5938, 2025](https://doi.org/10.1038/s41467-025-61234-x), Fig. 1 and Eq. 1) describe a 3D ray–box method using consistent side signs on six oriented edges. For an axis-aligned box, each side expression reduces to a two-term dot product. The thin-film lithium-niobate core uses two cascaded push–pull MZMs per signal branch and a coherent reference branch. Around null bias the fields approximate the two signed products. Photodetection and thresholding against the reference intensity give the sign. The paper reports 16 GS/s experimental signaling, approximately 100 GHz modulator bandwidth and 326 fJ/operation under its own accounting.

The interactive circuit readout maps the 2D cross product between the center ray and the ray-origin-to-corner vector onto the same two-term structure. Corner deltas are divided by 16 and the factors are independently divided by 4 before taking sine, with unit field amplitudes. These normalizations keep the phases in a small-signal region and document the sign convention. The computed intensity difference is dimensionless. The circuit schematic is original and uses the functional blocks in the paper as its source. Neither the side illustration nor the quantized slab calculation reproduces the published six-edge algorithm, device errors or hardware performance. OPA-G-002 and OPA-G-003 retain those future validation goals.

## Tests

Run `node --test web/chip16/model.test.cjs` from the repository root. It covers forward-ray edge cases, 2,000 seeded comparisons with independent 2D segment tests, both quantization error presets and normalized optical readout signs. Browser checks cover all sliders, both selectors, presets, reset, method disclosure, deep links, previous chip selection, the headset image and the phase counts. Check the phone and tablet layouts using 360 and 768 px viewports.

## Website integration

The integration patch targets Sites source revision `d72c4926ef3c6eb4e84410b8feac0dbf5a8a0ec5`. To reproduce it in a compatible Sites checkout, run:

```sh
bash web/chip16/apply.sh /path/to/sites-worktree
```

The patch adds [OPA-G](../../research/OPA-G-ROADMAP.md) and [OPVR](../../research/OPVR-ROADMAP.md) to OPA Ecosystem, with all seven and nine phases, and integrates the standalone experiment into the lab selector. The OPVR concept image is AI-generated and depicts a proposed headset. The existing research roadmap and acceptance gates apply.

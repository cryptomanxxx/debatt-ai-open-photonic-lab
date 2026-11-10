# Debatt-AI Open Photonic Lab

An open, reproducible laboratory for designing photonic AI accelerators: from
simulation of single components, through Mach–Zehnder interferometer (MZI)
meshes, to chip layouts that can be sent to a multi-project wafer (MPW)
fabrication run.

> **Status:** early stage. The lab currently contains a series of
> reproducible Meep FDTD experiments on generic dielectric waveguides. No
> foundry-calibrated component or chip layout exists yet. See the
> [roadmap](#roadmap).

## Interactive demonstrations

- **Open Photonic Lab:** [Explore the photonic chip design laboratory](https://debatt-ai-open-photonic-lab.mr-marcus-sweden.chatgpt.site/)
- **MZI learning simulation:** [Explore optical interference and AI learning](https://optiskt-ai-larande.mr-marcus-sweden.chatgpt.site/)

## Why

Optical computing can perform matrix–vector multiplication, the core
operation of neural networks, with light instead of electrons. Going from an
idea to a fabricated photonic chip is still hard and mostly happens behind
closed doors. This lab aims to make every step open, documented and
reproducible so that anyone can learn from it and build on it.

## Principles

1. **Reproducible:** every experiment runs in GitHub Actions against an exact,
   locked conda environment
   ([`opa-fdtd-linux-64.lock.txt`](simulations/meep/opa-fdtd-linux-64.lock.txt)).
2. **Honest:** every result states what it does *not* show. Illustrative
   models are never presented as foundry-validated predictions.
3. **Incremental:** experiments are numbered (`OPA-FDTD-NNN`), small, and
   build on each other. Old experiments are kept unchanged as a record.

## Roadmap

| Phase | Goal | Status |
|-------|------|--------|
| 1 | FDTD fundamentals: reproducible Meep pipeline, convergence and normalization practice | **Done** (001–009) |
| 2 | Guided-mode metrics in 3D (eigenmode source and decomposition) | **Started** (010–011) |
| 3 | Real material platforms (e.g. Si/SiO₂ 220 nm, SiN, LNOI) and spectral response | Planned |
| 4 | GDSFactory components in an open PDK: waveguide, bend, directional coupler, MMI, phase shifter, single 2×2 MZI | Planned |
| 5 | MZI mesh (2×2 → 4×4) as an optical matrix multiplier, with a link to the MZI learning simulation | Planned |
| 6 | Design-rule-checked GDS ready for an MPW run | Planned |
| 7 | Measurement plan and published measurement data | Planned |

Fabricating photonic chips requires a foundry. The realistic open path is to
share designs made in open PDKs and submit them to MPW runs, where many
designs share one wafer.

## Experiments

All experiments live in [`simulations/meep/`](simulations/meep/) and each has
its own workflow in [`.github/workflows/`](.github/workflows/). Results are
uploaded as workflow artifacts (GitHub deletes these after 90 days by
default), so key numbers are also recorded below.

| ID | What it establishes |
|----|---------------------|
| 001 | Meep runs reproducibly in CI with a locked environment (free-space smoke test) |
| 002 | Normalized 2D straight-waveguide / air-gap scattering with convergence check |
| 003 | Exploratory 2D 90° bend-radius comparison (aperture flux) |
| 004 | 2D guided-mode power audit of bends using eigenmode decomposition |
| 005 | Memory and runtime benchmark for bounded 3D simulations |
| 006 | Guarded 40×40×4 µm 3D capacity profile |
| 007 | First 3D dielectric waveguide bend comparison (aperture flux) |
| 008 | Temporal convergence of the 3D bend simulations |
| 009 | Grid-resolution sensitivity of the 3D bend simulations |
| 010 | 3D modal decomposition (odd-Z band 1) of bend ports, still with a finite-size Ez source |
| 011 | 3D **guided-mode** bend transmission: launched TE-like eigenmode, decomposed at both ports, validated by a straight reference |

### OPA-FDTD-011 results

Fundamental TE-like mode, index-1.8 core (0.8 × 0.4) in air, vacuum
wavelength 1.25 (Meep units), 90° bend:

| Case | Guided transmission (res 12 → 16) | Loss at res 16 | Aperture-flux ratio at res 16 |
|------|-----------------------------------|----------------|-------------------------------|
| Straight reference | 0.9996 → 0.9998 | 0.001 dB | 1.000 |
| Bend, radius 1.0 | 0.333 → 0.315 | 5.0 dB | 0.472 |
| Bend, radius 2.0 | 0.762 → 0.743 | 1.3 dB | 0.819 |

What this shows:

- The straight waveguide transmits 99.98 % in the guided mode, which
  validates the measurement method.
- The aperture flux used in 007–010 **overestimates** guided transmission,
  by about 50 % (relative) at radius 1.0, because it also counts radiated light that
  passes through the output aperture.
- Guided reflection is about 0.00001 for both bends, measured after
  subtracting the straight-reference fields. Without that subtraction, leakage
  of the incident field into the discretized backward mode reads about 10–20×
  higher, comparable to the straight waveguide's own leakage floor.
- The low index contrast (1.8 vs 1.0) makes tight bends very lossy. Real
  platforms such as silicon (index ≈ 3.48) allow much tighter bends.
- Changing the resolution from 12 to 16 changes transmission by less than 0.02,
  but two resolutions do not prove convergence.

Numbers come from a local run with the same locked environment; the full report is
[`results/opa-fdtd-011/result.json`](results/opa-fdtd-011/result.json), and the CI
artifact `opa-meep-bend-launched-mode-v011` contains the same report.

## Running locally

```bash
# Requires micromamba (or conda/mamba) on linux-64
micromamba create -n opa-fdtd --file simulations/meep/opa-fdtd-linux-64.lock.txt
micromamba activate opa-fdtd
python simulations/meep/bend_3d_launched_mode_v011.py   # writes results/opa-fdtd-011/result.json
```

New experiments should import shared geometry and measurement helpers from
[`simulations/meep/opa_common.py`](simulations/meep/opa_common.py).

## Contributing

Contributions are welcome. Add a new numbered experiment (`OPA-FDTD-NNN`)
with its own workflow, state its limitations in the result report, and add a
row to the experiment table above.

## License

[MIT](LICENSE)
